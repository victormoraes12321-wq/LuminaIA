"""Trigger service for initiating post-sync insight runs after successful sync v1.0."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from contracts.post_sync_insights_v2 import (
    PostSyncInsightRunRequestV2,
    PostSyncInsightTriggerV2,
)
from models.post_sync_insights_v2 import PostSyncInsightOutboxModelV2


class PostSyncInsightTriggerServiceV2:
    async def trigger_post_sync_insights(
        self,
        db: AsyncSession,
        tenant_id: str,
        sync_run_id: str,
        watermark: str,
        reconciliation_status: str = "SUCCESS",
    ) -> PostSyncInsightTriggerV2:
        tenant_uuid = uuid.UUID(tenant_id)
        sync_uuid = uuid.UUID(sync_run_id)
        now = datetime.now(timezone.utc)
        idempotency_scope = f"outbox:{tenant_id}:{sync_run_id}"

        payload = PostSyncInsightRunRequestV2(
            tenant_id=tenant_id,
            sync_run_id=sync_run_id,
            source_id="VW_VENDAS_LM",
            source_version="1.0.0",
            watermark=watermark,
            reconciliation_status=reconciliation_status,
            force_replay=False,
        ).model_dump(mode="json")

        outbox_entry = PostSyncInsightOutboxModelV2(
            id=uuid.uuid4(),
            tenant_id=tenant_uuid,
            sync_run_id=sync_uuid,
            status="PENDING",
            attempts=0,
            max_attempts=3,
            idempotency_scope=idempotency_scope,
            payload_json=payload,
            next_attempt_at=now,
            created_at=now,
        )
        db.add(outbox_entry)
        await db.commit()

        return PostSyncInsightTriggerV2(
            trigger_id=f"trg-{outbox_entry.id}",
            tenant_id=tenant_id,
            sync_run_id=sync_run_id,
            triggered_at=now,
            status="QUEUED",
        )


trigger_service = PostSyncInsightTriggerServiceV2()
