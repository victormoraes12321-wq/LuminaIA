"""Planning service for post-sync insights v1.0."""
from __future__ import annotations

import hashlib
from contracts.post_sync_insights_v2 import (
    PostSyncInsightDetectorPlanV2,
    PostSyncInsightDimensionPlanV2,
    PostSyncInsightMetricPlanV2,
    PostSyncInsightPolicyV2,
    PostSyncInsightRunRequestV2,
)


class PostSyncInsightPlanningService:
    def create_plan(
        self,
        request: PostSyncInsightRunRequestV2,
        policy: PostSyncInsightPolicyV2,
    ) -> dict[str, object]:
        detector_plans: list[PostSyncInsightDetectorPlanV2] = []
        for det_id in policy.enabled_detectors:
            detector_plans.append(
                PostSyncInsightDetectorPlanV2(
                    detector_id=det_id,
                    detector_version="1.0.0",
                    supported_types=(),
                    target_metric_keys=("faturamento_comercial", "total_bruto"),
                    estimated_query_count=1,
                )
            )

        metrics = [
            PostSyncInsightMetricPlanV2(metric_key="faturamento_comercial", formula="SUM(ptotal_)", unit="BRL", grain="periodo"),
            PostSyncInsightMetricPlanV2(metric_key="desconto_total", formula="SUM(pdesconto_)", unit="BRL", grain="periodo"),
        ]
        dimensions = [
            PostSyncInsightDimensionPlanV2(dimension_key="produto", top_n=5),
            PostSyncInsightDimensionPlanV2(dimension_key="vendedor", top_n=5),
        ]

        raw_checksum = f"{request.tenant_id}:{request.sync_run_id}:{policy.checksum}"
        plan_checksum = hashlib.sha256(raw_checksum.encode()).hexdigest()

        return {
            "request": request.model_dump(mode="json"),
            "policy_id": policy.policy_id,
            "policy_version": policy.policy_version,
            "detector_plans": [dp.model_dump(mode="json") for dp in detector_plans],
            "metrics": [m.model_dump(mode="json") for m in metrics],
            "dimensions": [d.model_dump(mode="json") for d in dimensions],
            "checksum": plan_checksum,
        }


planning_service = PostSyncInsightPlanningService()
