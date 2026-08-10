"""User state service for user-scoped acknowledgement and dismissal v1.0."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.post_sync_insights_v2 import (
    PostSyncInsightAcknowledgementV2,
    PostSyncInsightDismissalV2,
)
from models.post_sync_insights_v2 import (
    PostSyncInsightModelV2,
    PostSyncInsightUserStateModelV2,
)


class PostSyncInsightUserStateService:
    async def acknowledge_insight(
        self,
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        insight_id: str,
        note: str | None = None,
    ) -> PostSyncInsightAcknowledgementV2:
        tenant_uuid = uuid.UUID(tenant_id)
        user_uuid = uuid.UUID(user_id)
        raw_id = insight_id[8:] if insight_id.startswith("insight-") else insight_id
        insight_uuid = uuid.UUID(raw_id)

        # Check insight exists for tenant
        stmt_ins = select(PostSyncInsightModelV2).where(
            PostSyncInsightModelV2.id == insight_uuid,
            PostSyncInsightModelV2.tenant_id == tenant_uuid,
        )
        res_ins = await db.execute(stmt_ins)
        if not res_ins.scalar_one_or_none():
            raise ValueError(f"Insight {insight_id} not found for tenant {tenant_id}")

        stmt = select(PostSyncInsightUserStateModelV2).where(
            PostSyncInsightUserStateModelV2.tenant_id == tenant_uuid,
            PostSyncInsightUserStateModelV2.user_id == user_uuid,
            PostSyncInsightUserStateModelV2.insight_id == insight_uuid,
        )
        res = await db.execute(stmt)
        state = res.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if not state:
            state = PostSyncInsightUserStateModelV2(
                id=uuid.uuid4(),
                tenant_id=tenant_uuid,
                user_id=user_uuid,
                insight_id=insight_uuid,
                is_acknowledged=True,
                acknowledged_at=now,
                is_dismissed=False,
                updated_at=now,
            )
            db.add(state)
        else:
            state.is_acknowledged = True
            state.acknowledged_at = now
            state.updated_at = now
            db.add(state)

        await db.commit()
        return PostSyncInsightAcknowledgementV2(
            acknowledgement_id=f"ack-{state.id}",
            insight_id=insight_id,
            tenant_id=tenant_id,
            user_id=user_id,
            acknowledged_at=now,
            note=note,
        )

    async def dismiss_insight(
        self,
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        insight_id: str,
        reason: str = "NOT_RELEVANT",
    ) -> PostSyncInsightDismissalV2:
        tenant_uuid = uuid.UUID(tenant_id)
        user_uuid = uuid.UUID(user_id)
        raw_id = insight_id[8:] if insight_id.startswith("insight-") else insight_id
        insight_uuid = uuid.UUID(raw_id)

        stmt_ins = select(PostSyncInsightModelV2).where(
            PostSyncInsightModelV2.id == insight_uuid,
            PostSyncInsightModelV2.tenant_id == tenant_uuid,
        )
        res_ins = await db.execute(stmt_ins)
        if not res_ins.scalar_one_or_none():
            raise ValueError(f"Insight {insight_id} not found for tenant {tenant_id}")

        stmt = select(PostSyncInsightUserStateModelV2).where(
            PostSyncInsightUserStateModelV2.tenant_id == tenant_uuid,
            PostSyncInsightUserStateModelV2.user_id == user_uuid,
            PostSyncInsightUserStateModelV2.insight_id == insight_uuid,
        )
        res = await db.execute(stmt)
        state = res.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if not state:
            state = PostSyncInsightUserStateModelV2(
                id=uuid.uuid4(),
                tenant_id=tenant_uuid,
                user_id=user_uuid,
                insight_id=insight_uuid,
                is_acknowledged=False,
                is_dismissed=True,
                dismissed_at=now,
                dismiss_reason=reason,
                updated_at=now,
            )
            db.add(state)
        else:
            state.is_dismissed = True
            state.dismissed_at = now
            state.dismiss_reason = reason
            state.updated_at = now
            db.add(state)

        await db.commit()
        return PostSyncInsightDismissalV2(
            dismissal_id=f"dsm-{state.id}",
            insight_id=insight_id,
            tenant_id=tenant_id,
            user_id=user_id,
            dismissed_at=now,
            reason=reason,  # type: ignore
        )


user_state_service = PostSyncInsightUserStateService()
