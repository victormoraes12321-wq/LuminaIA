from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from uuid import UUID
import uuid

# ── A) Enums de Controle e Infraestrutura ──────────────────────────

class ExecutionStatus(str, Enum):
    READY = "READY"
    AMBIGUOUS = "AMBIGUOUS"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"
    NEEDS_REPLANNING = "NEEDS_REPLANNING"

class IntentType(str, Enum):
    LIST = "LIST"
    AGGREGATION = "AGGREGATION"
    RANKING = "RANKING"
    TREND = "TREND"
    INVESTIGATION = "INVESTIGATION"
    COMPARISON = "COMPARISON"
    DETAIL = "DETAIL"
    KPI = "KPI"

class VisualizationType(str, Enum):
    TABLE = "TABLE"
    KPI_CARD = "KPI_CARD"
    BAR = "BAR"
    LINE = "LINE"
    PIE = "PIE"
    DONUT = "DONUT"
    SCATTER = "SCATTER"
    HEATMAP = "HEATMAP"

class ComparisonOperator(str, Enum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    GREATER_EQUAL = "GREATER_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_EQUAL = "LESS_EQUAL"
    IN = "IN"
    NOT_IN = "NOT_IN"
    LIKE = "LIKE"
    BETWEEN = "BETWEEN"

class QueryCost(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

class EmptyDatasetPolicy(str, Enum):
    EMPTY_EXPECTED = "EMPTY_EXPECTED"
    EMPTY_UNEXPECTED = "EMPTY_UNEXPECTED"
    EMPTY_SUSPICIOUS = "EMPTY_SUSPICIOUS"

# ── B) Classe Base de Rastreamento (TrackedModel) ──────────────────

class TrackedModel(BaseModel):
    trace_id: UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pipeline_version: str = "2.0"

# ── C) Modelos de Planejamento Lógico ──────────────────────────────

class SemanticFilter(BaseModel):
    field: str = Field(..., description="Ex: 'clientes.cidade'")
    operator: ComparisonOperator
    value: str = Field(..., description="Valor do filtro em formato string. Para múltiplos valores, separe por vírgula.")

class SemanticPlan(TrackedModel):
    status: ExecutionStatus
    ambiguities: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    
    intent: IntentType
    goal: str
    entities: List[str]
    metrics: List[str]
    dimensions: List[str]
    filters: List[SemanticFilter] = Field(default_factory=list)
    limit: int = Field(100, description="Limite máximo de linhas para a consulta. Use 100 por padrão.")
    suggested_visualization: VisualizationType = VisualizationType.TABLE

class CanonicalFilter(BaseModel):
    field: str = Field(..., description="Ex: 'Cliente.cidade'")
    operator: ComparisonOperator
    value: Union[str, int, float, List[str], List[int], List[float]] = Field(..., description="Valor do filtro.")

class CanonicalPlan(TrackedModel):
    status: ExecutionStatus
    intent: IntentType
    goal: str
    entities: List[str]
    metrics: List[str]
    dimensions: List[str]
    filters: List[CanonicalFilter] = Field(default_factory=list)
    limit: Optional[int] = None
    suggested_visualization: VisualizationType = VisualizationType.TABLE
    canonicalization_trace: List[Dict[str, Any]] = Field(default_factory=list)

# ── D) Modelos de Resolução Física ────────────────────────────────

class ResolvedEntity(BaseModel):
    logical_name: str
    physical_view: str
    primary_key: str
    available_columns: List[str] = Field(default_factory=list)
    foreign_keys: Dict[str, str] = Field(default_factory=dict)  # Destino_Entity -> Chave_Fisica
    supported_metrics: List[str] = Field(default_factory=list)
    supported_dimensions: List[str] = Field(default_factory=list)

class ResolvedEntities(TrackedModel):
    entities: Dict[str, ResolvedEntity]
    joins: List[Dict[str, str]] = Field(default_factory=list)

class ExecutionPlan(TrackedModel):
    status: ExecutionStatus = ExecutionStatus.READY
    resolved_entities: ResolvedEntities
    selected_views: List[str]
    columns: List[str]
    filters: List[CanonicalFilter] = Field(default_factory=list)
    group_by: List[str] = Field(default_factory=list)
    order_by: List[str] = Field(default_factory=list)
    having: List[str] = Field(default_factory=list)
    cte: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    limit: Optional[int] = None
    resolution_justification: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadados de Controle de Execução
    estimated_cost: QueryCost = QueryCost.LOW
    estimated_rows: int = 0
    execution_priority: int = 1
    cacheable: bool = True
    cache_key: Optional[str] = None
    required_permissions: List[str] = Field(default_factory=list)
    timeout: int = 30
    empty_dataset_policy: EmptyDatasetPolicy = EmptyDatasetPolicy.EMPTY_EXPECTED

# ── E) Execução, Contexto e Estado de Sessão ───────────────────────

class ExecutionResult(TrackedModel):
    status: ExecutionStatus
    dataset: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    execution_time_ms: float
    row_count: int
    cache_hit: bool = False
    source_views: List[str] = Field(default_factory=list)

class QueryContext(TrackedModel):
    dataset_id: str
    dataset_version: int = 1
    source_sync_timestamp: Optional[datetime] = None
    row_count: int
    execution_time_ms: float
    is_cached: bool = False

class DashboardState(BaseModel):
    chart_type: VisualizationType
    selected_chart_id: Optional[str] = None
    layout_mode: str = "DEFAULT"
    drilldown_stack: List[str] = Field(default_factory=list)
    hidden_columns: List[str] = Field(default_factory=list)
    visible_metrics: List[str] = Field(default_factory=list)
    selected_series: List[str] = Field(default_factory=list)
    active_dashboard: Optional[str] = None
    selected_filters: Dict[str, Any] = Field(default_factory=dict)
    expanded_cards: List[str] = Field(default_factory=list)
    selected_tab: Optional[str] = None
    pagination_page: int = 1
    sort_column: Optional[str] = None
    sort_direction: Optional[str] = None

class ConversationNode(BaseModel):
    node_id: str
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)
    user_query: str
    canonical_plan: CanonicalPlan
    execution_result: Optional[ExecutionResult] = None
    query_context: Optional[QueryContext] = None
    dashboard_state: DashboardState

class ConversationGraph(BaseModel):
    nodes: Dict[str, ConversationNode] = Field(default_factory=dict)
    current_node_id: Optional[str] = None


# ── Validação de Criação e Execução de Teste Integrado ─────────────

def validate_tracked_model_inheritance():
    """
    Instancia um ConversationGraph complexo e verifica que
    a herança do TrackedModel funciona com geração automática de UUIDs e Timestamps.
    """
    print("START: Iniciando validacao dos novos contratos do pipeline analitico...")
    
    # 1. Criação do estado de visualização
    db_state = DashboardState(
        chart_type=VisualizationType.KPI_CARD,
        selected_filters={"regiao": "Sudeste"}
    )
    
    # 2. Criação dos planos lógicos e canônicos
    c_filter = CanonicalFilter(
        field="Cliente.cidade",
        operator=ComparisonOperator.EQUALS,
        value="Ataléia"
    )
    
    c_plan = CanonicalPlan(
        status=ExecutionStatus.READY,
        intent=IntentType.KPI,
        goal="Analise de vendas de Ataleia",
        entities=["Cliente", "Venda"],
        metrics=["receita_total"],
        dimensions=["cidade"],
        filters=[c_filter]
    )
    
    # Validações dos campos de rastreamento herdados do TrackedModel
    assert c_plan.trace_id is not None
    assert c_plan.created_at is not None
    assert c_plan.pipeline_version == "2.0"
    print(f"SUCCESS: Heranca do TrackedModel validada com sucesso em CanonicalPlan! Trace ID: {c_plan.trace_id}")
    
    # 3. Criação de nós e estruturação do ConversationGraph
    node_root = ConversationNode(
        node_id="root",
        user_query="Qual o faturamento em Ataleia?",
        canonical_plan=c_plan,
        dashboard_state=db_state,
        children_ids=["child_1"]
    )
    
    # Nó filho com novo plano temporal ("E no mês passado?")
    c_plan_child = CanonicalPlan(
        status=ExecutionStatus.READY,
        intent=IntentType.KPI,
        goal="Comparativo temporal em Ataleia",
        entities=["Cliente", "Venda"],
        metrics=["receita_total"],
        dimensions=["cidade"],
        filters=[
            c_filter,
            CanonicalFilter(
                field="Venda.data",
                operator=ComparisonOperator.BETWEEN,
                value=["2026-06-01", "2026-06-30"]
            )
        ]
    )
    
    node_child = ConversationNode(
        node_id="child_1",
        parent_id="root",
        user_query="E no mes passado?",
        canonical_plan=c_plan_child,
        dashboard_state=db_state
    )
    
    graph = ConversationGraph(
        nodes={
            "root": node_root,
            "child_1": node_child
        },
        current_node_id="child_1"
    )
    
    assert len(graph.nodes) == 2
    assert graph.current_node_id == "child_1"
    assert graph.nodes["child_1"].parent_id == "root"
    print("SUCCESS: Grafo de conversacao estruturado e validado com sucesso!")

if __name__ == "__main__":
    validate_tracked_model_inheritance()
