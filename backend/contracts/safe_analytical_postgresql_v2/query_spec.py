from __future__ import annotations

from typing import Any, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from contracts.safe_analytical_postgresql_v2.identity import (
    AnalyticalBudgetDecisionV2,
    AnalyticalFilterOperatorV2,
)


class StrictAnalyticalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AnalyticalFilterExpressionV2(StrictAnalyticalModel):
    dimension_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    operator: AnalyticalFilterOperatorV2
    values: List[Any] = Field(default_factory=list)


class AnalyticalFilterGroupV2(StrictAnalyticalModel):
    logical_operator: str = Field(default="AND", pattern=r"^(AND|OR)$")
    expressions: List[AnalyticalFilterExpressionV2] = Field(default_factory=list)


class AnalyticalMetricSelectV2(StrictAnalyticalModel):
    metric_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    alias: Optional[str] = None


class AnalyticalDimensionSelectV2(StrictAnalyticalModel):
    dimension_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    alias: Optional[str] = None


class AnalyticalOrderByV2(StrictAnalyticalModel):
    field: str = Field(pattern=r"^[a-z0-9_.]+$")
    direction: str = Field(default="ASC", pattern=r"^(ASC|DESC)$")


class AnalyticalPaginationV2(StrictAnalyticalModel):
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0, le=10000)


class AnalyticalQueryBudgetV2(StrictAnalyticalModel):
    maximum_relations: int = 5
    maximum_joins: int = 4
    maximum_metrics: int = 10
    maximum_dimensions: int = 10
    maximum_filters: int = 20
    maximum_rows: int = 1000
    maximum_columns: int = 50
    maximum_cells: int = 50000
    maximum_result_bytes: int = 10485760  # 10 MB
    maximum_timeout_seconds: float = 10.0
    complexity_score: int = 10
    budget_decision: AnalyticalBudgetDecisionV2 = AnalyticalBudgetDecisionV2.ALLOWED


class AnalyticalQuerySpecV2(StrictAnalyticalModel):
    spec_id: str = Field(min_length=1, max_length=128)
    dataset_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    metrics: List[AnalyticalMetricSelectV2] = Field(default_factory=list)
    dimensions: List[AnalyticalDimensionSelectV2] = Field(default_factory=list)
    filter_group: Optional[AnalyticalFilterGroupV2] = None
    group_by_dimensions: List[str] = Field(default_factory=list)
    order_by: List[AnalyticalOrderByV2] = Field(default_factory=list)
    pagination: AnalyticalPaginationV2 = Field(default_factory=AnalyticalPaginationV2)
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    expected_shape: str = Field(default="TABLE", pattern=r"^(SCALAR|SERIES|TABLE|RANKING)$")
    locale: str = "pt-BR"
    timezone: str = "America/Sao_Paulo"
