"""Validation service for post-sync insight candidates v1.0."""
from __future__ import annotations

from contracts.post_sync_insights_v2 import (
    PostSyncInsightCandidateV2,
    PostSyncInsightPolicyV2,
)


class PostSyncInsightValidationService:
    def validate_candidate(
        self,
        candidate: PostSyncInsightCandidateV2,
        policy: PostSyncInsightPolicyV2,
    ) -> bool:
        if candidate.tenant_id != policy.tenant_id:
            return False
        if not candidate.evidence.checksum:
            return False
        if not candidate.evidence.reconciliation_verified and policy.suppression_policy.suppress_on_reconciliation_error:
            # Allow RECONCILIATION_VARIANCE type itself, but suppress business insights if reconciliation failed
            if candidate.insight_type.value not in {"RECONCILIATION_VARIANCE", "COMPLETENESS_DEGRADED", "FRESHNESS_DEGRADED"}:
                return False
        return True


validation_service = PostSyncInsightValidationService()
