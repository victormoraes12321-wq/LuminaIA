"""
LuminaAI — Smart Cache Invalidation Service
lumina.smart-cache-materialization/1.0
"""
import logging
from typing import Optional
from contracts.smart_cache_materialization_v2 import (
    CacheInvalidationRequestV2,
    CacheInvalidationResultV2,
)
from .repository import SmartCacheRepository

logger = logging.getLogger(__name__)


class SmartCacheInvalidationService:
    def __init__(self, repository: SmartCacheRepository):
        self.repository = repository

    async def invalidate(
        self, trusted_tenant_id: str, request: CacheInvalidationRequestV2
    ) -> CacheInvalidationResultV2:
        tenant_id = trusted_tenant_id
        count = 0

        if request.invalidation_scope.value == "TAG" and request.target_identifier:
            count = await self.repository.invalidate_entries_by_tag(tenant_id, request.target_identifier)
        elif request.invalidation_scope.value in {
            "METRIC", "CATALOG", "SYNC", "TENANT", "PERMISSION",
            "VALIDATION_POLICY", "MATERIALIZATION",
        }:
            target = request.target_identifier or request.invalidation_scope.value.lower()
            await self.repository.increment_generation(tenant_id, target, request.reason)
            count = 1  # Incremented generation invalidates dependent cache entries
        else:
            raise ValueError("invalidation scope requires a governed target")

        await self.repository.log_event(
            tenant_id=tenant_id,
            event_type="SMART_CACHE_INVALIDATED",
            reason_code=request.reason,
            details={"scope": request.invalidation_scope.value, "target": request.target_identifier, "count": count},
        )

        return CacheInvalidationResultV2(
            success=True,
            invalidated_count=count,
            tenant_id=tenant_id,
            invalidation_scope=request.invalidation_scope,
        )
