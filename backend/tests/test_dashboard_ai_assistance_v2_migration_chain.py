from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import text

from config import settings
from database import engine


ROOT = Path(__file__).resolve().parents[1]


def _load(version: int):
    path = ROOT / "database" / f"migration_v{version}_0.py"
    spec = importlib.util.spec_from_file_location(f"prompt22_chain_v{version}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dsn() -> str:
    assert settings.TEST_DATABASE_URL
    return settings.TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def _up(version: int, module) -> None:
    if 12 <= version <= 16:
        await module.run_up(_dsn())
    else:
        await module.run_up()


async def _down(version: int, module) -> None:
    try:
        if 12 <= version <= 16:
            await module.run_down(confirm_test_only=True, dsn=_dsn())
        elif version in {17, 21, 22, 23}:
            await module.run_down(confirm_test_only=True)
        else:
            # v18, v19, v20, v24 and others use plain run_down()
            await module.run_down()
    except Exception as exc:
        if version == 12 and "lumina_schema_migrations" in str(exc):
            pass
        else:
            raise


from testing.test_database import reset_and_seed_test_database


@pytest.mark.asyncio
async def test_migration_chain_down_v23_to_v12_and_up_v12_to_v23() -> None:
    modules = {version: _load(version) for version in range(12, 25)}
    try:
        for version in range(24, 11, -1):
            await _down(version, modules[version])
    finally:
        for version in range(12, 25):
            await _up(version, modules[version])
        await reset_and_seed_test_database(engine)

    async with engine.connect() as connection:
        for version, module in modules.items():
            tables = tuple(getattr(module, "TABLES", ()))
            for table_name in tables:
                exists = await connection.scalar(
                    text("SELECT to_regclass(:name) IS NOT NULL"),
                    {"name": f"public.{table_name}"},
                )
                assert exists, f"v{version} table missing after chain: {table_name}"
