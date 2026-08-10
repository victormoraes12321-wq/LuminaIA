"""Integration test for full migration chain up/down including v25."""
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
    spec = importlib.util.spec_from_file_location(f"chain_v25_test_v{version}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_migration_chain_v12_to_v25():
    await guard_engine_before_write(engine)

    v12 = _load(12)
    v24 = _load(24)
    v25 = _load(25)

    # Re-up v25
    await v25.run_up(engine)

    # Down v25 -> v24 -> v12
    await v25.run_down(engine)
    await v24.run_down(engine)

    # Re-up v24 -> v25
    await v24.run_up(engine)
    await v25.run_up(engine)

    async with engine.connect() as conn:
        res = await conn.execute(sqlalchemy.text("SELECT to_regclass('operational_metric_rollups_v2')"))
        assert res.scalar() is not None
