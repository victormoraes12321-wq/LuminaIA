from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import text

from contracts.safe_analytical_postgresql_v2 import (
    AnalyticalExecutionResultV2,
    AnalyticalQuerySpecV2,
    AnalyticalResultStatisticsV2,
    AnalyticalResultValidationV2,
)
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
from contracts.validation_provenance_v2 import ValidationStatus
from database import AsyncSessionLocal, get_db_context
from services.smart_cache_materialization import (
    GovernedMaterializationBuildService,
    MaterializationPublicationService,
    MaterializationRefreshService,
    MaterializationRepository,
    MaterializationRollbackService,
    SmartCacheGarbageCollectionService,
    SmartCacheInvalidationService,
    SmartCacheKeyBuilder,
    SmartCacheLookupService,
    SmartCachePolicyService,
    SmartCacheRepository,
    SmartCacheWriteService,
)
from testing.test_database import ADMIN_A, TENANT_A, TENANT_B


def _load_v21():
    path = Path(__file__).resolve().parents[1] / "database" / "migration_v21_0.py"
    spec = importlib.util.spec_from_file_location("prompt18_repository_v21", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest_asyncio.fixture
async def v21_schema(isolated_test_database):
    migration = _load_v21()
    await migration.run_down(confirm_test_only=True)
    await migration.run_up()
    yield migration


def _scope(tenant=TENANT_A, permission="a" * 64):
    return CacheScopeV2(
        tenant_id=str(tenant),
        permission_fingerprint=permission,
    )


def _key(scope):
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
        compiler_version="compiler-v1",
        tool_registry_snapshot="tools-v1",
        generation_counters={"catalog": 1, "permission": 1},
    )


def _eligibility():
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


def _lookup(scope):
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
        compiler_version="compiler-v1",
        tool_registry_snapshot="tools-v1",
        generation_counters={"catalog": 1, "permission": 1},
    )


@pytest.mark.asyncio
async def test_repository_miss_write_hit_and_cross_tenant_scope(v21_schema) -> None:
    async with AsyncSessionLocal() as session:
        repository = SmartCacheRepository(session)
        policies = SmartCachePolicyService()
        lookup = SmartCacheLookupService(repository, policies)
        write = SmartCacheWriteService(repository, policies)
        scope = _scope()
        assert (await lookup.lookup(_lookup(scope))).decision is CacheDecision.MISS
        result = await write.write(
            CacheWriteRequestV2(
                scope=scope,
                cache_key=_key(scope),
                payload={"rows": [], "complete": True},
                certification_id="cert-valid",
                tenant_proof_id="proof-valid",
                eligibility=_eligibility(),
                dependency_tags=["metric:sales", "catalog:v1"],
            )
        )
        assert result.success
        assert (await lookup.lookup(_lookup(scope))).decision is CacheDecision.HIT
        assert (await lookup.lookup(_lookup(_scope(TENANT_B)))).decision is CacheDecision.MISS
        assert (
            await lookup.lookup(_lookup(_scope(TENANT_A, permission="b" * 64)))
        ).decision is CacheDecision.MISS


@pytest.mark.asyncio
async def test_repository_invalidation_generation_gc_and_tenant_boundaries(v21_schema) -> None:
    async with AsyncSessionLocal() as session:
        repository = SmartCacheRepository(session)
        service = SmartCacheInvalidationService(repository)
        result = await service.invalidate(
            str(TENANT_A),
            CacheInvalidationRequestV2(
                invalidation_scope=InvalidationScope.PERMISSION,
                target_identifier="permission",
                reason="permission changed",
            ),
        )
        assert result.invalidated_count == 1
        assert await repository.get_generation(str(TENANT_A), "permission") == 1
        assert await repository.get_generation(str(TENANT_B), "permission") == 1

        gc = SmartCacheGarbageCollectionService(repository)
        dry = await gc.execute_gc(str(TENANT_A), dry_run=True, limit=10)
        assert dry.dry_run and dry.evicted_count == 0


@pytest.mark.asyncio
async def test_database_leases_coordinate_two_replicas(v21_schema) -> None:
    first_session = AsyncSessionLocal()
    second_session = AsyncSessionLocal()
    try:
        first = SmartCacheRepository(first_session)
        second = SmartCacheRepository(second_session)
        acquired_first = await first.acquire_lease(str(TENANT_A), "k" * 64, "owner-token-first-123", 30)
        acquired_second = await second.acquire_lease(str(TENANT_A), "k" * 64, "owner-token-second-123", 30)
        assert acquired_first is True
        assert acquired_second is False
        assert await second.release_lease(str(TENANT_A), "k" * 64, "owner-token-second-123") is False
        assert await first.release_lease(str(TENANT_A), "k" * 64, "owner-token-first-123") is True
        assert await second.acquire_lease(str(TENANT_A), "k" * 64, "owner-token-second-123", 30) is True
    finally:
        await first_session.close()
        await second_session.close()


