"""Pure deterministic smart-cache eligibility authority."""
from __future__ import annotations

from contracts.smart_cache_materialization_v2 import (
    CacheDecision,
    CacheEligibilityDecisionV2,
    CacheEligibilityRequestV2,
    CertificationStatus,
    DataClassification,
    FreshnessStatus,
    SmartCachePolicyV2,
)


class SmartCacheEligibilityEngine:
    def evaluate(
        self,
        request: CacheEligibilityRequestV2,
        policy: SmartCachePolicyV2,
    ) -> CacheEligibilityDecisionV2:
        if request.cache_type in policy.disallowed_cache_types:
            return self._blocked(CacheDecision.CLASSIFICATION_BLOCKED, "CACHE_TYPE_FORBIDDEN")
        if request.data_classification in {
            DataClassification.PII,
            DataClassification.SECRET,
            DataClassification.FORBIDDEN,
        } or request.has_pii or request.is_row_level:
            return self._blocked(CacheDecision.CLASSIFICATION_BLOCKED, "CLASSIFICATION_FORBIDDEN")
        if request.certification_status is CertificationStatus.VALID_WITH_WARNINGS:
            if not policy.allow_valid_with_warnings:
                return self._blocked(CacheDecision.CERTIFICATION_INVALID, "WARNINGS_NOT_ALLOWED")
        elif request.certification_status is not CertificationStatus.VALID:
            return self._blocked(CacheDecision.CERTIFICATION_INVALID, "CERTIFICATION_NOT_VALID")
        if not request.tenant_proof_valid:
            return self._blocked(CacheDecision.INVALID, "TENANT_PROOF_MISSING")
        if not request.query_fingerprint_valid:
            return self._blocked(CacheDecision.INVALID, "QUERY_FINGERPRINT_MISSING")
        if not request.result_checksum_valid:
            return self._blocked(CacheDecision.CHECKSUM_MISMATCH, "RESULT_CHECKSUM_INVALID")
        if not request.metric_fingerprints_valid:
            return self._blocked(CacheDecision.INVALID, "METRIC_FINGERPRINT_INVALID")
        if request.source_freshness is not FreshnessStatus.FRESH:
            return self._blocked(CacheDecision.STALE, "SOURCE_NOT_FRESH")
        if not request.is_complete or request.is_partial:
            return self._blocked(CacheDecision.BYPASS, "RESULT_PARTIAL")
        if request.is_truncated:
            return self._blocked(CacheDecision.BYPASS, "RESULT_TRUNCATED")
        if request.has_ambiguity:
            return self._blocked(CacheDecision.BYPASS, "AMBIGUOUS_RESULT")
        if request.timed_out:
            return self._blocked(CacheDecision.BYPASS, "EXECUTION_TIMEOUT")
        if request.cancelled:
            return self._blocked(CacheDecision.BYPASS, "EXECUTION_CANCELLED")
        if request.has_error:
            return self._blocked(CacheDecision.ERROR, "EXECUTION_ERROR")
        if request.payload_size_bytes > policy.max_payload_bytes:
            return self._blocked(CacheDecision.BYPASS, "PAYLOAD_TOO_LARGE")
        return CacheEligibilityDecisionV2(
            eligible=True,
            decision=CacheDecision.MISS,
            reason_code="ELIGIBLE",
        )

    @staticmethod
    def _blocked(decision: CacheDecision, reason: str) -> CacheEligibilityDecisionV2:
        return CacheEligibilityDecisionV2(
            eligible=False,
            decision=decision,
            reason_code=reason,
        )
