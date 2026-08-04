"""Pure eligibility request/decision contracts."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .identity import (
    CacheDecision,
    CacheType,
    CertificationStatus,
    DataClassification,
    FreshnessStatus,
)


class CacheEligibilityRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cache_type: CacheType
    certification_status: CertificationStatus
    tenant_proof_valid: bool
    query_fingerprint_valid: bool
    result_checksum_valid: bool
    metric_fingerprints_valid: bool
    source_freshness: FreshnessStatus
    is_complete: bool
    is_partial: bool = False
    is_truncated: bool = False
    has_pii: bool = False
    is_row_level: bool = False
    has_ambiguity: bool = False
    timed_out: bool = False
    cancelled: bool = False
    has_error: bool = False
    payload_size_bytes: int = Field(default=0, ge=0)
    data_classification: DataClassification = DataClassification.INTERNAL


class CacheEligibilityDecisionV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    eligible: bool
    decision: CacheDecision
    reason_code: str = Field(min_length=1, max_length=128)
