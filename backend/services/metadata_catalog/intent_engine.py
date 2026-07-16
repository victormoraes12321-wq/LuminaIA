import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from models.new_pipeline_contracts import (
    SemanticPlan, SemanticFilter, ExecutionStatus, IntentType,
    VisualizationType, ComparisonOperator, ConversationNode
)
from services.metadata_catalog.catalog import get_corporate_catalog
from services.ai_credential_manager import ai_credential_manager
import uuid

logger = logging.getLogger("luminaai.services.metadata_catalog.intent_engine")

class SemanticPatch(BaseModel):
    operation: str = Field(..., description="ADD_FILTER, CHANGE_PERIOD, REMOVE_FILTER, ADD_METRIC, CHANGE_LIMIT")
    field: str = Field("", description="Nome conceitual da dimensão ou métrica, ex: 'Estado', 'Receita'")
    value: str = Field("", description="Novo valor ou período do filtro, ex: 'MG', 'LAST_YEAR', '2026-06-01'")

class IntentEngineOutput(BaseModel):
    is_continuity: bool = Field(..., description="Indica se a pergunta é uma continuação direta/mutação do plano anterior da conversa.")
    status: ExecutionStatus = Field(..., description="READY, AMBIGUOUS, OUT_OF_SCOPE, MISSING_INFORMATION")
    ambiguities: List[str] = Field(default_factory=list, description="Lista de ambiguidades se o status for AMBIGUOUS.")
    missing_information: List[str] = Field(default_factory=list, description="Lista de informações ausentes se o status for MISSING_INFORMATION.")
    
    # Preenchido obrigatoriamente (para evitar anyOf de nulo na OpenAI)
    plan: SemanticPlan = Field(..., description="Plano semântico completo se status for READY e não for continuidade. Se for continuidade, retorne um plano padrão vazio (status=INVALID, goal='', etc.)")
    patches: List[SemanticPatch] = Field(default_factory=list, description="Lista de alterações semânticas sobre o plano anterior.")

