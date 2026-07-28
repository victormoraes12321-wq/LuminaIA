from __future__ import annotations

import asyncpg
import importlib.util
from pathlib import Path
import pytest

from config import settings


_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "database" / "migration_v12_0.py"
_SPEC = importlib.util.spec_from_file_location("lumina_migration_v12_0", _MIGRATION_PATH)
assert _SPEC and _SPEC.loader
_MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATION)
TABLES = _MIGRATION.TABLES
run_down = _MIGRATION.run_down
run_up = _MIGRATION.run_up
verify_schema = _MIGRATION.verify_schema


pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.security]


def _dsn() -> str:
    assert settings.TEST_DATABASE_URL
    return settings.TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


@pytest.mark.asyncio
async def test_migration_up_idempotent_down_and_up_again() -> None:
    first = await run_up(_dsn())
    second = await run_up(_dsn())
    assert first["tables"] == sorted(TABLES)
    assert second["tables"] == sorted(TABLES)
    assert set(first["indexes"]) == set(second["indexes"])

    await run_down(confirm_test_only=True, dsn=_dsn())
    conn = await asyncpg.connect(_dsn())
    try:
        remaining = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_tables "
            "WHERE schemaname='public' AND tablename = ANY($1::text[])",
            list(TABLES),
        )
        assert remaining == 0
    finally:
        await conn.close()

    restored = await run_up(_dsn())
    assert restored["tables"] == sorted(TABLES)


@pytest.mark.asyncio
async def test_migration_schema_has_owner_and_graph_constraints() -> None:
    await run_up(_dsn())
    conn = await asyncpg.connect(_dsn())
    try:
        rows = await conn.fetch(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid IN (SELECT oid FROM pg_class WHERE relname = ANY($1::text[]))",
            list(TABLES),
        )
        constraints = {row["conname"] for row in rows}
        assert {
            "uq_conversation_session_public_global",
            "fk_conversation_node_session_owner",
            "fk_conversation_node_parent_session",
            "fk_conversation_session_head",
            "uq_conversation_snapshot_version",
            "fk_conversation_snapshot_head_session",
        }.issubset(constraints)
        await verify_schema(conn)
    finally:
        await conn.close()