class FakeAnalyticalExecutor:
    def __init__(self):
        self.calls = []

    async def execute_query(self, spec, tenant_id, user_id="system"):
        self.calls.append((spec, tenant_id, user_id))
        return AnalyticalExecutionResultV2(
            result_id="result-1",
            compiled_query_id="compiled-1",
            columns=[],
            rows=[],
            statistics=AnalyticalResultStatisticsV2(
                row_count=0,
                column_count=0,
                cell_count=0,
                execution_time_ms=1.0,
                bytes_serialized=2,
                truncated=False,
            ),
            validation=AnalyticalResultValidationV2(tenant_isolation_verified=True),
        )


class FakeValidationExecutor:
    def __init__(self, status=ValidationStatus.VALID):
        self.status = status
        self.calls = []

    async def execute(self, request):
        self.calls.append(request)
        return SimpleNamespace(
            overall_status=self.status,
            certification_id=uuid.uuid4(),
            result_certification=SimpleNamespace(tenant_proof_checksum="t" * 64),
            facts=[],
        )


async def _approved_definition(repository: MaterializationRepository):
    query_spec = AnalyticalQuerySpecV2(
        spec_id="monthly-sales",
        dataset_id="sales",
        expected_shape="SCALAR",
    )
    definition = await repository.save_definition(
        tenant_id=str(TENANT_A),
        definition_id="monthly-sales",
        canonical_name="Monthly sales",
        materialization_type="SCALAR_AGGREGATE",
        classification="INTERNAL",
        query_json=query_spec.model_dump(mode="json"),
        source_json={
            "dataset": "sales",
            "source_sync_version": "sync-v1",
            "watermark": "verified-watermark-1",
            "tenant_strategy": "ISOLATED_ANALYTICAL_CLONE",
        },
        query_fingerprint="q" * 64,
        checksum="d" * 64,
    )
    review = await repository.transition_definition(
        str(TENANT_A), "monthly-sales", 1,
        expected_lock_version=definition.lock_version,
        expected_lifecycle="DRAFT", new_lifecycle="IN_REVIEW",
    )
    return await repository.transition_definition(
        str(TENANT_A), "monthly-sales", 1,
        expected_lock_version=review.lock_version,
        expected_lifecycle="IN_REVIEW", new_lifecycle="APPROVED",
    )


