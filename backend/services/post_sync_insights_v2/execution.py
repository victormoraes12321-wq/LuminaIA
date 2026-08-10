"""Execution service for running deterministic post-sync detectors v1.0."""
from __future__ import annotations

import logging
from typing import Any

from contracts.post_sync_insights_v2 import (
    PostSyncInsightCandidateV2,
    PostSyncInsightPolicyV2,
    PostSyncInsightRunRequestV2,
)
from services.post_sync_insights_v2.detector_registry import detector_registry

logger = logging.getLogger("luminaai.services.post_sync_insights.execution")


class PostSyncInsightExecutionService:
    async def execute_detectors(
        self,
        request: PostSyncInsightRunRequestV2,
        policy: PostSyncInsightPolicyV2,
        ctx: dict[str, Any] | None = None,
    ) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        execution_context = ctx or {}

        for detector_id in policy.enabled_detectors:
            detector = detector_registry.get_detector(detector_id)
            if not detector:
                logger.warning("Detector %s not found in registry. Skipping.", detector_id)
                continue

            try:
                det_candidates = await detector.detect(request, policy, execution_context)
                candidates.extend(det_candidates)
            except Exception as exc:
                logger.error("Detector %s failed: %s", detector_id, exc)

        return candidates


execution_service = PostSyncInsightExecutionService()
