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

_KNOWLEDGE_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "database" / "migration_v13_0.py"
)
_KNOWLEDGE_SPEC = importlib.util.spec_from_file_location(
    "lumina_migration_v13_0_for_v12_compat",
    _KNOWLEDGE_MIGRATION_PATH,
)
assert _KNOWLEDGE_SPEC and _KNOWLEDGE_SPEC.loader
_KNOWLEDGE_MIGRATION = importlib.util.module_from_spec(_KNOWLEDGE_SPEC)
_KNOWLEDGE_SPEC.loader.exec_module(_KNOWLEDGE_MIGRATION)

_PROFILE_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "database" / "migration_v14_0.py"
)
_PROFILE_SPEC = importlib.util.spec_from_file_location(
    "lumina_migration_v14_0_for_v12_compat",
    _PROFILE_MIGRATION_PATH,
)
assert _PROFILE_SPEC and _PROFILE_SPEC.loader
_PROFILE_MIGRATION = importlib.util.module_from_spec(_PROFILE_SPEC)
_PROFILE_SPEC.loader.exec_module(_PROFILE_MIGRATION)

_FEEDBACK_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "database" / "migration_v15_0.py"
)
_FEEDBACK_SPEC = importlib.util.spec_from_file_location(
    "lumina_migration_v15_0_for_v12_compat",
    _FEEDBACK_MIGRATION_PATH,
)
assert _FEEDBACK_SPEC and _FEEDBACK_SPEC.loader
_FEEDBACK_MIGRATION = importlib.util.module_from_spec(_FEEDBACK_SPEC)
_FEEDBACK_SPEC.loader.exec_module(_FEEDBACK_MIGRATION)

_SEMANTIC_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "database" / "migration_v16_0.py"
)
_SEMANTIC_SPEC = importlib.util.spec_from_file_location(
    "lumina_migration_v16_0_for_v12_compat",
    _SEMANTIC_MIGRATION_PATH,
)
assert _SEMANTIC_SPEC and _SEMANTIC_SPEC.loader
_SEMANTIC_MIGRATION = importlib.util.module_from_spec(_SEMANTIC_SPEC)
_SEMANTIC_SPEC.loader.exec_module(_SEMANTIC_MIGRATION)


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

    # Downstream migrations must be removed before the migration they depend on.
    await _SEMANTIC_MIGRATION.run_down(confirm_test_only=True, dsn=_dsn())
    await _FEEDBACK_MIGRATION.run_down(confirm_test_only=True, dsn=_dsn())
    await _PROFILE_MIGRATION.run_down(confirm_test_only=True, dsn=_dsn())
    await _KNOWLEDGE_MIGRATION.run_down(confirm_test_only=True, dsn=_dsn())
    try:
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
        restored_knowledge = await _KNOWLEDGE_MIGRATION.run_up(_dsn())
        assert restored_knowledge["tables"] == sorted(_KNOWLEDGE_MIGRATION.TABLES)
        restored_profile = await _PROFILE_MIGRATION.run_up(_dsn())
        assert restored_profile["tables"] == sorted(_PROFILE_MIGRATION.TABLES)
        restored_feedback = await _FEEDBACK_MIGRATION.run_up(_dsn())
        assert restored_feedback["tables"] == sorted(_FEEDBACK_MIGRATION.TABLES)
        restored_semantic = await _SEMANTIC_MIGRATION.run_up(_dsn())
        assert restored_semantic["tables"] == sorted(_SEMANTIC_MIGRATION.TABLES)
    finally:
        await run_up(_dsn())
        await _KNOWLEDGE_MIGRATION.run_up(_dsn())
        await _PROFILE_MIGRATION.run_up(_dsn())
        await _FEEDBACK_MIGRATION.run_up(_dsn())
        await _SEMANTIC_MIGRATION.run_up(_dsn())


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
