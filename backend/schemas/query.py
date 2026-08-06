"""
LuminaAI — Schemas Pydantic v2: Query Engine

Schemas de Request e Response para o endpoint central POST /api/v1/query.
Define o contrato completo da API de consulta inteligente.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, field_validator

from contracts.analytical_v2 import AnalyticalResponseV2
from models.view_catalog import ChartType
from schemas.dashboard_ui_sidechat import DashboardSideChatActionV2, DashboardSideChatContextV2


# ── Request ───────────────────────────────────────────────────

class ChatMessageSchema(BaseModel):
    """Representa uma mensagem do histórico do chat no request."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)

class QueryRequest(BaseModel):
    """
    Payload de entrada para o endpoint de consulta inteligente.
    O usuário envia uma pergunta em linguagem natural e o ID do tenant.
    """

    pergunta: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Pergunta em linguagem natural do usuário",
        examples=[
            "Qual foi o faturamento mensal de 2024?",
            "Me mostre a evolução de clientes do último semestre",
            "Quero ver o resumo executivo do trimestre atual",
        ],
    )
    tenant_id: uuid.UUID = Field(
        ...,
        description="UUID da empresa para filtrar o catálogo de views correto",
    )
    history: list[ChatMessageSchema] | None = Field(
        default=None,
        max_length=20,
        description="Histórico recente de mensagens (conversação activa)",
    )
    session_id: str | None = Field(
        default=None,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_.:-]+$",
        description="Identificador opcional da sessao conversacional ativa.",
    )
    mode: str = Field(
        default="analytical",
        max_length=32,
        description="Modo de resposta da IA: quick/operational | analytical/intelligent | executive",
    )
    semantic_version: str | None = Field(
        default=None,
        max_length=64,
        description="Versão semântica opcional para reprodutibilidade histórica"
    )
    blueprint_version: str | None = Field(
        default=None,
        max_length=64,
        description="Versão do blueprint opcional para reprodutibilidade histórica"
    )
    use_new_pipeline: bool = Field(
        default=False,
        description="Flag para desviar a requisição para o novo pipeline cognitivo"
    )
    parent_id: str | None = Field(
        default=None,
        max_length=64,
        description="ID do nó pai no grafo de conversa para ramificações"
    )

    client_message_id: uuid.UUID | None = Field(
        default=None,
        description="UUID idempotente gerado uma vez por submissao e reutilizado no retry.",
    )
    expected_context_version: int | None = Field(
        default=None,
        ge=0,
        description="Versao server-side esperada pelo cliente para detectar concorrencia.",
    )
    dashboard_context: DashboardSideChatContextV2 | None = Field(
        default=None,
        description="Envelope público mínimo para o side chat governado de dashboards V2.",
    )

    @field_validator("mode")
    @classmethod
    def normalize_known_mode(cls, value: str) -> str:
        clean = str(value or "analytical").strip().lower().replace("-", "_").replace(" ", "_")
        allowed = {
            "quick",
            "fast",
            "rapido",
            "rapida",
            "operational",
            "operacional",
            "mode_1",
            "analytical",
            "analytic",
            "intelligent",
            "inteligente",
            "smart",
            "padrao",
            "default",
            "mode_2",
            "executive",
            "executivo",
            "advisor",
            "consultor",
            "premium",
            "mode_3",
        }
        return clean if clean in allowed else "analytical"


# ── Estruturas de Dados por Tipo de Gráfico ───────────────────

class DatasetBar(BaseModel):
    """Dataset individual para gráfico de barras."""
    label: str
    data: list[float]
    backgroundColor: str | list[str]
    borderColor: str
    borderWidth: int = 2
    type: str | None = None  # Permite datasets mistos (ex: bar + line)


class ChartDataBar(BaseModel):
    """Estrutura de dados para gráfico de barras (compatível Chart.js)."""
    labels: list[str] = Field(description="Labels do eixo X")
    datasets: list[DatasetBar]
    resumo: dict[str, Any] = Field(
        default_factory=dict,
        description="Métricas resumidas: total, média, melhor período, etc.",
    )


class DatasetLine(BaseModel):
    """Dataset individual para gráfico de linhas."""
    label: str
    data: list[float]
    borderColor: str
    backgroundColor: str
    fill: bool = False
    tension: float = 0.4
    yAxisID: str | None = None


class ChartDataLine(BaseModel):
    """Estrutura de dados para gráfico de linhas (compatível Chart.js)."""
    labels: list[str]
    datasets: list[DatasetLine]
    resumo: dict[str, Any] = Field(default_factory=dict)


class ChartDataPie(BaseModel):
    """Estrutura de dados para gráfico de pizza / donut (compatível Chart.js)."""
    labels: list[str] = Field(description="Nome de cada fatia")
    values: list[float] = Field(description="Percentuais (somam ~100%)")
    colors: list[str] = Field(description="Cores HEX de cada fatia")
    resumo: dict[str, Any] = Field(default_factory=dict)


