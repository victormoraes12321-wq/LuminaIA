"""
LuminaAI — Smart Cache Statistics Service
lumina.smart-cache-materialization/1.0
"""
import logging
from contracts.smart_cache_materialization_v2 import CacheStatisticsV2, MaterializationStatisticsV2
from .repository import SmartCacheRepository, MaterializationRepository

logger = logging.getLogger(__name__)


class SmartCacheStatisticsService:
    def __init__(self, cache_repo: SmartCacheRepository, mat_repo: MaterializationRepository):
        self.cache_repo = cache_repo
        self.mat_repo = mat_repo

    async def get_cache_statistics(self, tenant_id: str) -> CacheStatisticsV2:
        values = await self.cache_repo.statistics(tenant_id)
        materializations = await self.mat_repo.statistics(tenant_id)
        return CacheStatisticsV2(
            tenant_id=tenant_id,
            **values,
            published_materializations_count=materializations["published_definitions"],
        )

    async def get_materialization_statistics(self, tenant_id: str) -> MaterializationStatisticsV2:
        return MaterializationStatisticsV2(
            tenant_id=tenant_id, **(await self.mat_repo.statistics(tenant_id))
        )