class CorporateIntentEngine:
    """
    Motor de Intenções Corporativo (Refatorado).
    Opera unicamente no domínio conceitual do negócio, sem qualquer conhecimento
    de Views físicas, tabelas, banco de dados ou sintaxe SQL.
    """
    
    def __init__(self):
        pass

    def _build_system_prompt(self) -> str:
        catalog = get_corporate_catalog()
        
        # Constrói especificações conceituais dinâmicas do CKG
        entities_desc = []
        for ent_name, ent in catalog.entities.items():
            # Mapeia dimensões amigáveis de negócio a partir do CKG
            friendly_dims = []
            for dim_name, dim in catalog.dimensions.items():
                if dim.physical_view in ent.views:
                    friendly_dims.append(dim_name)
                    
            # Mapeia métricas amigáveis de negócio a partir do CKG
            friendly_mets = []
            for met_name, met in catalog.metrics.items():
                if met.physical_view in ent.views:
                    friendly_mets.append(met_name)
                    
            entities_desc.append(
                f"- {ent_name}: "
                f"dimensões={list(set(friendly_dims))}, "
                f"métricas={list(set(friendly_mets))}"
            )
            
        metrics_desc = []
        for met_name, met in catalog.metrics.items():
            metrics_desc.append(f"- {met_name}: {met.description} (unidade: {met.unit})")
            
        dimensions_desc = []
        for dim_name, dim in catalog.dimensions.items():
            dimensions_desc.append(f"- {dim_name}: {dim.dimension_type} (hierarquia: {dim.hierarchy})")

        aliases_desc = []
        for alias_name, alias_meta in catalog.aliases.items():
            aliases_desc.append(f"- '{alias_name}' refere-se a '{alias_meta.canonical_name}'")

        system_prompt = (
            "Você é o Interpretador Semântico do LuminaAI. Sua responsabilidade é traduzir a pergunta do usuário "
            "em um plano conceitual analítico (SemanticPlan) ou em uma lista de patches semânticos (SemanticPatch).\n"
            "Você opera unicamente no domínio conceitual de negócio. NUNCA mencione tabelas, views (como VW_...), "
            "schemas, SQL ou colunas físicas de banco de dados.\n\n"
            
            "## ENTIDADES DE NEGÓCIO DISPONÍVEIS:\n"
            f"{'/n'.join(entities_desc)}\n\n"
            
            "## MÉTRICAS DISPONÍVEIS:\n"
            f"{'/n'.join(metrics_desc)}\n\n"
            
            "## DIMENSÕES DISPONÍVEIS:\n"
            f"{'/n'.join(dimensions_desc)}\n\n"
            
            "## ALIASES & SINÔNIMOS MAPEADOS:\n"
            f"{'/n'.join(aliases_desc[:25])}\n\n"
            
            "## DIRETRIZES DE CONTINUIDADE DA CONVERSA:\n"
            "1. Se o usuário fizer uma pergunta de acompanhamento curta (ex: 'Agora de MG', 'E no mês passado', 'Filtrar ativos') "
            "que altere a pergunta anterior, defina 'is_continuity' = True e preencha a lista de 'patches'.\n"
            "2. Se for uma nova pergunta analítica completa, defina 'is_continuity' = False e preencha o plano completo ('plan').\n\n"
            
            "## DIRETRIZES DE STATUS:\n"
            "1. Se a pergunta contiver ambiguidades claras sobre qual entidade ou métrica se refere, defina status = 'AMBIGUOUS' "
            "e descreva o problem em 'ambiguities'.\n"
            "2. Se for uma pergunta totalmente fora do domínio de BI corporativo (ex: 'Quem criou o Excel'), defina status = 'OUT_OF_SCOPE'.\n"
            "3. Se faltar informação essencial para a análise, defina status = 'MISSING_INFORMATION'.\n\n"

            "## DIRETRIZES DE PROJEÇÃO DE CAMPOS:\n"
            "1. Se a intenção for listagem simples de cadastros (ex: 'Listar todos os clientes', 'Ver vendedores cadastrados', 'Listar produtos'), "
            "você DEVE obrigatoriamente preencher o array 'dimensions' com os campos conceituais que descrevem aquela entidade. "
            "Por exemplo: para Clientes inclua 'Cliente.nome' e 'Cliente.cnpj_cpf'; para Vendedor inclua 'Vendedor.nome_ved'; para Produto inclua 'Produto.nome_produto'. "
            "NUNCA gere um plano com arrays de metrics e dimensions simultaneamente vazios para evitar queries inválidas no banco de dados.\n"
            "2. Quando o usuário pedir por 'produtos mais vendidos' ou 'ranking de produtos' ou similares, você DEVE priorizar a métrica 'Receita' "
            "(faturamento total) em vez de 'quantidade' para evitar que itens de valor irrisório (como porcas, parafusos, miudezas) dominem o topo do ranking, "
            "garantindo que os produtos de maior relevância comercial sejam exibidos."
        )
        return system_prompt

    async def analyze_query(
        self,
        query: str,
        tenant_id: str,
        history: List[Dict[str, str]] = None,
        current_node: Optional[ConversationNode] = None,
        **kwargs
    ) -> IntentEngineOutput:
        logger.info(f"[IntentEngine] Analisando query: '{query}' para tenant: {tenant_id}")
        
        lease = await ai_credential_manager.resolve_client(tenant_id=uuid.UUID(tenant_id))
        client = lease.client
        model = lease.model
        
        system_prompt = self._build_system_prompt()
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Adiciona histórico se relevante
        if history:
            for msg in history[-6:]:  # Limita a 6 mensagens recentes
                messages.append({"role": msg["role"], "content": msg["content"]})
                
        messages.append({"role": "user", "content": query})
        
        try:
            chat_completion = await client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=IntentEngineOutput,
                temperature=0.0
            )
            output = chat_completion.choices[0].message.parsed
            
            # Se for plano completo, garante injeção de Trace ID e timestamps
            if output.plan:
                output.plan.trace_id = uuid.uuid4()
            
            logger.info(f"[IntentEngine] Query processada. Status: {output.status.value}. Continuidade: {output.is_continuity}")
            return output
            
        except Exception as exc:
            logger.error(f"[IntentEngine] Falha ao processar com LLM estruturado: {exc}", exc_info=True)
            # Fallback determinístico básico sem IA
            return IntentEngineOutput(
                is_continuity=False,
                status=ExecutionStatus.READY,
                plan=SemanticPlan(
                    status=ExecutionStatus.READY,
                    intent=IntentType.LIST,
                    goal=query,
                    entities=["Cliente"],
                    metrics=[],
                    dimensions=[],
                    trace_id=uuid.uuid4()
                )
            )

corporate_intent_engine = CorporateIntentEngine()
