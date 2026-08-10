"""Publication service for storing and making certified insights available v1.0."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.post_sync_insights_v2 import PostSyncInsightV2
from models.post_sync_insights_v2 import (
    PostSyncInsightEvidenceModelV2,
    PostSyncInsightModelV2,
)

logger = logging.getLogger("luminaai.services.post_sync_insights.publication")


def _to_uuid(val: str, prefix: str = "", seed: str = "") -> uuid.UUID:
    raw = val[len(prefix):] if prefix and val.startswith(prefix) else val
    try:
        return uuid.UUID(raw)
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_DNS, seed or val)


class PostSyncInsightPublicationService:
    async def publish_insights(
        self,
        db: AsyncSession,
        insights: list[PostSyncInsightV2],
    ) -> list[PostSyncInsightV2]:
        published: list[PostSyncInsightV2] = []

        for ins in insights:
            # Check idempotency / existence
            ins_uuid = _to_uuid(ins.insight_id, prefix="insight-", seed=f"{ins.tenant_id}:{ins.fingerprint}")
            tenant_uuid = _to_uuid(ins.tenant_id)
            sync_run_uuid = _to_uuid(ins.sync_run_id)

            stmt = select(PostSyncInsightModelV2).where(
                PostSyncInsightModelV2.id == ins_uuid,
                PostSyncInsightModelV2.tenant_id == tenant_uuid,
            )
            res = await db.execute(stmt)
            if res.scalar_one_or_none():
                continue

            model = PostSyncInsightModelV2(
                id=ins_uuid,
                tenant_id=tenant_uuid,
                sync_run_id=sync_run_uuid,
                run_id=sync_run_uuid,
                insight_type=ins.insight_type.value,
                category=ins.category.value,
                severity=ins.severity.value,
                lifecycle=ins.lifecycle.value,
                headline=ins.summary.headline,
                detail=ins.summary.detail,
                metric_key=ins.evidence.metric_key,
                fingerprint=ins.fingerprint,
                insight_json=ins.model_dump(mode="json"),
                published_at=ins.published_at,
                expires_at=ins.expires_at,
            )
            db.add(model)
            await db.flush()

            evidence_uuid = _to_uuid(ins.evidence.evidence_id, prefix="ev-", seed=f"{ins.tenant_id}:{ins.evidence.checksum}")
            evidence_model = PostSyncInsightEvidenceModelV2(
                id=evidence_uuid,
                tenant_id=tenant_uuid,
                insight_id=ins_uuid,
                sync_run_id=sync_run_uuid,
                metric_key=ins.evidence.metric_key,
                evidence_json=ins.evidence.model_dump(mode="json"),
                checksum=ins.evidence.checksum,
            )
            db.add(evidence_model)
            await db.flush()
            published.append(ins)

        await db.commit()
        return published


publication_service = PostSyncInsightPublicationService()
