"""
LuminaAI — Corporate Intelligence Engine Schemas
------------------------------------------------
Estruturas de dados tipadas (Pydantic) do CIE.
"""
from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel, Field


# ── Filtros do Plano ──────────────────────────────────────────────────────────

class PlanFiltersSchema(BaseModel):
    """Filtros dimensionais extraídos pela IA."""
    date_range: str = Field(default="", description="Intervalo temporal em formato texto (ex: '2025-01-01 to 2025-06-30')")
    products: list[str] = Field(default_factory=list, description="Lista de produtos identificados")
    customers: list[str] = Field(default_factory=list, description="Lista de compradores/clientes identificados")
    regions: list[str] = Field(default_factory=list, description="Lista de regiões ou filiais")


class PlanVisualizationSchema(BaseModel):
    """Preferências de visualização para o frontend."""
    type: str = Field(default="TABLE", description="Tipo de visualização recomendado (BAR | LINE | PIE | TABLE | KPI | AREA | SCATTER | HEATMAP | TREEMAP | FUNNEL)")
    layout_priority: str = Field(default="ALTA", description="Prioridade de layout de renderização ('ALTA' | 'MEDIA' | 'BAIXA')")


class StructuredPlanSchema(BaseModel):
    """Plano de execução estruturado legado para compatibilidade retroativa."""
    request_id: str = Field(description="UUID imutável fornecido pelo backend")
    intent: str = Field(description="Intenção principal (ex: 'analisar faturamento')")
    query_type: str = Field(description="Tipo de consulta ('SELECT' | 'AGGREGATION' | 'TIME_SERIES')")
    metrics: list[str] = Field(default_factory=list, description="Métricas solicitadas")
    group_by: list[str] = Field(default_factory=list, description="Campos de agrupamento")
    filters: PlanFiltersSchema = Field(default_factory=PlanFiltersSchema)
    comparisons: list[str] = Field(default_factory=list, description="Comparações temporais")
    visualization: PlanVisualizationSchema = Field(default_factory=PlanVisualizationSchema)
    requires_insight: bool = Field(default=True, description="Se requer insights textuais complementares")
    confidence_score: float = Field(default=0.0, description="Score de confiança do plano")


# ── Schemas de Retorno da LLM (Structured Outputs) ───────────────────────────

class ParametroFiltro(BaseModel):
    """Parâmetro chave-valor estruturado de filtro."""
    chave: str = Field(description="Nome do parâmetro (ex: vendedor_nome, data_inicio, etc.)")
    valor: str = Field(description="Valor do parâmetro (ex: 'Carlos Oliveira', '2025-01-01')")


class IntentionResponseSchema(BaseModel):
    """Estrutura detalhada de intenção individual extraída pela LLM."""
    view_catalog_id: uuid.UUID | None = Field(description="UUID exato da view correspondente no catálogo ou null")
    confianca: float = Field(ge=0.0, le=1.0, description="Score de confiança (0.0 a 1.0)")
    parametros: list[ParametroFiltro] = Field(default_factory=list, description="Parâmetros de filtro extraídos")
    justificativa: str = Field(description="Justificativa curta (máx. 250 chars) em português brasileiro")
    fora_de_escopo: bool = Field(default=False, description="True se pedir informações fora do domínio de vendas")
    mensagem_bloqueio: str | None = Field(default=None, description="Mensagem amigável de bloqueio se fora_de_escopo=True")
    resposta_direta: str | None = Field(default=None, description="Resposta curta em português para perguntas puramente conceituais")
    chart_type_sobrescrever: str | None = Field(default=None, description="Tipo visual explícito solicitado")
    chart_types_solicitados: list[str] | None = Field(default=None, description="Formatos múltiplos solicitados")
    plano_estruturado: StructuredPlanSchema | None = Field(default=None, description="Plano legado")
    
    # Propriedades de NLU estendidas do motor
    operacao: str = Field(description="RANKING | TOP | BOTTOM | MAIOR | MENOR | QUANTIDADE | TOTAL | SOMA | MEDIA | MAXIMO | MINIMO | COMPARACAO | TENDENCIA | CRESCIMENTO | QUEDA | PARTICIPACAO | DISTRIBUICAO | CORRELACAO | LISTAGEM | DETALHAMENTO | RESUMO | KPI | ANOMALIA | PROJECOES")
    entidade_alvo: str = Field(description="PRODUTO | CLIENTE | FORNECEDOR | PEDIDO | VENDA | COMPRA | ESTOQUE | CATEGORIA | MARCA | REPRESENTANTE | VENDEDOR | FILIAL | CIDADE | ESTADO | FORMA_PAGAMENTO | RECEITA | DESPESA | LUCRO | MARGEM | TICKET | QUANTIDADE")
    quantidade_limite: int | None = Field(default=None, description="Quantidade ou limite superior (ex: TOP 10 -> 10)")
    periodo_referencia: str | None = Field(default=None, description="Período temporal identificado (ex: MES_PASSADO, ULTIMOS_30_DIAS)")
    is_comparacao: bool = Field(default=False, description="True se for uma comparação (ex: Junho x Maio)")
    comparativo_detalhe: str | None = Field(default=None, description="Caso is_comparacao=True, o que comparar (ex: 'Junho vs Maio')")
    visualizacao_preferida: str | None = Field(default=None, description="Componente visual ideal (BAR | LINE | PIE | TABLE | KPI | etc.)")
    nivel_confianca: str = Field(description="Nivel de confiança: ALTA | MEDIA | BAIXA")


