"""
LuminaAI — Smart Cache Lookup Service
lumina.smart-cache-materialization/1.0
"""
import time
from datetime import datetime, timezone
import logging
from typing import Optional
from contracts.smart_cache_materialization_v2 import (
    CacheLookupRequestV2,
    CacheLookupResultV2,
    CacheDecision,
    FreshnessStatus,
    CacheEntryV2,
    CacheEntryMetadataV2,
    CacheEntryPayloadReferenceV2,
)
from .repository import SmartCacheRepository
from .key_builder import SmartCacheKeyBuilder
from .policy_service import SmartCachePolicyService
from .eligibility_engine import SmartCacheEligibilityEngine

logger = logging.getLogger(__name__)


class SmartCacheLookupService:
    def __init__(self, repository: SmartCacheRepository, policy_service: SmartCachePolicyService):
        self.repository = repository
        self.policy_service = policy_service
        self.eligibility_engine = SmartCacheEligibilityEngine()

    async def lookup(self, request: CacheLookupRequestV2) -> CacheLookupResultV2:
        start_time = time.time()
        tenant_id = request.scope.tenant_id
        policy = self.policy_service.get_cache_policy(tenant_id)

        # Build Key
        key = SmartCacheKeyBuilder.build_key(
            cache_type=request.cache_type,
            scope=request.scope,
            canonical_query_fingerprint=request.canonical_query_fingerprint,
            analytical_catalog_version=request.analytical_catalog_version,
            metric_fingerprints=request.metric_fingerprints,
            filter_structure_fingerprint=request.filter_structure_fingerprint,
            canonical_period_fingerprint=request.canonical_period_fingerprint,
            source_sync_version=request.source_sync_version,
            source_watermark=request.source_watermark,
            validation_policy_version=request.validation_policy_version,
            certification_contract_version=request.certification_contract_version,
            compiler_version=request.compiler_version,
            tool_registry_snapshot=request.tool_registry_snapshot,
            generation_counters=request.generation_counters,
        )
        checksum = key.compute_key_checksum()

        if not policy.enable_cache_read or request.cache_type in policy.disallowed_cache_types:
            latency = (time.time() - start_time) * 1000
            await self.repository.log_event(
                tenant_id=tenant_id,
                event_type="SMART_CACHE_LOOKUP",
                reason_code="CACHE_READ_DISABLED",
                cache_key_checksum=checksum,
                decision=CacheDecision.BYPASS.value,
            )
            return CacheLookupResultV2(
                decision=CacheDecision.BYPASS,
                reason_code="CACHE_READ_DISABLED",
                cache_key_checksum=checksum,
                lookup_latency_ms=latency,
            )

        # Lookup in Repository
        entry_model = await self.repository.get_entry_by_key_checksum(tenant_id, checksum)
        latency = (time.time() - start_time) * 1000

        if not entry_model:
            await self.repository.log_event(
                tenant_id=tenant_id,
                event_type="SMART_CACHE_MISS",
                reason_code="CACHE_MISS",
                cache_key_checksum=checksum,
                decision=CacheDecision.MISS.value,
            )
            return CacheLookupResultV2(
                decision=CacheDecision.MISS,
                reason_code="CACHE_MISS",
                cache_key_checksum=checksum,
                lookup_latency_ms=latency,
            )

        if entry_model.expires_at <= datetime.now(timezone.utc):
            await self.repository.mark_entry(
                tenant_id, entry_model.id, status="EXPIRED", freshness="STALE_HARD"
            )
            return CacheLookupResultV2(
                decision=CacheDecision.EXPIRED,
                reason_code="CACHE_ENTRY_EXPIRED",
                cache_key_checksum=checksum,
                freshness=FreshnessStatus.STALE_HARD,
                lookup_latency_ms=latency,
            )

        if entry_model.freshness != FreshnessStatus.FRESH.value:
            return CacheLookupResultV2(
                decision=CacheDecision.STALE,
                reason_code="CACHE_ENTRY_STALE",
                cache_key_checksum=checksum,
                freshness=FreshnessStatus(entry_model.freshness),
                lookup_latency_ms=latency,
            )

        dependency_tags = await self.repository.get_dependency_tags(tenant_id, entry_model.id)

        # Build CacheEntryV2
        entry = CacheEntryV2(
            metadata=CacheEntryMetadataV2(
                entry_id=str(entry_model.id),
                tenant_id=str(entry_model.tenant_id),
                cache_type=request.cache_type,
                cache_key_checksum=entry_model.cache_key_checksum,
                scope_fingerprint=entry_model.scope_fingerprint,
                permission_fingerprint=entry_model.permission_fingerprint,
                query_fingerprint=entry_model.query_fingerprint,
                metric_fingerprints=request.metric_fingerprints,
                source_sync_version=entry_model.source_sync_version,
                source_watermark=entry_model.source_watermark,
                validation_policy_version=entry_model.validation_policy_version,
                compiler_version=entry_model.compiler_version,
                tool_registry_snapshot=entry_model.tool_registry_snapshot,
                certification_id=entry_model.certification_id,
                tenant_proof_id=entry_model.tenant_proof_id,
                created_at=entry_model.created_at.isoformat(),
                expires_at=entry_model.expires_at.isoformat(),
                generation=entry_model.generation,
                hit_count=entry_model.hit_count,
                payload_size_bytes=entry_model.payload_size_bytes,
                classification=entry_model.classification,
            ),
            payload_ref=CacheEntryPayloadReferenceV2(
                payload_id=str(entry_model.id),
                payload_checksum=entry_model.payload_checksum,
                payload_data=entry_model.payload_json,
            ),
            dependency_tags=dependency_tags,
            status=entry_model.status,
            freshness=FreshnessStatus(entry_model.freshness),
            entry_checksum=entry_model.entry_checksum,
        )

        # Verify Entry Checksum & Integrity
        if not entry.verify_checksum():
            await self.repository.mark_entry(
                tenant_id, entry_model.id, status="CORRUPTED", freshness="INVALIDATED"
            )
            await self.repository.log_event(
                tenant_id=tenant_id,
                event_type="SMART_CACHE_ENTRY_CORRUPTED",
                reason_code="CHECKSUM_MISMATCH",
                cache_key_checksum=checksum,
                decision=CacheDecision.CHECKSUM_MISMATCH.value,
            )
            return CacheLookupResultV2(
                decision=CacheDecision.CHECKSUM_MISMATCH,
                reason_code="CHECKSUM_MISMATCH",
                cache_key_checksum=checksum,
                lookup_latency_ms=latency,
            )

        # Increment hit count asynchronously
        await self.repository.increment_hit_count(tenant_id, entry_model.id)
        await self.repository.log_event(
            tenant_id=tenant_id,
            event_type="SMART_CACHE_HIT",
            reason_code="CACHE_HIT",
            cache_key_checksum=checksum,
            decision=CacheDecision.HIT.value,
        )

        return CacheLookupResultV2(
            decision=CacheDecision.HIT,
            reason_code="CACHE_HIT",
            cache_key_checksum=checksum,
            entry=entry,
            freshness=entry.freshness,
            lookup_latency_ms=latency,
        )
