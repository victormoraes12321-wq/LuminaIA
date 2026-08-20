"""Audit service for recording structural telemetry of post-sync insights v1.0."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.post_sync_insights_v2 import PostSyncInsightAuditEventModelV2


class PostSyncInsightAuditService:
    async def log_event(
        self,
        db: AsyncSession,
        tenant_id: str,
        action: str,
        user_id: str | None = None,
        insight_id: str | None = None,
        run_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        tenant_uuid = uuid.UUID(tenant_id)
        user_uuid = uuid.UUID(user_id) if user_id else None
        ins_uuid = uuid.UUID(insight_id) if insight_id else None
        run_uuid = uuid.UUID(run_id) if run_id else None

        event = PostSyncInsightAuditEventModelV2(
            id=uuid.uuid4(),
            tenant_id=tenant_uuid,
            user_id=user_uuid,
            action=action,
            insight_id=ins_uuid,
            run_id=run_uuid,
            details_json=details or {},
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()


audit_service = PostSyncInsightAuditService()
