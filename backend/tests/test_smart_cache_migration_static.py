from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path

import pytest


pytestmark = pytest.mark.no_database
BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = BACKEND_ROOT / "database" / "migration_v21_0.py"

HISTORICAL_MIGRATION_HASHES = {
    12: "cc4c96e1e8937f3d6d2cc8b8565fd4e85975a2eec2fcff9fa8cab20e059e2d19",
    13: "ca45680282b5f8ca4e1ca3349e14f711c8f731e45f231553eea752e5eae4e931",
    14: "74617d6aeb49cc8721dea2ee461677de549a6628bb45e9fa4e3a3d7b1fb7c13a",
    15: "d7bb65038a8fac318aee04aec5f5fa69a620cb266d2e5eeb63eeca25a1cfbb05",
    16: "4019b70dea67b0614d84d02270a4acdad554458dcb9f7b7cfe50a2136232ca31",
    17: "934f7e339031c44272366a29025a740e96174e4d9cec3e910aa1841fd68eea1c",
    18: "5ba33ce11617524638c2df244be6dcbc7a4705c0335f4c74e5fe8e0b8a45cc78",
    19: "0690fa64b4f9d3f9e743f9e4d3d3d8d0bdd87837c0642e464a78f7c30c73d998",
    20: "e3ea2b7fd73b0f5bb6c8bd4322f7bdb70ac528f3b515a7bbb597d561caac4b61",
}


def _load_migration():
    spec = importlib.util.spec_from_file_location("lumina_test_migration_v21", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_import_is_safe_and_declares_governed_entrypoints() -> None:
    module = _load_migration()
    assert callable(module.run_up)
    assert callable(module.run_down)
    assert len(module.TABLES) == len(set(module.TABLES)) == 14
    assert "materialization_versions" not in module.TABLES


def test_migration_source_has_no_forbidden_side_effects_or_imports() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lowered = source.lower()
    assert "create_all" not in lowered
    assert "oracle" not in lowered
    assert "database.connection" not in source
    assert "database.database_guard" not in source
    assert "5432" not in source
    assert "guard_engine_before_write" in source
    assert not any(isinstance(node, (ast.Call, ast.Await)) for node in tree.body)


def test_migration_declares_expected_tables_constraints_and_indexes() -> None:
    module = _load_migration()
    ddl = "\n".join(module.UP_STATEMENTS).lower()
    for table in module.TABLES:
        assert f"create table if not exists {table}" in ddl
    for marker in (
        "foreign key (entry_id, tenant_id)",
        "foreign key (tenant_id, definition_id, definition_version)",
        "expires_at > created_at",
        "expires_at > acquired_at",
        "query_fingerprint",
        "permission_fingerprint",
        "certification_id",
        "lock_version",
        "generation >= 0",
        "row_level_detail",
        "create index if not exists idx_smart_cache_entry_lookup",
        "create index if not exists idx_materialization_snapshot_state",
    ):
        assert marker in ddl


def test_historical_migrations_v12_to_v20_are_byte_identical() -> None:
    for version, expected in HISTORICAL_MIGRATION_HASHES.items():
        path = BACKEND_ROOT / "database" / f"migration_v{version}_0.py"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
