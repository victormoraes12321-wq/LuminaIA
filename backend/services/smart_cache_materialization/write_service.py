"""
LuminaAI — Smart Cache Write Service
lumina.smart-cache-materialization/1.0
"""
import uuid
import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from contracts.smart_cache_materialization_v2 import (
    CacheWriteRequestV2,
    CacheWriteResultV2,
    CacheDecision,
)
from .repository import SmartCacheRepository
from .policy_service import SmartCachePolicyService
from .eligibility_engine import SmartCacheEligibilityEngine

logger = logging.getLogger(__name__)


class SmartCacheWriteService:
    def __init__(self, repository: SmartCacheRepository, policy_service: SmartCachePolicyService):
        self.repository = repository
        self.policy_service = policy_service
        self.eligibility_engine = SmartCacheEligibilityEngine()

    async def write(self, request: CacheWriteRequestV2) -> CacheWriteResultV2:
        tenant_id = request.scope.tenant_id
        policy = self.policy_service.get_cache_policy(tenant_id)
        checksum = request.cache_key.compute_key_checksum()

        if str(request.scope.tenant_id) != str(request.cache_key.tenant_id):
            raise ValueError("cache key tenant must match the trusted scope")
        scope_fingerprint = request.scope.compute_scope_fingerprint()
        if request.cache_key.scope_fingerprint != scope_fingerprint:
            raise ValueError("cache key scope fingerprint is not authoritative")

        payload_serialized = json.dumps(
            request.payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        payload_bytes = len(payload_serialized.encode("utf-8"))

        eligibility = self.eligibility_engine.evaluate(
            request.eligibility.model_copy(
                update={
                    "cache_type": request.cache_key.cache_type,
                    "payload_size_bytes": payload_bytes,
                }
            ),
            policy,
        )

        if not eligibility.eligible:
            await self.repository.log_event(
                tenant_id=tenant_id,
                event_type="SMART_CACHE_ENTRY_BLOCKED",
                reason_code=eligibility.reason_code,
                cache_key_checksum=checksum,
                decision=eligibility.decision.value,
            )
            return CacheWriteResultV2(
                success=False,
                cache_key_checksum=checksum,
                reason_code=eligibility.reason_code,
                payload_size_bytes=payload_bytes,
            )

        ttl_sec = policy.default_ttl_seconds.get(request.cache_key.cache_type.value)
        if ttl_sec is None:
            raise ValueError("cache type has no governed TTL")
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_sec)

        # Compute entry checksum
        existing = await self.repository.get_entry_by_key_checksum(tenant_id, checksum)
        entry_uuid = existing.id if existing is not None else uuid.uuid4()
        entry_id = str(entry_uuid)
        payload_checksum = hashlib.sha256(payload_serialized.encode("utf-8")).hexdigest()
        data_to_hash = {
            "contract_version": request.cache_key.contract_version,
            "entry_id": entry_id,
            "tenant_id": str(tenant_id),
            "cache_key_checksum": checksum,
            "payload_checksum": payload_checksum,
            "generation": request.cache_key.generation_counter,
        }
        entry_checksum = hashlib.sha256(json.dumps(data_to_hash, sort_keys=True).encode("utf-8")).hexdigest()

        entry_model = await self.repository.save_entry(
            entry_id=entry_uuid,
            tenant_id=tenant_id,
            cache_type=request.cache_key.cache_type.value,
            cache_key_checksum=checksum,
            scope_fingerprint=scope_fingerprint,
            permission_fingerprint=request.scope.permission_fingerprint,
            query_fingerprint=request.cache_key.canonical_query_fingerprint,
            analytical_catalog_version=request.cache_key.analytical_catalog_version,
            source_sync_version=request.cache_key.source_sync_version,
            source_watermark=request.cache_key.source_watermark,
            validation_policy_version=request.cache_key.validation_policy_version,
            compiler_version=request.cache_key.compiler_version,
            tool_registry_snapshot=request.cache_key.tool_registry_snapshot,
            certification_id=request.certification_id,
            tenant_proof_id=request.tenant_proof_id,
            generation=request.cache_key.generation_counter,
            payload_size_bytes=payload_bytes,
            classification=request.eligibility.data_classification.value,
            payload_json=request.payload,
            payload_checksum=payload_checksum,
            dependency_tags=request.dependency_tags,
            entry_checksum=entry_checksum,
            expires_at=expires_at,
        )

        await self.repository.log_event(
            tenant_id=tenant_id,
            event_type="SMART_CACHE_ENTRY_WRITTEN",
            reason_code="ENTRY_SAVED",
            cache_key_checksum=checksum,
            decision="WRITTEN",
        )

        return CacheWriteResultV2(
            success=True,
            entry_id=str(entry_model.id),
            cache_key_checksum=checksum,
            reason_code="ENTRY_SAVED",
            payload_size_bytes=payload_bytes,
        )
