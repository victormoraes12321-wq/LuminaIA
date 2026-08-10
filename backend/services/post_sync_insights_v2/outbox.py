"""Outbox service for polling and processing pending post-sync insight jobs v1.0."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.post_sync_insights_v2 import PostSyncInsightRunRequestV2
from models.post_sync_insights_v2 import PostSyncInsightOutboxModelV2

logger = logging.getLogger("luminaai.services.post_sync_insights.outbox")


class PostSyncInsightOutboxServiceV2:
    async def fetch_pending_jobs(
        self,
        db: AsyncSession,
        limit: int = 10,
    ) -> list[PostSyncInsightOutboxModelV2]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(PostSyncInsightOutboxModelV2)
            .where(
                PostSyncInsightOutboxModelV2.status.in_(["PENDING", "FAILED"]),
                PostSyncInsightOutboxModelV2.attempts < PostSyncInsightOutboxModelV2.max_attempts,
                PostSyncInsightOutboxModelV2.next_attempt_at <= now,
            )
            .order_by(PostSyncInsightOutboxModelV2.created_at.asc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def mark_processed(
        self,
        db: AsyncSession,
        outbox_id: uuid.UUID,
    ) -> None:
        now = datetime.now(timezone.utc)
        stmt = select(PostSyncInsightOutboxModelV2).where(PostSyncInsightOutboxModelV2.id == outbox_id)
        res = await db.execute(stmt)
        entry = res.scalar_one_or_none()
        if entry:
            entry.status = "COMPLETED"
            entry.processed_at = now
            db.add(entry)
            await db.commit()

    async def mark_failed(
        self,
        db: AsyncSession,
        outbox_id: uuid.UUID,
        error_msg: str,
    ) -> None:
        stmt = select(PostSyncInsightOutboxModelV2).where(PostSyncInsightOutboxModelV2.id == outbox_id)
        res = await db.execute(stmt)
        entry = res.scalar_one_or_none()
        if entry:
            entry.attempts += 1
            entry.last_error = error_msg
            if entry.attempts >= entry.max_attempts:
                entry.status = "DEAD_LETTER"
            else:
                entry.status = "FAILED"
            db.add(entry)
            await db.commit()


outbox_service = PostSyncInsightOutboxServiceV2()
