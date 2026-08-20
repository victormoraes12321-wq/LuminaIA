"""Replay service for administrative idempotent post-sync insight reprocessing v1.0."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from contracts.post_sync_insights_v2 import (
    PostSyncInsightReplayRequestV2,
    PostSyncInsightRunRequestV2,
    PostSyncInsightRunResultV2,
)


class PostSyncInsightReplayService:
    async def replay_run(
        self,
        db: AsyncSession,
        replay_req: PostSyncInsightReplayRequestV2,
        service: Any,
    ) -> PostSyncInsightRunResultV2:
        run_req = PostSyncInsightRunRequestV2(
            tenant_id=replay_req.tenant_id,
            sync_run_id=replay_req.run_id,
            source_id="VW_VENDAS_LM",
            source_version="1.0.0",
            watermark=f"replay-{replay_req.run_id[:8]}",
            reconciliation_status="SUCCESS",
            force_replay=True,
        )
        return await service.run_post_sync_pipeline(db, run_req)


replay_service = PostSyncInsightReplayService()
