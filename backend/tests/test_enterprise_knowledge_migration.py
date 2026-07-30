from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "database" / "migration_v13_0.py"
_SPEC = importlib.util.spec_from_file_location("lumina_migration_v13_0", _MIGRATION_PATH)
assert _SPEC and _SPEC.loader
_MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATION)
TABLES = _MIGRATION.TABLES
run_down = _MIGRATION.run_down
run_up = _MIGRATION.run_up

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.security]


@pytest.mark.asyncio
async def test_migration_v13_up_idempotent_down_and_up_again() -> None:
    await run_down(confirm_test_only=True)
    first = await run_up()
    second = await run_up()
    assert first["tables"] == sorted(TABLES)
    assert second["tables"] == first["tables"]
    assert "fk_knowledge_asset_published_version" in first["constraints"]
    assert "idx_knowledge_alias_lookup" in first["indexes"]
    await run_down(confirm_test_only=True)
    final = await run_up()
    assert final["tables"] == sorted(TABLES)
