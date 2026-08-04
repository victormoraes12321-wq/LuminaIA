"""
LuminaAI — Smart Cache Pipeline
lumina.smart-cache-materialization/1.0
"""
import logging
from typing import Optional, Dict
from pydantic import JsonValue
from sqlalchemy.ext.asyncio import AsyncSession
from contracts.smart_cache_materialization_v2 import (
    CacheScopeV2,
    CacheLookupRequestV2,
    CacheLookupResultV2,
    CacheWriteRequestV2,
    CacheWriteResultV2,
    CacheType,
    CacheEligibilityRequestV2,
)
from .repository import SmartCacheRepository, MaterializationRepository
from .policy_service import SmartCachePolicyService
from .key_builder import SmartCacheKeyBuilder
from .lookup_service import SmartCacheLookupService
from .write_service import SmartCacheWriteService
from .invalidation_service import SmartCacheInvalidationService

logger = logging.getLogger(__name__)


class SmartCachePipeline:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache_repo = SmartCacheRepository(session)
        self.mat_repo = MaterializationRepository(session)
        self.policy_service = SmartCachePolicyService()
        self.lookup_service = SmartCacheLookupService(self.cache_repo, self.policy_service)
        self.write_service = SmartCacheWriteService(self.cache_repo, self.policy_service)
        self.invalidation_service = SmartCacheInvalidationService(self.cache_repo)

    async def lookup_certified_analytical_result(
        self,
        *,
        scope: CacheScopeV2,
        canonical_query_fingerprint: str,
        analytical_catalog_version: str,
        metric_fingerprints: list[str],
        filter_structure_fingerprint: str = "",
        canonical_period_fingerprint: str = "",
        source_sync_version: str = "v1",
        source_watermark: str = "unknown",
        compiler_version: str = "v1",
        tool_registry_snapshot: str = "v1",
        generation_counters: Optional[dict[str, int]] = None,
    ) -> CacheLookupResultV2:
        req = CacheLookupRequestV2(
            scope=scope,
            cache_type=CacheType.CERTIFIED_ANALYTICAL_RESULT,
            canonical_query_fingerprint=canonical_query_fingerprint,
            analytical_catalog_version=analytical_catalog_version,
            metric_fingerprints=metric_fingerprints,
            filter_structure_fingerprint=filter_structure_fingerprint,
            canonical_period_fingerprint=canonical_period_fingerprint,
            source_sync_version=source_sync_version,
            source_watermark=source_watermark,
            compiler_version=compiler_version,
            tool_registry_snapshot=tool_registry_snapshot,
            generation_counters=generation_counters or {},
        )
        return await self.lookup_service.lookup(req)

    async def write_certified_analytical_result(
        self,
        *,
        scope: CacheScopeV2,
        canonical_query_fingerprint: str,
        analytical_catalog_version: str,
        metric_fingerprints: list[str],
        payload: Dict[str, JsonValue],
        certification_id: str,
        tenant_proof_id: str,
        eligibility: CacheEligibilityRequestV2,
        source_sync_version: str = "v1",
        source_watermark: str = "unknown",
        compiler_version: str = "v1",
        tool_registry_snapshot: str = "v1",
        generation_counters: Optional[dict[str, int]] = None,
        dependency_tags: Optional[list[str]] = None,
    ) -> CacheWriteResultV2:
        key = SmartCacheKeyBuilder.build_key(
            cache_type=CacheType.CERTIFIED_ANALYTICAL_RESULT,
            scope=scope,
            canonical_query_fingerprint=canonical_query_fingerprint,
            analytical_catalog_version=analytical_catalog_version,
            metric_fingerprints=metric_fingerprints,
            source_sync_version=source_sync_version,
            source_watermark=source_watermark,
            compiler_version=compiler_version,
            tool_registry_snapshot=tool_registry_snapshot,
            generation_counters=generation_counters or {},
        )
        req = CacheWriteRequestV2(
            scope=scope,
            cache_key=key,
            payload=payload,
            certification_id=certification_id,
            tenant_proof_id=tenant_proof_id,
            eligibility=eligibility,
            dependency_tags=dependency_tags or [],
        )
        return await self.write_service.write(req)
