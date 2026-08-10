"""Prioritization service for ranking and capping post-sync insight candidates v1.0."""
from __future__ import annotations

from contracts.post_sync_insights_v2 import (
    PostSyncInsightCandidateV2,
    PostSyncInsightPolicyV2,
)


class PostSyncInsightPrioritizationService:
    def prioritize(
        self,
        candidates: list[PostSyncInsightCandidateV2],
        policy: PostSyncInsightPolicyV2,
    ) -> list[PostSyncInsightCandidateV2]:
        # Sort deterministically by final_score DESC, then candidate_id ASC
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (-c.score.final_score, c.candidate_id),
        )
        max_count = policy.priority_policy.max_insights_per_run
        return sorted_candidates[:max_count]


prioritization_service = PostSyncInsightPrioritizationService()
