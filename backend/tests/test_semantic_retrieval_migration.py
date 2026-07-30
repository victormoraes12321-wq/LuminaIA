from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "database" / "migration_v16_0.py"
_SPEC = importlib.util.spec_from_file_location("lumina_migration_v16_0", _MIGRATION_PATH)
assert _SPEC and _SPEC.loader
_MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATION)

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.security]


@pytest.mark.asyncio
async def test_migration_v16_up_idempotent_down_and_up_again() -> None:
    await _MIGRATION.run_down(confirm_test_only=True)
    first = await _MIGRATION.run_up()
    second = await _MIGRATION.run_up()
    assert first["tables"] == sorted(_MIGRATION.TABLES)
    assert second["tables"] == first["tables"]
    assert "fk_semantic_index_active_version" in first["constraints"]
    assert "idx_semantic_alias_lookup" in first["indexes"]
    assert "idx_semantic_document_label" in first["indexes"]
    await _MIGRATION.run_down(confirm_test_only=True)
    final = await _MIGRATION.run_up()
    assert final["tables"] == sorted(_MIGRATION.TABLES)
