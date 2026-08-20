"""
LuminaAI — Smart Cache Evaluation Contracts
lumina.smart-cache-materialization/1.0
"""
from typing import Dict
from pydantic import BaseModel, Field, ConfigDict, JsonValue


class SmartCacheEvaluationCaseV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    tenant_id: str
    description: str
    scenario_type: str
    canonical_query_fingerprint: str
    expected_decision: str
    expected_freshness: str
    checksum: str
    is_active: bool = True


class SmartCacheEvaluationResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    result_id: str
    case_id: str
    case_checksum: str
    tenant_id: str
    actual_decision: str
    actual_freshness: str
    passed: bool
    details: Dict[str, JsonValue] = Field(default_factory=dict)
    evaluated_at: str
