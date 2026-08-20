from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import pytest

pytestmark = pytest.mark.no_database


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database" / "migration_v22_0.py"


def _module():
    spec = importlib.util.spec_from_file_location("migration_v22_0_static", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_is_import_safe_additive_and_explicit() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "create_all" not in source
    assert "oracle" not in source.lower()
    assert "blueprints.json" not in source
    assert "run_up" in {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "run_down" in {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def test_migration_declares_exact_expected_tables_and_compilable_ddl() -> None:
    module = _module()
    expected = {
        "dashboards_v2", "dashboard_revisions_v2", "dashboard_reviews_v2", "dashboard_approvals_v2",
        "dashboard_publications_v2", "dashboard_active_publications_v2", "dashboard_collaborators_v2",
        "dashboard_access_policies_v2", "dashboard_audit_events_v2", "dashboard_runtime_executions_v2",
        "dashboard_widget_executions_v2", "dashboard_evaluation_cases_v2", "dashboard_evaluation_results_v2",
    }
    assert set(module.TABLES) == expected
    assert {table.name for table in module.MODEL_TABLES} == expected
    for table in module.MODEL_TABLES:
        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert "CREATE TABLE" in ddl


def test_history_tables_receive_immutability_triggers() -> None:
    module = _module()
    statements = "\n".join(module.IMMUTABILITY_STATEMENTS)
    for table in module.IMMUTABLE_TABLES:
        assert f"trg_{table}_immutable" in statements
    assert "fk_dashboards_v2_head_revision" in statements
