"""Integration test for full migration chain up to v24 in disposable PostgreSQL database."""
from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import inspect
import pytest

from config import settings
from database import engine
from testing.database_guard import guard_engine_before_write

ROOT = Path(__file__).resolve().parents[1]


def _load(version: int):
    path = ROOT / "database" / f"migration_v{version}_0.py"
    spec = importlib.util.spec_from_file_location(f"chain_v24_test_v{version}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dsn() -> str:
    assert settings.TEST_DATABASE_URL
    return settings.TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _up(version: int, module) -> None:
    params = inspect.signature(module.run_up).parameters
    if "dsn" in params:
        await module.run_up(_dsn())
    else:
        await module.run_up()


async def _down(version: int, module) -> None:
    try:
        params = inspect.signature(module.run_down).parameters
        if "confirm_test_only" in params and "dsn" in params:
            await module.run_down(confirm_test_only=True, dsn=_dsn())
        elif "confirm_test_only" in params:
            await module.run_down(confirm_test_only=True)
        else:
            await module.run_down()
    except Exception as exc:
        if version == 12 and "lumina_schema_migrations" in str(exc):
            pass
        else:
            raise


@pytest.mark.asyncio
async def test_migration_chain_v12_to_v24():
    await guard_engine_before_write(engine)

    modules = {v: _load(v) for v in range(12, 25)}

    # Up chain v12..v24
    for v in range(12, 25):
        await _up(v, modules[v])

    # Re-run up24 idempotency check
    await _up(24, modules[24])

    # Down chain v24..v12
    for v in range(24, 11, -1):
        await _down(v, modules[v])

    # Restore baseline v12..v24
    for v in range(12, 25):
        await _up(v, modules[v])

    from testing.test_database import reset_and_seed_test_database
    await reset_and_seed_test_database(engine)
