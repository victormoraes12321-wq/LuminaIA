from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from contracts.safe_analytical_postgresql_v2.identity import (
    SAFE_ANALYTICAL_POSTGRESQL_VERSION,
    AnalyticalTenantStrategyV2,
)


class StrictAnalyticalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AnalyticalQueryFingerprintV2(StrictAnalyticalModel):
    fingerprint_hash: str = Field(min_length=16, max_length=64)
    catalog_version: str = "1.0.0"
    compiler_version: str = "1.0.0"
    metric_ids: List[str] = Field(default_factory=list)
    dimension_ids: List[str] = Field(default_factory=list)
    dataset_id: str


class AnalyticalQueryProvenanceV2(StrictAnalyticalModel):
    provenance_id: str = Field(min_length=1, max_length=128)
    contract_version: str = SAFE_ANALYTICAL_POSTGRESQL_VERSION
    catalog_version: str = "1.0.0"
    dataset_id: str
    tenant_strategy: AnalyticalTenantStrategyV2
    isolation_proof_checksum: str = Field(min_length=16, max_length=64)
    query_fingerprint: str = Field(min_length=16, max_length=64)
    row_count: int = Field(ge=0)
    truncated: bool = False
    validation_status: str = "VALIDATED"
    execution_time_ms: float = Field(ge=0.0)
    executed_at: str


class AnalyticalAuditEventV2(StrictAnalyticalModel):
    event_id: str
    event_type: str
    tenant_id: str
    user_id: str
    details: Dict[str, Any]
    timestamp: str


class AnalyticalEvaluationCaseV2(StrictAnalyticalModel):
    case_id: str
    description: str
    input_query_spec: Dict[str, Any]
    expected_row_count: int
    expected_first_value: Optional[Any] = None


class AnalyticalEvaluationResultV2(StrictAnalyticalModel):
    case_id: str
    passed: bool
    actual_row_count: int
    matched_value: bool = True
    error_message: Optional[str] = None
