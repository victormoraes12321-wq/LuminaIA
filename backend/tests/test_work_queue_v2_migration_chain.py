"""Integration test for full migration chain up/down including v26."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest
import sqlalchemy
from database import engine
from testing.database_guard import guard_engine_before_write

ROOT = Path(__file__).resolve().parents[1]


def _load(version: int):
    path = ROOT / "database" / f"migration_v{version}_0.py"
    spec = importlib.util.spec_from_file_location(f"chain_v26_test_v{version}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_migration_chain_v12_to_v26():
    await guard_engine_before_write(engine)

    v12 = _load(12)
    v25 = _load(25)
    v26 = _load(26)

    # Re-up v26
    await v26.run_up(engine)

    # Down v26 -> v25
    await v26.run_down(engine)
    await v25.run_down(engine)

    # Re-up v25 -> v26
    await v25.run_up(engine)
    await v26.run_up(engine)

    async with engine.connect() as conn:
        res = await conn.execute(sqlalchemy.text("SELECT to_regclass('governed_work_queue_jobs_v2')"))
        assert res.scalar() is not None
        res_perf = await conn.execute(sqlalchemy.text("SELECT to_regclass('performance_baselines_v2')"))
        assert res_perf.scalar() is not None
