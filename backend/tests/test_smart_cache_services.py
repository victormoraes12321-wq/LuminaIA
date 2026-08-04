from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from contracts.smart_cache_materialization_v2 import (
    CacheDecision,
    CacheEligibilityRequestV2,
    CacheInvalidationRequestV2,
    CacheLookupRequestV2,
    CacheScopeV2,
    CacheType,
    CacheWriteRequestV2,
    CertificationStatus,
    DataClassification,
    FreshnessStatus,
    InvalidationScope,
)
from services.smart_cache_materialization import (
    CacheSingleFlightService,
    SmartCacheInvalidationService,
    SmartCacheKeyBuilder,
    SmartCacheLookupService,
    SmartCachePolicyService,
    SmartCacheWriteService,
)


pytestmark = pytest.mark.no_database


def _scope(tenant: str, permission: str = "a" * 64) -> CacheScopeV2:
    return CacheScopeV2(tenant_id=tenant, permission_fingerprint=permission)


def _eligibility() -> CacheEligibilityRequestV2:
    return CacheEligibilityRequestV2(
        cache_type=CacheType.CERTIFIED_ANALYTICAL_RESULT,
        certification_status=CertificationStatus.VALID,
        tenant_proof_valid=True,
        query_fingerprint_valid=True,
        result_checksum_valid=True,
        metric_fingerprints_valid=True,
        source_freshness=FreshnessStatus.FRESH,
        is_complete=True,
        data_classification=DataClassification.INTERNAL,
    )


def _key(scope: CacheScopeV2):
    return SmartCacheKeyBuilder.build_key(
        cache_type=CacheType.CERTIFIED_ANALYTICAL_RESULT,
        scope=scope,
        canonical_query_fingerprint="q" * 64,
        analytical_catalog_version="catalog-v1",
        metric_fingerprints=["m" * 64],
        filter_structure_fingerprint="f" * 64,
        canonical_period_fingerprint="p" * 64,
        source_sync_version="sync-v1",
        source_watermark="watermark-v1",
        validation_policy_version="v1.0",
        compiler_version="compiler-v1",
        tool_registry_snapshot="tools-v1",
        generation_counters={"catalog": 1},
    )


def _lookup(scope: CacheScopeV2) -> CacheLookupRequestV2:
    return CacheLookupRequestV2(
        scope=scope,
        cache_type=CacheType.CERTIFIED_ANALYTICAL_RESULT,
        canonical_query_fingerprint="q" * 64,
        analytical_catalog_version="catalog-v1",
        metric_fingerprints=["m" * 64],
        filter_structure_fingerprint="f" * 64,
        canonical_period_fingerprint="p" * 64,
        source_sync_version="sync-v1",
        source_watermark="watermark-v1",
        validation_policy_version="v1.0",
        compiler_version="compiler-v1",
        tool_registry_snapshot="tools-v1",
        generation_counters={"catalog": 1},
    )


class MemoryCacheRepository:
    def __init__(self):
        self.entries = {}
        self.dependencies = {}
        self.events = []
        self.generations = {}

    async def get_entry_by_key_checksum(self, tenant_id, checksum):
        return self.entries.get((tenant_id, checksum))

    async def save_entry(self, **values):
        entry = SimpleNamespace(
            id=values["entry_id"],
            tenant_id=values["tenant_id"],
            created_at=datetime.now(timezone.utc),
            status="ACTIVE",
            freshness="FRESH",
            hit_count=0,
            invalidated_at=None,
            expires_at=values["expires_at"],
            **{k: v for k, v in values.items() if k not in {"entry_id", "tenant_id", "expires_at", "dependency_tags"}},
        )
        self.entries[(values["tenant_id"], values["cache_key_checksum"])] = entry
        self.dependencies[(values["tenant_id"], entry.id)] = list(values["dependency_tags"])
        return entry

    async def get_dependency_tags(self, tenant_id, entry_id):
        return self.dependencies.get((tenant_id, entry_id), [])

    async def increment_hit_count(self, tenant_id, entry_id):
        for (owner, _), entry in self.entries.items():
            if owner == tenant_id and entry.id == entry_id:
                entry.hit_count += 1

    async def mark_entry(self, tenant_id, entry_id, *, status, freshness):
        for (owner, _), entry in self.entries.items():
            if owner == tenant_id and entry.id == entry_id:
                entry.status = status
                entry.freshness = freshness

    async def log_event(self, **event):
        self.events.append(event)

    async def invalidate_entries_by_tag(self, tenant_id, tag):
        count = 0
        for (owner, entry_id), tags in self.dependencies.items():
            if owner == tenant_id and tag in tags:
                for (entry_owner, _), entry in self.entries.items():
                    if entry_owner == tenant_id and entry.id == entry_id:
                        entry.status = "INVALIDATED"
                        count += 1
        return count

    async def increment_generation(self, tenant_id, target, reason):
        key = (tenant_id, target)
        self.generations[key] = self.generations.get(key, 0) + 1
        return self.generations[key]


