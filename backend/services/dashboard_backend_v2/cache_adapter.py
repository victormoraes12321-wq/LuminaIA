"""Adapter to the existing Smart Cache invalidation authority."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from contracts.smart_cache_materialization_v2 import CacheInvalidationRequestV2, InvalidationScope
from services.smart_cache_materialization.pipeline import SmartCachePipeline


class ExistingSmartCacheDashboardInvalidatorV2:
    def __init__(self, session: AsyncSession):
        self.pipeline = SmartCachePipeline(session)

    async def invalidate_dashboard(self, *, tenant_id: str, dashboard_id: str, semantic_checksum: str, generation: int) -> None:
        await self.pipeline.invalidation_service.invalidate(
            tenant_id,
            CacheInvalidationRequestV2(
                invalidation_scope=InvalidationScope.TAG,
                target_identifier=f"dashboard:{dashboard_id}:semantic:{semantic_checksum}",
                reason=f"dashboard-publication-generation-{generation}",
            ),
        )