class TableColumn(BaseModel):
    """Definição de coluna para tabela de dados."""
    key: str = Field(description="Chave do campo no objeto de cada row")
    label: str = Field(description="Título da coluna para exibição")
    type: str = Field(
        description=(
            "Tipo de renderização: "
            "string | number | currency | date | badge | boolean"
        ),
    )
    sortable: bool = True
    width: str | None = None


class ChartDataTable(BaseModel):
    """Estrutura de dados para tabela paginada."""
    columns: list[TableColumn]
    rows: list[dict[str, Any]]
    total_rows: int = Field(description="Total de registros (para paginação)")
    resumo: dict[str, Any] = Field(default_factory=dict)


class KPIItem(BaseModel):
    """Item individual de um painel de KPIs."""
    id: str = Field(description="Identificador único do KPI para o frontend")
    label: str = Field(description="Título do KPI")
    value: float = Field(description="Valor numérico bruto")
    value_formatado: str = Field(description="Valor formatado para exibição (ex: R$ 1.250.000,00)")
    unit: str = Field(description="Unidade: BRL | percent | count | score")
    trend: str = Field(description="Direção da tendência: up | down | stable")
    trend_value: float = Field(description="Variação percentual ou absoluta")
    trend_label: str = Field(description="Período de comparação (ex: 'vs. mês anterior')")
    icon: str = Field(description="Ícone sugerido: currency | chart | users | star | ticket")


class ChartDataKPI(BaseModel):
    """Estrutura de dados para painel de KPIs executivos."""
    kpis: list[KPIItem]
    periodo: str = Field(description="Período de referência dos dados")
    gerado_em: str = Field(description="Data de geração dos dados (ISO 8601)")


class VisualizationItem(BaseModel):
    """Visualização individual de dados analíticos."""
    chart_type: ChartType
    chart_data: dict[str, Any]
    view_name: str | None = None


# ── Response ──────────────────────────────────────────────────

class IntentionPlanItem(BaseModel):
    """Representa um item do plano de intenções estruturado (NLU)."""
    view_catalog_id: uuid.UUID | None = None
    confianca: float
    operacao: str
    entidade_alvo: str
    quantidade_limite: int | None = None
    periodo_referencia: str | None = None
    is_comparacao: bool = False
    comparativo_detalhe: str | None = None
    visualizacao_preferida: str | None = None
    nivel_confianca: str
    filtros: dict[str, str] = Field(default_factory=dict)
    justificativa: str


