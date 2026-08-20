"""Main facade for post-sync insights v1.0."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.post_sync_insights_v2 import (
    POST_SYNC_INSIGHTS_CONTRACT_VERSION,
    PostSyncInsightAcknowledgementV2,
    PostSyncInsightCandidateV2,
    PostSyncInsightDetailV2,
    PostSyncInsightDismissalV2,
    PostSyncInsightLifecycleV2,
    PostSyncInsightListItemV2,
    PostSyncInsightListRequestV2,
    PostSyncInsightPolicyV2,
    PostSyncInsightRunRequestV2,
    PostSyncInsightRunResultV2,
    PostSyncInsightRunV2,
    PostSyncInsightV2,
    PostSyncInsightWarningV2,
)
from models.post_sync_insights_v2 import (
    PostSyncInsightModelV2,
    PostSyncInsightPolicyModelV2,
    PostSyncInsightRunModelV2,
    PostSyncInsightUserStateModelV2,
)
from services.post_sync_insights_v2.certification import certification_service
from services.post_sync_insights_v2.deduplication import deduplication_service
from services.post_sync_insights_v2.execution import execution_service
from services.post_sync_insights_v2.planning import planning_service
from services.post_sync_insights_v2.policy import get_default_post_sync_policy
from services.post_sync_insights_v2.prioritization import prioritization_service
from services.post_sync_insights_v2.publication import publication_service
from services.post_sync_insights_v2.validation import validation_service

logger = logging.getLogger("luminaai.services.post_sync_insights.facade")


def _to_uuid(val: str, prefix: str = "", seed: str = "") -> uuid.UUID:
    raw = val[len(prefix):] if prefix and val.startswith(prefix) else val
    try:
        return uuid.UUID(raw)
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_DNS, seed or val)


import json


def _validate_json_dict(model_cls: type[Any], data: dict[str, Any]) -> Any:
    return model_cls.model_validate_json(json.dumps(data))


class PostSyncInsightsServiceV2:
    async def get_active_policy(
        self,
        db: AsyncSession,
        tenant_id: str,
    ) -> PostSyncInsightPolicyV2:
        tenant_uuid = uuid.UUID(tenant_id)
        stmt = (
            select(PostSyncInsightPolicyModelV2)
            .where(
                PostSyncInsightPolicyModelV2.tenant_id == tenant_uuid,
                PostSyncInsightPolicyModelV2.enabled.is_(True),
            )
            .order_by(PostSyncInsightPolicyModelV2.created_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        row = res.scalar_one_or_none()
        if row:
            return _validate_json_dict(PostSyncInsightPolicyV2, row.policy_json)

        default_policy = get_default_post_sync_policy(tenant_id)
        p_uuid = _to_uuid(default_policy.policy_id, prefix="policy-")
        policy_model = PostSyncInsightPolicyModelV2(
            id=p_uuid,
            tenant_id=tenant_uuid,
            policy_version=default_policy.policy_version,
            enabled=default_policy.enabled,
            policy_json=default_policy.model_dump(mode="json"),
            checksum=default_policy.checksum or "default-policy-checksum",
            lock_version=1,
            schema_version="lumina.post-sync-insights/1.0",
        )
        db.add(policy_model)
        await db.flush()
        return default_policy

    async def run_post_sync_pipeline(
        self,
        db: AsyncSession,
        request: PostSyncInsightRunRequestV2,
        context_override: dict[str, Any] | None = None,
    ) -> PostSyncInsightRunResultV2:
        tenant_uuid = uuid.UUID(request.tenant_id)
        policy = await self.get_active_policy(db, request.tenant_id)
        run_uuid = uuid.uuid4()
        started_at = datetime.now(timezone.utc)

        # Handle blocked / failed sync run
        if request.reconciliation_status in {"FAILED", "BLOCKED"} and policy.suppression_policy.suppress_on_reconciliation_error:
            run_model = PostSyncInsightRunModelV2(
                id=run_uuid,
                tenant_id=tenant_uuid,
                sync_run_id=uuid.UUID(request.sync_run_id),
                policy_id=uuid.UUID(policy.policy_id[7:] if policy.policy_id.startswith("policy-") else str(uuid.uuid4())),
                policy_version=policy.policy_version,
                status=PostSyncInsightLifecycleV2.BLOCKED.value,
                candidates_count=0,
                published_count=0,
                suppressed_count=0,
                error_message="Reconciliation blocked or failed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            db.add(run_model)
            await db.commit()

            run_dto = PostSyncInsightRunV2(
                run_id=f"run-{run_uuid}",
                contract_version=POST_SYNC_INSIGHTS_CONTRACT_VERSION,
                tenant_id=request.tenant_id,
                sync_run_id=request.sync_run_id,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                status=PostSyncInsightLifecycleV2.BLOCKED,
                candidates_count=0,
                published_count=0,
                suppressed_count=0,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                error_message="Reconciliation blocked or failed",
            )
            return PostSyncInsightRunResultV2(
                run=run_dto,
                published_insights=(),
                warnings=(PostSyncInsightWarningV2(code="RECONCILIATION_BLOCKED", message="Sync reconciliation failed or blocked."),),
            )

        # Execute pipeline steps
        plan = planning_service.create_plan(request, policy)
        raw_candidates = await execution_service.execute_detectors(request, policy, context_override)

        # Validate candidates
        valid_candidates = [c for c in raw_candidates if validation_service.validate_candidate(c, policy)]

        # Fetch existing published insights for deduplication
        existing_stmt = select(PostSyncInsightModelV2).where(
            PostSyncInsightModelV2.tenant_id == tenant_uuid,
            PostSyncInsightModelV2.lifecycle == PostSyncInsightLifecycleV2.PUBLISHED.value,
        )
        existing_res = await db.execute(existing_stmt)
        existing_insights = [_validate_json_dict(PostSyncInsightV2, row.insight_json) for row in existing_res.scalars().all()]

        deduped_candidates, suppressed_count = deduplication_service.filter_candidates(valid_candidates, existing_insights, policy)
        prioritized_candidates = prioritization_service.prioritize(deduped_candidates, policy)

        # Certify
        certified_insights = [certification_service.certify_candidate(c) for c in prioritized_candidates]

        # Insert run_model FIRST so FK constraint on insights is satisfied
        run_uuid = uuid.UUID(request.sync_run_id)
        run_model = PostSyncInsightRunModelV2(
            id=run_uuid,
            tenant_id=tenant_uuid,
            sync_run_id=run_uuid,
            policy_id=_to_uuid(policy.policy_id, prefix="policy-"),
            policy_version=policy.policy_version,
            status=PostSyncInsightLifecycleV2.PUBLISHED.value,
            candidates_count=len(raw_candidates),
            published_count=len(certified_insights),
            suppressed_count=suppressed_count,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run_model)
        await db.flush()

        # Publish insights
        published_insights = await publication_service.publish_insights(db, certified_insights)

        completed_at = datetime.now(timezone.utc)
        run_model.completed_at = completed_at
        run_model.published_count = len(published_insights)
        await db.commit()

        run_dto = PostSyncInsightRunV2(
            run_id=f"run-{run_uuid}",
            contract_version=POST_SYNC_INSIGHTS_CONTRACT_VERSION,
            tenant_id=request.tenant_id,
            sync_run_id=request.sync_run_id,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            status=PostSyncInsightLifecycleV2.PUBLISHED,
            candidates_count=len(raw_candidates),
            published_count=len(published_insights),
            suppressed_count=suppressed_count,
            started_at=started_at,
            completed_at=completed_at,
        )

        return PostSyncInsightRunResultV2(
            run=run_dto,
            published_insights=tuple(published_insights),
            warnings=(),
        )

    async def list_insights(
        self,
        db: AsyncSession,
        req: PostSyncInsightListRequestV2,
        user_id: str | None = None,
    ) -> tuple[list[PostSyncInsightListItemV2], str | None]:
        tenant_uuid = uuid.UUID(req.tenant_id)
        stmt = select(PostSyncInsightModelV2).where(PostSyncInsightModelV2.tenant_id == tenant_uuid)

        if req.severity:
            stmt = stmt.where(PostSyncInsightModelV2.severity == req.severity.value)
        if req.category:
            stmt = stmt.where(PostSyncInsightModelV2.category == req.category.value)
        if req.lifecycle:
            stmt = stmt.where(PostSyncInsightModelV2.lifecycle == req.lifecycle.value)
        if req.metric_key:
            stmt = stmt.where(PostSyncInsightModelV2.metric_key == req.metric_key)

        stmt = stmt.order_by(PostSyncInsightModelV2.published_at.desc()).limit(req.limit + 1)
        res = await db.execute(stmt)
        rows = list(res.scalars().all())

        has_more = len(rows) > req.limit
        results = rows[:req.limit]
        next_cursor = str(results[-1].id) if has_more and results else None

        items: list[PostSyncInsightListItemV2] = []
        user_uuid = uuid.UUID(user_id) if user_id else None

        for row in results:
            ins_json = row.insight_json
            ins_dto = _validate_json_dict(PostSyncInsightV2, ins_json)

            is_ack = False
            is_dsm = False
            if user_uuid:
                u_stmt = select(PostSyncInsightUserStateModelV2).where(
                    PostSyncInsightUserStateModelV2.tenant_id == tenant_uuid,
                    PostSyncInsightUserStateModelV2.user_id == user_uuid,
                    PostSyncInsightUserStateModelV2.insight_id == row.id,
                )
                u_res = await db.execute(u_stmt)
                ustate = u_res.scalar_one_or_none()
                if ustate:
                    is_ack = ustate.is_acknowledged
                    is_dsm = ustate.is_dismissed

            if is_dsm and not req.include_dismissed:
                continue

            items.append(
                PostSyncInsightListItemV2(
                    insight_id=ins_dto.insight_id,
                    insight_type=ins_dto.insight_type,
                    category=ins_dto.category,
                    severity=ins_dto.severity,
                    lifecycle=ins_dto.lifecycle,
                    headline=ins_dto.summary.headline,
                    metric_key=ins_dto.evidence.metric_key,
                    metric_label=ins_dto.evidence.metric_label,
                    formatted_delta=ins_dto.evidence.comparison.formatted_delta,
                    published_at=ins_dto.published_at,
                    is_acknowledged=is_ack,
                    is_dismissed=is_dsm,
                )
            )

        return items, next_cursor

    async def get_insight_detail(
        self,
        db: AsyncSession,
        tenant_id: str,
        insight_id: str,
        user_id: str | None = None,
    ) -> PostSyncInsightDetailV2:
        tenant_uuid = uuid.UUID(tenant_id)
        ins_uuid = uuid.UUID(insight_id[8:] if insight_id.startswith("insight-") else insight_id)

        stmt = select(PostSyncInsightModelV2).where(
            PostSyncInsightModelV2.id == ins_uuid,
            PostSyncInsightModelV2.tenant_id == tenant_uuid,
        )
        res = await db.execute(stmt)
        row = res.scalar_one_or_none()
        if not row:
            raise ValueError(f"Insight {insight_id} not found for tenant {tenant_id}")

        ins = _validate_json_dict(PostSyncInsightV2, row.insight_json)
        ack = None
        dsm = None

        if user_id:
            user_uuid = uuid.UUID(user_id)
            u_stmt = select(PostSyncInsightUserStateModelV2).where(
                PostSyncInsightUserStateModelV2.tenant_id == tenant_uuid,
                PostSyncInsightUserStateModelV2.user_id == user_uuid,
                PostSyncInsightUserStateModelV2.insight_id == ins_uuid,
            )
            u_res = await db.execute(u_stmt)
            ustate = u_res.scalar_one_or_none()
            if ustate:
                if ustate.is_acknowledged and ustate.acknowledged_at:
                    ack = PostSyncInsightAcknowledgementV2(
                        acknowledgement_id=f"ack-{ustate.id}",
                        insight_id=insight_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        acknowledged_at=ustate.acknowledged_at,
                    )
                if ustate.is_dismissed and ustate.dismissed_at:
                    dsm = PostSyncInsightDismissalV2(
                        dismissal_id=f"dsm-{ustate.id}",
                        insight_id=insight_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        dismissed_at=ustate.dismissed_at,
                        reason=ustate.dismiss_reason or "NOT_RELEVANT",  # type: ignore
                    )

        return PostSyncInsightDetailV2(
            insight=ins,
            user_acknowledgement=ack,
            user_dismissal=dsm,
        )


post_sync_insights_service = PostSyncInsightsServiceV2()
