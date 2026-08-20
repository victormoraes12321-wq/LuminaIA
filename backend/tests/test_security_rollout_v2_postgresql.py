from __future__ import annotations

import pytest

from database import engine
from services.security_rollout_v2 import MigrationLockUnavailable, PostgresMigrationLockV2
from testing.database_guard import guard_engine_before_write


@pytest.mark.asyncio
async def test_real_postgresql_migration_lock_contention_and_release() -> None:
    await guard_engine_before_write(engine)
    async with engine.connect() as first, engine.connect() as second:
        async with PostgresMigrationLockV2.hold(first):
            with pytest.raises(MigrationLockUnavailable, match="MIGRATION_LOCK_CONTENDED"):
                async with PostgresMigrationLockV2.hold(second):
                    raise AssertionError("contended lock must never enter")
        async with PostgresMigrationLockV2.hold(second):
            pass
