"""Evaluation service for testing post-sync insight detector precision offline v1.0."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from contracts.post_sync_insights_v2 import (
    PostSyncInsightEvaluationCaseV2,
    PostSyncInsightEvaluationResultV2,
)
from models.post_sync_insights_v2 import (
    PostSyncInsightEvaluationCaseModelV2,
    PostSyncInsightEvaluationResultModelV2,
)


class PostSyncInsightEvaluationService:
    async def run_evaluation(
        self,
        db: AsyncSession,
        case: PostSyncInsightEvaluationCaseV2,
        service: Any,
    ) -> PostSyncInsightEvaluationResultV2:
        res = await service.run_post_sync_pipeline(db, case.input_run_request)
        actual_types = tuple(i.insight_type for i in res.published_insights)

        expected_types_set = set(case.expected_insight_types)
        actual_types_set = set(actual_types)

        matched = tuple(expected_types_set.intersection(actual_types_set))
        missing = tuple(expected_types_set.difference(actual_types_set))

        count_ok = case.expected_min_insights <= len(actual_types) <= case.expected_max_insights
        types_ok = len(missing) == 0
        passed = count_ok and types_ok

        eval_res = PostSyncInsightEvaluationResultV2(
            case_id=case.case_id,
            passed=passed,
            actual_insights_count=len(actual_types),
            matched_types=matched,
            missing_types=missing,
            details=f"Evaluated {len(actual_types)} insights. Count OK: {count_ok}, Types OK: {types_ok}.",
        )

        tenant_uuid = uuid.UUID(case.input_run_request.tenant_id)

        # Save case & result to db
        case_model = PostSyncInsightEvaluationCaseModelV2(
            id=uuid.uuid4(),
            tenant_id=tenant_uuid,
            case_key=case.case_id,
            description=case.description,
            case_json=case.model_dump(mode="json"),
            created_at=datetime.now(timezone.utc),
        )
        res_model = PostSyncInsightEvaluationResultModelV2(
            id=uuid.uuid4(),
            tenant_id=tenant_uuid,
            case_key=case.case_id,
            passed=passed,
            result_json=eval_res.model_dump(mode="json"),
            executed_at=datetime.now(timezone.utc),
        )
        db.add(case_model)
        db.add(res_model)
        await db.commit()

        return eval_res


evaluation_service = PostSyncInsightEvaluationService()
