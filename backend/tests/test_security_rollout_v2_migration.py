from __future__ import annotations

import pytest

from contracts.security_rollout_v2 import GovernedFeatureV2, SchemaCompatibilityStateV2, SchemaManifestV2
from services.security_rollout_v2 import MigrationCompatibilityServiceV2, MigrationLockUnavailable, PostgresMigrationLockV2

pytestmark = pytest.mark.no_database


def test_schema_compatibility_window_and_future_schema_fail_closed() -> None:
    assert MigrationCompatibilityServiceV2.evaluate(current_schema_version=26).state is SchemaCompatibilityStateV2.COMPATIBLE
    assert MigrationCompatibilityServiceV2.evaluate(current_schema_version=25).state is SchemaCompatibilityStateV2.UPGRADE_REQUIRED
    assert MigrationCompatibilityServiceV2.evaluate(current_schema_version=27).state is SchemaCompatibilityStateV2.DATABASE_TOO_NEW
    assert MigrationCompatibilityServiceV2.evaluate(current_schema_version=0).state is SchemaCompatibilityStateV2.UNKNOWN


def test_feature_specific_previous_schema_is_compatible() -> None:
    result = MigrationCompatibilityServiceV2.evaluate_feature(GovernedFeatureV2.OBSERVABILITY_V2, 25)
    assert result.state is SchemaCompatibilityStateV2.COMPATIBLE


def test_missing_critical_object_is_schema_drift() -> None:
    manifest = SchemaManifestV2(schema_version=26, tables=())
    result = MigrationCompatibilityServiceV2.evaluate(current_schema_version=26, manifest=manifest)
    assert result.state is SchemaCompatibilityStateV2.BLOCKED
    assert "governed_work_queue_jobs_v2" in result.missing_objects


class _Result:
    def __init__(self, value: bool) -> None:
        self.value = value

    def scalar(self) -> bool:
        return self.value


class _Target:
    def __init__(self, acquire: bool) -> None:
        self.acquire = acquire
        self.statements: list[str] = []

    async def execute(self, statement: object, parameters: dict[str, int] | None = None) -> _Result:
        rendered = str(statement)
        self.statements.append(rendered)
        return _Result(self.acquire if "try_advisory" in rendered else True)


@pytest.mark.asyncio
async def test_migration_lock_acquires_and_releases() -> None:
    target = _Target(True)
    async with PostgresMigrationLockV2.hold(target):
        assert len(target.statements) == 1
    assert "pg_advisory_unlock" in target.statements[-1]


@pytest.mark.asyncio
async def test_migration_lock_contention_blocks() -> None:
    with pytest.raises(MigrationLockUnavailable, match="MIGRATION_LOCK_CONTENDED"):
        async with PostgresMigrationLockV2.hold(_Target(False)):
            raise AssertionError("unreachable")