@pytest.mark.asyncio
async def test_governed_build_publication_refresh_and_rollback(v21_schema) -> None:
    async with AsyncSessionLocal() as session:
        repository = MaterializationRepository(session)
        approved = await _approved_definition(repository)
        analytical = FakeAnalyticalExecutor()
        validation = FakeValidationExecutor()
        build_service = GovernedMaterializationBuildService(repository, analytical, validation)
        build, first_snapshot = await build_service.build_snapshot(
            tenant_id=str(TENANT_A), user_id=str(ADMIN_A), definition_id="monthly-sales",
            expected_lock_version=approved.lock_version,
            permissions=["materialization:build"], request_id="request-1",
        )
        assert build.status.value == "READY"
        assert await repository.get_published_snapshot(str(TENANT_A), "monthly-sales") is None
        assert isinstance(analytical.calls[0][0], AnalyticalQuerySpecV2)
        assert analytical.calls[0][1] == str(TENANT_A)
        assert validation.calls[0].context.tenant_id == TENANT_A

        publisher = MaterializationPublicationService(repository)
        first_publication = await publisher.publish(
            str(TENANT_A), "monthly-sales", first_snapshot.snapshot_id, str(ADMIN_A),
            expected_lock_version=0, permissions=["materialization:publish"],
        )
        assert first_publication.previous_snapshot_id is None
        active = await repository.get_published_snapshot(str(TENANT_A), "monthly-sales")
        assert active and active.snapshot_id == first_snapshot.snapshot_id

        definition = await repository.get_definition(str(TENANT_A), "monthly-sales")
        refresh = MaterializationRefreshService(build_service)
        refresh_result = await refresh.trigger_refresh(
            tenant_id=str(TENANT_A), user_id=str(ADMIN_A), definition_id="monthly-sales",
            expected_lock_version=definition.lock_version,
            permissions=["materialization:refresh"], request_id="request-2",
            trigger="MANUAL",
        )
        still_active = await repository.get_published_snapshot(str(TENANT_A), "monthly-sales")
        assert still_active and still_active.snapshot_id == first_snapshot.snapshot_id
        assert refresh_result.new_snapshot_id != first_snapshot.snapshot_id

        second_publication = await publisher.publish(
            str(TENANT_A), "monthly-sales", refresh_result.new_snapshot_id, str(ADMIN_A),
            expected_lock_version=1, permissions=["materialization:publish"],
        )
        assert second_publication.previous_snapshot_id == first_snapshot.snapshot_id
        rollback = MaterializationRollbackService(repository)
        rolled = await rollback.rollback(
            str(TENANT_A), "monthly-sales", first_snapshot.snapshot_id, str(ADMIN_A),
            expected_lock_version=2, permissions=["materialization:rollback"],
        )
        assert rolled.from_snapshot_id == refresh_result.new_snapshot_id
        assert (await repository.get_published_snapshot(str(TENANT_A), "monthly-sales")).snapshot_id == first_snapshot.snapshot_id
        assert await repository.get_snapshot_by_id(str(TENANT_B), first_snapshot.snapshot_id) is None

        unused = await repository.save_snapshot(
            tenant_id=str(TENANT_A), snapshot_id="unused-expired", definition_id="monthly-sales",
            definition_version=1, row_count=0, fact_count=0, payload_size_bytes=17,
            certification_id="cert-valid", certification_status="VALID",
            tenant_proof_id="proof-valid", watermark="verified-watermark-1",
            source_sync_version="sync-v1", payload_json={"rows": []},
            payload_checksum="e" * 64, checksum="f" * 64,
        )
        failed_build = await repository.save_build(
            tenant_id=str(TENANT_A), build_id="failed-old", definition_id="monthly-sales",
            definition_version=1, status="FAILED", error_code="SYNTHETIC",
        )
        old = datetime.now(timezone.utc) - timedelta(days=60)
        built = old - timedelta(days=1)
        await session.execute(
            text(
                "UPDATE materialization_snapshots SET built_at=:built, expires_at=:old "
                "WHERE tenant_id=:tenant AND snapshot_id IN (:active, :previous, :unused)"
            ),
            {
                "old": old,
                "built": built,
                "tenant": TENANT_A,
                "active": first_snapshot.snapshot_id,
                "previous": refresh_result.new_snapshot_id,
                "unused": unused.snapshot_id,
            },
        )
        await session.execute(
            text("UPDATE materialization_builds SET completed_at=:old WHERE id=:id"),
            {"old": old, "id": failed_build.id},
        )
        await session.commit()
        assert await repository.garbage_collect_retained_artifacts(
            str(TENANT_A), dry_run=True, limit=10
        ) == (2, 17)
        assert await repository.garbage_collect_retained_artifacts(
            str(TENANT_A), dry_run=False, limit=10
        ) == (2, 17)
        assert await repository.get_snapshot_by_id(str(TENANT_A), "unused-expired") is None
        assert (await repository.get_published_snapshot(str(TENANT_A), "monthly-sales")).snapshot_id == first_snapshot.snapshot_id


@pytest.mark.asyncio
async def test_validation_failure_and_untrusted_incremental_watermark_fail_closed(v21_schema) -> None:
    async with AsyncSessionLocal() as session:
        repository = MaterializationRepository(session)
        approved = await _approved_definition(repository)
        failing = GovernedMaterializationBuildService(
            repository, FakeAnalyticalExecutor(), FakeValidationExecutor(ValidationStatus.INVALID)
        )
        with pytest.raises(RuntimeError, match="did not certify"):
            await failing.build_snapshot(
                tenant_id=str(TENANT_A), user_id=str(ADMIN_A), definition_id="monthly-sales",
                expected_lock_version=approved.lock_version,
                permissions=["materialization:build"], request_id="request-fail",
            )
        definition = await repository.get_definition(str(TENANT_A), "monthly-sales")
        assert definition.lifecycle == "FAILED"

        await session.execute(
            text("UPDATE materialization_definitions SET lifecycle='APPROVED', lock_version=lock_version+1, source_json=jsonb_set(source_json, '{watermark}', '\"unverified\"') WHERE tenant_id=:tenant"),
            {"tenant": TENANT_A},
        )
        await session.commit()
        session.expire_all()
        definition = await repository.get_definition(str(TENANT_A), "monthly-sales")
        with pytest.raises(ValueError, match="verified watermark"):
            await failing.build_snapshot(
                tenant_id=str(TENANT_A), user_id=str(ADMIN_A), definition_id="monthly-sales",
                expected_lock_version=definition.lock_version,
                permissions=["materialization:build"], request_id="request-incremental",
                incremental=True,
            )
