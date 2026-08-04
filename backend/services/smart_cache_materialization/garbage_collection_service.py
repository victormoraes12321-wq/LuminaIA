"""
LuminaAI — Smart Cache Garbage Collection Service
lumina.smart-cache-materialization/1.0
"""
import logging
from contracts.smart_cache_materialization_v2 import CacheEvictionResultV2
from .repository import MaterializationRepository, SmartCacheRepository

logger = logging.getLogger(__name__)


class SmartCacheGarbageCollectionService:
    def __init__(
        self,
        repository: SmartCacheRepository,
        materialization_repository: MaterializationRepository | None = None,
    ):
        self.repository = repository
        self.materialization_repository = materialization_repository

    async def execute_gc(
        self,
        tenant_id: str,
        dry_run: bool = True,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> CacheEvictionResultV2:
        count, bytes_freed, next_cursor = await self.repository.delete_expired_entries(
            tenant_id, dry_run=dry_run, limit=limit, cursor=cursor
        )
        if self.materialization_repository is not None and next_cursor is None and count < limit:
            materialization_count, materialization_bytes = (
                await self.materialization_repository.garbage_collect_retained_artifacts(
                    tenant_id,
                    dry_run=dry_run,
                    limit=limit - count,
                )
            )
            count += materialization_count
            bytes_freed += materialization_bytes
        await self.repository.log_event(
            tenant_id=tenant_id,
            event_type="SMART_CACHE_GC_COMPLETED" if not dry_run else "SMART_CACHE_GC_STARTED",
            reason_code="GC_SUCCESS",
            details={"evicted_count": count, "bytes_freed": bytes_freed, "dry_run": dry_run},
        )
        return CacheEvictionResultV2(
            evicted_count=count,
            bytes_freed=bytes_freed,
            dry_run=dry_run,
            next_cursor=next_cursor,
        )
