from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from contracts.safe_analytical_postgresql_v2.identity import (
    SAFE_ANALYTICAL_POSTGRESQL_VERSION,
    AnalyticalColumnTypeV2,
)


class StrictAnalyticalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AnalyticalResultColumnV2(StrictAnalyticalModel):
    name: str
    column_type: AnalyticalColumnTypeV2
    nullable: bool = True
    canonical_id: Optional[str] = None


class AnalyticalResultRowV2(StrictAnalyticalModel):
    values: Dict[str, Any]


class AnalyticalResultStatisticsV2(StrictAnalyticalModel):
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    cell_count: int = Field(ge=0)
    execution_time_ms: float = Field(ge=0.0)
    bytes_serialized: int = Field(ge=0)
    truncated: bool = False
    truncation_reason: Optional[str] = None


class AnalyticalResultValidationV2(StrictAnalyticalModel):
    is_valid: bool = True
    schema_matched: bool = True
    shape_matched: bool = True
    decimal_preserved: bool = True
    null_policy_applied: bool = True
    tenant_isolation_verified: bool = True
    validation_warnings: List[str] = Field(default_factory=list)


class AnalyticalExecutionErrorV2(StrictAnalyticalModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class AnalyticalExecutionContextV2(StrictAnalyticalModel):
    request_id: str
    correlation_id: str
    tenant_id: str
    user_id: str
    user_role: str
    session_id: str
    reference_time: str
    read_only_transaction: bool = True


class AnalyticalExecutionResultV2(StrictAnalyticalModel):
    result_id: str = Field(min_length=1, max_length=128)
    contract_version: str = SAFE_ANALYTICAL_POSTGRESQL_VERSION
    compiled_query_id: str
    columns: List[AnalyticalResultColumnV2]
    rows: List[AnalyticalResultRowV2]
    statistics: AnalyticalResultStatisticsV2
    validation: AnalyticalResultValidationV2
    error: Optional[AnalyticalExecutionErrorV2] = None
