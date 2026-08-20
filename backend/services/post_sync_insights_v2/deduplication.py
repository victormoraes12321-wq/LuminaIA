"""Deduplication and suppression service for post-sync insights v1.0."""
from __future__ import annotations

from contracts.post_sync_insights_v2 import (
    PostSyncInsightCandidateV2,
    PostSyncInsightPolicyV2,
    PostSyncInsightV2,
)


class PostSyncInsightDeduplicationService:
    def filter_candidates(
        self,
        candidates: list[PostSyncInsightCandidateV2],
        existing_insights: list[PostSyncInsightV2],
        policy: PostSyncInsightPolicyV2,
    ) -> tuple[list[PostSyncInsightCandidateV2], int]:
        seen_fingerprints: set[str] = {i.fingerprint for i in existing_insights}
        filtered: list[PostSyncInsightCandidateV2] = []
        suppressed_count = 0

        for cand in candidates:
            if cand.fingerprint in seen_fingerprints:
                suppressed_count += 1
                continue
            seen_fingerprints.add(cand.fingerprint)
            filtered.append(cand)

        return filtered, suppressed_count


deduplication_service = PostSyncInsightDeduplicationService()
