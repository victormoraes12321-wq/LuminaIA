"""Legacy AI contracts shared by the CIE facade and compatibility bridge."""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ModelViolationError(Exception):
    pass


class AIServiceError(Exception):
    pass


class PlanFiltersSchema(BaseModel):
    date_range: str = ""
    products: list[str] = Field(default_factory=list)
    customers: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)


class PlanVisualizationSchema(BaseModel):
    type: str = "TABLE"
    layout_priority: str = "ALTA"


class StructuredPlanSchema(BaseModel):
    request_id: str
    intent: str
    query_type: str
    metrics: list[str] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    filters: PlanFiltersSchema = Field(default_factory=PlanFiltersSchema)
    comparisons: list[str] = Field(default_factory=list)
    visualization: PlanVisualizationSchema = Field(default_factory=PlanVisualizationSchema)
    requires_insight: bool = True
    confidence_score: float = 0.0


class IntentionResponse(BaseModel):
    view_catalog_id: uuid.UUID | None = None
    confianca: float = 0.0
    parametros: dict[str, str] = Field(default_factory=dict)
    justificativa: str = ""
    fora_de_escopo: bool = False
    mensagem_bloqueio: str | None = None
    resposta_direta: str | None = None
    chart_type_sobrescrever: str | None = None
    chart_types_solicitados: list[str] | None = None
    plano_estruturado: StructuredPlanSchema | None = None
    operacao: str | None = None
    entidade_alvo: str | None = None
    quantidade_limite: int | None = None
    periodo_referencia: str | None = None
    is_comparacao: bool = False
    comparativo_detalhe: str | None = None
    visualizacao_preferida: str | None = None
    nivel_confianca: str | None = None
    telemetry: dict[str, Any] | None = None
