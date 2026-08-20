from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from contracts.safe_analytical_postgresql_v2.identity import (
    SAFE_ANALYTICAL_POSTGRESQL_VERSION,
    AnalyticalTenantStrategyV2,
)


class StrictAnalyticalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AnalyticalBindParameterV2(StrictAnalyticalModel):
    name: str = Field(pattern=r"^[a-zA-Z0-9_]+$")
    value: Any
    value_type: str = Field(default="STRING", pattern=r"^(STRING|INTEGER|DECIMAL|BOOLEAN|DATE|TIMESTAMP|UUID|LIST)$")


class AnalyticalIsolationProofV2(StrictAnalyticalModel):
    tenant_strategy: AnalyticalTenantStrategyV2
    tenant_id: str
    tenant_predicate_applied: bool = True
    tenant_column: Optional[str] = None
    dataset_id: str
    relation_id: str
    connection_scope: str = "READ_ONLY_POSTGRESQL"
    proof_checksum: str = Field(min_length=16, max_length=64)
    validation_status: str = "VALIDATED"


class AnalyticalAuthorizationDecisionV2(StrictAnalyticalModel):
    is_authorized: bool = True
    user_id: str
    user_role: str
    tenant_id: str
    granted_permissions: List[str] = Field(default_factory=list)
    denied_reason: Optional[str] = None


class AnalyticalCompiledQueryV2(StrictAnalyticalModel):
    compiled_query_id: str = Field(min_length=1, max_length=128)
    contract_version: str = SAFE_ANALYTICAL_POSTGRESQL_VERSION
    sql_template: str = Field(min_length=10, max_length=10000)
    bind_parameters: List[AnalyticalBindParameterV2] = Field(default_factory=list)
    isolation_proof: AnalyticalIsolationProofV2
    query_fingerprint: str = Field(min_length=16, max_length=64)
    target_database: str = "POSTGRESQL_ANALYTICAL"
    statement_timeout_seconds: float = 10.0
    lock_timeout_seconds: float = 3.0
