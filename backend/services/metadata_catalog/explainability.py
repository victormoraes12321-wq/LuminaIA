import logging
from typing import List, Dict, Any, Optional
from models.new_pipeline_contracts import (
    CanonicalPlan, DashboardState, QueryContext, ConversationGraph
)

logger = logging.getLogger("luminaai.services.metadata_catalog.explainability")

class ExplainabilityEngine:
    """
    O ExplainabilityEngine interpreta o dataset resultante da execução analítica,
    provendo insights executivos de negócios e respondendo perguntas explicativas
    diretas baseadas apenas nos dados carregados em memória RAM.
    """
    
    async def generate_explanation(
        self,
        query: str,
        plan: CanonicalPlan,
        dataset: List[Dict[str, Any]],
        db_state: DashboardState,
        client: Any,
        model: str
    ) -> tuple["ExecutiveExplanation", str]:
        from services.new_query_orchestrator import ExecutiveExplanation
        # Se o dataset estiver vazio, retorna explicação direta apropriada
        if not dataset:
            empty_explanation = ExecutiveExplanation(
                summary="Nenhum dado localizado para esta consulta específica.",
                insights=["O dataset retornado está vazio."],
                recommendations=["Tente ajustar as restrições ou remover filtros temporais."],
                warnings=["Nenhum registro encontrado."]
            )
            return empty_explanation, "N/A - Dataset Vazio"

        # Constrói o prompt analítico de forma 100% conceitual (sem vazamentos de SQL/Views)
        explain_prompt = (
            "Você é o Diretor de Business Intelligence corporativo do LuminaAI.\n"
            "Interprete o seguinte dataset analítico fornecido pelo backend analítico de produção:\n\n"
            f"- Pergunta original do usuário: {query}\n"
            f"- Objetivo do plano lógico: {plan.goal}\n"
            f"- Dataset Normalizado (primeiras 50 linhas): {dataset[:50]}\n\n"
            "## DIRETRIZES DE SEGURANÇA E ALUCINAÇÃO:\n"
            "1. NÃO tente calcular novos valores matemáticos (médias, somas, percentuais) além dos que já estão explicitamente contidos no dataset.\n"
            "2. Não invente novas métricas ou números. Atenha-se estritamente aos registros de fatos fornecidos.\n"
            "3. Forneça sugestões gerenciais pertinentes apenas com base no que foi extraído.\n"
            "4. Nunca mencione nomes físicos de views (como VW_...) ou comandos SQL analíticos."
        )

        try:
            chat_explain = await client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": "Você é um Diretor de Business Intelligence corporativo especialista em relatórios executivos."},
                    {"role": "user", "content": explain_prompt}
                ],
                response_format=ExecutiveExplanation,
                temperature=0.2
            )
            return chat_explain.choices[0].message.parsed, explain_prompt
        except Exception as e:
            logger.error(f"[Explainability] Falha ao gerar explicação executiva via LLM: {e}")
            fallback_explanation = ExecutiveExplanation(
                summary="Dados extraídos com sucesso. Veja a tabela de resultados.",
                insights=["Dataset carregado corretamente."],
                recommendations=[],
                warnings=[]
            )
            return fallback_explanation, explain_prompt

    async def explain_local_dataset(
        self,
        query: str,
        graph: ConversationGraph,
        client: Any,
        model: str
    ) -> Optional[Dict[str, Any]]:
        """
        Interpreta perguntas explicativas locais sobre o dataset ativo em memória RAM
        (ex: 'Explique melhor', 'Por quê?', 'Por que essa barra é maior?'), respondendo
        imediatamente sem re-consultar o banco clone.
        """
        if not graph.current_node_id or graph.current_node_id not in graph.nodes:
            return None

        current_node = graph.nodes[graph.current_node_id]
        if not current_node.execution_result or not current_node.execution_result.dataset:
            return None

        p_lower = query.lower()
        explanation_keywords = [
            "explique melhor", "explica", "por que", "por quê", "causou", "motivo", "detalhe", "barra", "linha"
        ]
        
        # Intercepta se a pergunta for de explicação ou detalhamento interpretativo
        if any(kw in p_lower for kw in explanation_keywords):
            logger.info(f"[Explainability] Interceptada pergunta explicativa local: '{query}'")
            
            explain_prompt = (
                "Você é o Diretor de Business Intelligence corporativo do LuminaAI.\n"
                "Forneça uma explicação gerencial adicional ou responda à dúvida do usuário sobre o dataset anterior:\n\n"
                f"- Pergunta atual: {query}\n"
                f"- Pergunta original executada: {current_node.user_query}\n"
                f"- Dataset em memória RAM: {current_node.execution_result.dataset[:50]}\n\n"
                "## REGRAS:\n"
                "1. Responda baseando-se estritamente no dataset fornecido.\n"
                "2. Não invente números e não recalcule valores analíticos matemáticos.\n"
                "3. Seja sucinto e direto."
            )
            
            try:
                from services.new_query_orchestrator import ExecutiveExplanation
                import uuid
                chat_explain = await client.beta.chat.completions.parse(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Você é um Diretor de Business Intelligence corporativo especialista em relatórios executivos."},
                        {"role": "user", "content": explain_prompt}
                    ],
                    response_format=ExecutiveExplanation,
                    temperature=0.2
                )
                explanation = chat_explain.choices[0].message.parsed
                
                # Retorna os dados com status de UI local atualizada (reutilizando o dataset atual)
                return {
                    "query_id": str(current_node.query_context.dataset_id if current_node.query_context else uuid.uuid4()),
                    "trace_id": str(uuid.uuid4()),
                    "request_id": str(uuid.uuid4()),
                    "status": "FULL_RENDERING",
                    "pergunta_original": query,
                    "resposta_direta": explanation.summary,
                    "ia_justificativa": "Explicação gerencial gerada localmente em cima dos dados em memória RAM.",
                    "chart_type": current_node.dashboard_state.chart_type.value,
                    "chart_data": {
                        "columns": [{"key": k, "label": k.replace("_", " ").title()} for k in current_node.execution_result.dataset[0].keys()] if current_node.execution_result.dataset else [],
                        "rows": current_node.execution_result.dataset
                    },
                    "insights": explanation.insights,
                    "recommendations": explanation.recommendations,
                    "warnings": explanation.warnings,
                    "execution_time_ms": 0.0
                }
            except Exception as e:
                logger.error(f"[Explainability] Falha na explicabilidade explicativa local: {e}")
                
        return None

explainability_engine = ExplainabilityEngine()