@pytest.mark.asyncio
async def test_miss_write_hit_alias_tenant_permission_stale_and_corruption() -> None:
    repository = MemoryCacheRepository()
    policies = SmartCachePolicyService()
    writer = SmartCacheWriteService(repository, policies)
    lookup = SmartCacheLookupService(repository, policies)
    scope = _scope("tenant-a")

    miss = await lookup.lookup(_lookup(scope))
    assert miss.decision is CacheDecision.MISS

    write = await writer.write(
        CacheWriteRequestV2(
            scope=scope,
            cache_key=_key(scope),
            payload={"rows": [], "complete": True},
            certification_id="cert-1",
            tenant_proof_id="proof-1",
            eligibility=_eligibility(),
            dependency_tags=["metric:sales"],
        )
    )
    assert write.success
    hit = await lookup.lookup(_lookup(scope))
    assert hit.decision is CacheDecision.HIT
    assert hit.entry is not None and hit.entry.payload_ref.payload_data["rows"] == []

    assert (await lookup.lookup(_lookup(_scope("tenant-b")))).decision is CacheDecision.MISS
    assert (await lookup.lookup(_lookup(_scope("tenant-a", "b" * 64)))).decision is CacheDecision.MISS

    entry = repository.entries[("tenant-a", write.cache_key_checksum)]
    entry.freshness = "STALE_HARD"
    assert (await lookup.lookup(_lookup(scope))).decision is CacheDecision.STALE
    entry.freshness = "FRESH"
    entry.payload_json = {"rows": ["corrupt"]}
    assert (await lookup.lookup(_lookup(scope))).decision is CacheDecision.CHECKSUM_MISMATCH
    assert entry.status == "CORRUPTED"


@pytest.mark.asyncio
async def test_invalidation_uses_trusted_tenant_and_never_crosses_tenants() -> None:
    repository = MemoryCacheRepository()
    service = SmartCacheInvalidationService(repository)
    result = await service.invalidate(
        "tenant-a",
        CacheInvalidationRequestV2(
            invalidation_scope=InvalidationScope.PERMISSION,
            target_identifier="permissions",
            reason="permission changed",
        ),
    )
    assert result.tenant_id == "tenant-a"
    assert repository.generations == {("tenant-a", "permissions"): 1}
    assert "tenant_id" not in CacheInvalidationRequestV2.model_fields


class LeaseRepository:
    def __init__(self):
        self.held = set()
        self.releases = 0

    async def acquire_lease(self, tenant, key, owner, ttl):
        identity = (tenant, key)
        if identity in self.held:
            return False
        self.held.add(identity)
        return True

    async def release_lease(self, tenant, key, owner):
        self.held.discard((tenant, key))
        self.releases += 1
        return True


@pytest.mark.asyncio
@pytest.mark.parametrize("request_count", [2, 10, 100])
async def test_single_flight_prevents_stampede(request_count: int) -> None:
    repository = LeaseRepository()
    service = CacheSingleFlightService(repository)
    executions = 0

    async def expensive():
        nonlocal executions
        executions += 1
        await asyncio.sleep(0.01)
        return 42

    results = await asyncio.gather(
        *(service.execute_single_flight("tenant-a", "k" * 64, expensive) for _ in range(request_count))
    )
    assert executions == 1
    assert sum(1 for owner, _ in results if owner) == 1
    assert {value for _, value in results} == {42}
    assert repository.releases == 1


@pytest.mark.asyncio
async def test_single_flight_separates_keys_tenants_and_recovers_after_failure() -> None:
    repository = LeaseRepository()
    service = CacheSingleFlightService(repository)
    calls = 0

    async def value():
        nonlocal calls
        calls += 1
        return calls

    await asyncio.gather(
        service.execute_single_flight("tenant-a", "a" * 64, value),
        service.execute_single_flight("tenant-a", "b" * 64, value),
        service.execute_single_flight("tenant-b", "a" * 64, value),
    )
    assert calls == 3

    async def fail():
        raise RuntimeError("synthetic executor failure")

    with pytest.raises(RuntimeError, match="synthetic"):
        await service.execute_single_flight("tenant-a", "f" * 64, fail)
    assert ("tenant-a", "f" * 64) not in repository.held
    assert (await service.execute_single_flight("tenant-a", "f" * 64, value))[1] == 4