class MultipleIntentionsResponseSchema(BaseModel):
    """Wrapper para permitir detecção de múltiplas intenções compostas de uma só vez."""
    intentions: list[IntentionResponseSchema] = Field(description="Lista de intenções detectadas")


# ── Objetos de Domínio Internos do CIE ────────────────────────────────────────

class BusinessIntentSchema(BaseModel):
    """
    Objeto Intermediário que representa a intenção estruturada de negócios.
    Importante: Nunca acessa banco de dados, views ou SQL diretamente.
    """
    objetivo: str = Field(description="Resumo do que o usuário deseja alcançar (ex: ranking_vendedores)")
    entidade: str = Field(description="Entidade de negócio alvo (ex: VENDEDOR)")
    dominio: str = Field(default="Vendas", description="Domínio operacional (ex: Vendas, Estoque)")
    area: str = Field(default="Comercial", description="Área corporativa responsável")
    indicadores: list[str] = Field(default_factory=list, description="Lista de indicadores requisitados em linguagem natural")
    kpis: list[str] = Field(default_factory=list, description="Lista de KPIs identificados na intenção")
    filtros: dict[str, Any] = Field(default_factory=dict, description="Parâmetros de filtro chave-valor extraídos")
    periodo: str | None = Field(default=None, description="Janela de tempo solicitada (ex: MES_PASSADO)")
    comparacoes: list[str] = Field(default_factory=list, description="Comparações pretendidas")
    agrupamentos: list[str] = Field(default_factory=list, description="Campos de agrupamento dimensional")
    prioridade: str = Field(default="MEDIA", description="Prioridade calculada (ALTA | MEDIA | BAIXA)")
    complexidade: str = Field(default="BAIXA", description="Complexidade analítica calculada (ALTA | MEDIA | BAIXA)")
    visual_sugerido: str = Field(default="TABLE", description="Tipo de visualização recomendado")
    nivel_confianca: str = Field(default="ALTA", description="Nivel de confiança geral (ALTA | MEDIA | BAIXA)")
    score_confianca: float = Field(default=1.0, description="Score numérico (0.0 a 1.0)")


class VisualStrategySchema(BaseModel):
    """Define a melhor estratégia visual e layout do painel analítico."""
    componente_principal: str = Field(default="TABLE", description="Tipo de gráfico ou componente principal (BAR | LINE | PIE | TABLE | KPI)")
    componentes_secundarios: list[str] = Field(default_factory=list, description="Componentes auxiliares de apoio")
    interatividade: list[str] = Field(default_factory=list, description="Recursos habilitados (drill-down, expand, etc.)")
    layout_sugerido: str = Field(default="GRID", description="Sugestão de layout de tela (GRID, FLOW, CARDS)")
    responsividade: bool = Field(default=True, description="Indica suporte a layouts móveis/responsivos")


class BlueprintSchema(BaseModel):
    """
    O Blueprint Analítico oficial gerado pelo CIE.
    IMPORTANTE: Nunca deve conter SQL, referências a tabelas, views físicas ou dados brutos.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="ID único do Blueprint")
    business_intent: BusinessIntentSchema = Field(description="A intenção de negócio estruturada original")
    kpis: list[str] = Field(default_factory=list, description="KPIs oficiais mapeados no BKE")
    filtros: dict[str, Any] = Field(default_factory=dict, description="Filtros dinâmicos limpos")
    agrupamentos: list[str] = Field(default_factory=list, description="Dimensões de agrupamento de dados")
    periodo: str | None = Field(default=None, description="Período temporal mapeado")
    comparacoes: list[str] = Field(default_factory=list, description="Comparações temporais mapeadas")
    visual_strategy: VisualStrategySchema = Field(description="Diretriz visual do dashboard")
    dependencias: list[str] = Field(default_factory=list, description="Fórmulas ou indicadores dependentes")
    dashboard_sugerida: str = Field(default="TEMPLATE_PADRAO", description="Nome do template de dashboard sugerido")
    criado_em: str = Field(default="", description="Data e hora de criação do Blueprint")


class CIEContextSchema(BaseModel):
    """Contexto empresarial completo fornecido ao CIE."""
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None = None
    session_id: str | None = None
    departamento: str = "Vendas"
    permissoes: list[str] = Field(default_factory=list)
    historico_recente: list[dict[str, str]] = Field(default_factory=list)
    custom_instructions: str | None = None