class QueryResponse(BaseModel):
    """
    Resposta estruturada completa do endpoint de consulta inteligente.

    O frontend usa `chart_type` para selecionar o componente visual correto
    e `chart_data` para alimentá-lo com dados.
    O campo `query_id` permite que o usuário favoritar esta consulta.
    v3.0: Adicionado `resposta_direta` e `visualizations` para múltiplos componentes.
    """

    query_id: uuid.UUID = Field(
        description="ID único desta consulta no search_history — use para favoritar",
    )
    request_id: uuid.UUID | None = Field(
        default=None,
        description="ID único de requisição imutável para rastreamento completo de ponta a ponta.",
    )
    session_id: str | None = Field(default=None, max_length=128)
    query_node_id: uuid.UUID | None = None
    response_node_id: uuid.UUID | None = None
    feedback_target_checksum: str | None = Field(
        default=None,
        pattern=r"^[a-f0-9]{64}$",
        description="Checksum estrutural da resposta para feedback governado.",
    )
    parent_id: uuid.UUID | str | None = None
    context_version: int | None = Field(default=None, ge=0)
    context_epoch: int | None = Field(default=None, ge=0)
    conversation_status: str | None = Field(default=None, max_length=32)
    idempotent_replay: bool = False
    conversation_warning: str | None = Field(default=None, max_length=500)
    context_relationship: str | None = Field(default=None, max_length=64)
    public_context_summary: dict[str, Any] | None = Field(
        default=None,
        description="Resumo publico dos campos mantidos, substituidos ou removidos.",
    )
    context_resolution_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Telemetria estrutural do resolvedor, exposta somente para ADMIN.",
    )
    applied_preference_summary: dict[str, Any] | None = Field(
        default=None,
        description="Resumo público e removível das preferências aplicadas.",
    )
    dashboard_action: DashboardSideChatActionV2 | None = Field(
        default=None,
        description="Ação estruturada e fechada solicitada pelo side chat; texto livre nunca é executável.",
    )
    user_profile_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Telemetria estrutural do perfil; sem conteúdo pessoal detalhado.",
    )
    view_catalog_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "ID da view Oracle identificada pela IA. "
            "Nulo quando a IA não encontra correspondência."
        ),
    )
    view_name: str | None = Field(
        default=None,
        description="Nome da view Oracle identificada (ex: VW_VENDAS_MENSAIS)",
    )
    chart_type: ChartType | None = Field(
        default=None,
        description=(
            "Tipo de componente visual padrão a renderizar. "
            "Para múltiplos componentes, consulte a lista 'visualizations'."
        ),
    )
    chart_data: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Dados estruturados para o componente padrão."
        ),
    )
    visualizations: list[VisualizationItem] | None = Field(
        default=None,
        description="v3.0: Lista de visualizações solicitadas (suporte a múltiplos componentes de uma vez)."
    )
    analytical_contract: AnalyticalResponseV2 | None = Field(
        default=None,
        description="Sidecar opcional e versionado lumina.analytics/2.0.",
    )
    bi_intelligence: dict[str, Any] | None = Field(
        default=None,
        description="v5.2: Motor de inteligência de dados determinístico calculado no backend."
    )
    parametros_extraidos: dict[str, Any] = Field(
        default_factory=dict,
        description="Parâmetros identificados pela IA na pergunta (datas, filtros, etc.)",
    )
    ia_confianca: float | None = Field(
        default=None,
        description="Score de confiança da IA (0.0 = sem match, 1.0 = certeza absoluta)",
    )
    ia_justificativa: str | None = Field(
        default=None,
        description="Explicação da IA sobre a escolha da view ou motivo de não encontrar",
    )
    pergunta_original: str = Field(
        description="Pergunta exatamente como foi recebida do usuário",
    )
    pode_favoritar: bool = Field(
        default=False,
        description="True apenas quando uma view foi identificada com sucesso",
    )
    ia_analise: str | None = Field(
        default=None,
        description="Análise executiva rica e detalhada dos dados gerados/retornados.",
    )
    mensagem: str | None = Field(
        default=None,
        description=(
            "Mensagem informativa para o usuário. "
            "Preenchida quando a IA não encontra correspondência."
        ),
    )
    resposta_direta: str | None = Field(
        default=None,
        description="v3.0: Resposta textual direta da IA para perguntas conceituais."
    )
    plano_nlu: list[IntentionPlanItem] | None = Field(
        default=None,
        description="v3.0: Plano estruturado NLU contendo a decomposição detalhada de intenções."
    )
    plano_execucao: dict[str, Any] | None = Field(
        default=None,
        description="Plano de execução detalhado gerado pela camada Query Planner."
    )
    dashboard_payload: dict[str, Any] | None = Field(
        default=None,
        description="Payload analítico completo estruturado para visualização no frontend."
    )
    datasets: dict[str, Any] | None = Field(
        default=None,
        description="Lista de datasets estruturados e normalizados gerados pelo DatasetBuilder."
    )
    analytics_results: dict[str, Any] | None = Field(
        default=None,
        description="Resultados agregados e KPIs de BI gerados pelo AnalyticsEngine."
    )
    analytical_package_id: str | None = Field(
        default=None,
        description="ID do Analytical Package reutilizado nesta consulta (quando package_reused=True).",
    )
    package_reused: bool = Field(
        default=False,
        description="True quando a consulta foi respondida por reuso de um Analytical Package (sem NLU/Planner).",
    )
    package_compatibility_score: float | None = Field(
        default=None,
        description="Score de compatibilidade semântica (0.0-1.0) que levou ao reuso do Package.",
    )
    telemetry: dict[str, Any] | None = Field(
        default=None,
        description="Métricas de observabilidade e performance do pipeline de IA.",
    )
    trust_center: dict[str, Any] | None = Field(
        default=None,
        description="Métricas de observabilidade, linhagem de dados e status de sincronização/cache da consulta.",
    )
    data_status: dict[str, Any] | None = Field(
        default=None,
        description="Status real dos dados analiticos no PostgreSQL e horario da ultima sincronizacao.",
    )
    validation_summary: dict[str, Any] | None = Field(
        default=None,
        description="Resultado das validacoes matematicas executadas antes da entrega da resposta.",
    )
    interaction_options: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Acoes seguras para aprofundar ou reorganizar a resposta na mesma conversa.",
    )
    admin_diagnostics: dict[str, Any] | None = Field(
        default=None,
        description="Diagnostico tecnico completo. Presente somente para usuarios ADMIN.",
    )
    roqg_validated: bool = Field(
        default=True,
        description="True quando a resposta foi auditada e validada pelo ROQG."
    )
    render_plan: dict[str, Any] | None = Field(
        default=None,
        description="Plano formal de renderização gerado pelo Response Orchestrator & Quality Gate (ROQG)."
    )
    status: str | None = Field(
        default=None,
        description="Status de execução (FULL_RENDERING, AMBIGUOUS, MISSING_INFORMATION, etc.)"
    )
    ambiguities: list[str] | None = Field(
        default=None,
        description="Lista de opções para resolução de ambiguidade"
    )
    missing_information: list[str] | None = Field(
        default=None,
        description="Lista de campos obrigatórios ausentes"
    )
    semantic_clarification: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Clarificação semântica tipada com opções públicas e tokens assinados."
        ),
    )
    goal: str | None = Field(
        default=None,
        description="Objetivo analítico do plano"
    )



class HistoryListItem(BaseModel):
    """Schema de histórico de pesquisa simplificado para a sidebar do frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pergunta: str
    view_name: str | None = None
    chart_type: ChartType | None = None
    timestamp: datetime
    parametros: dict[str, Any] | None = None


class FavoriteListItem(BaseModel):
    """Schema de favoritos estruturado contendo metadados visuais da view Oracle."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    view_name: str
    chart_type: ChartType
    parametros: dict
    query_id: uuid.UUID
