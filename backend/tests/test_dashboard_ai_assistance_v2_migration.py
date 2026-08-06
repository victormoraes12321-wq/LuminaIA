from __future__ import annotations

import ast
from pathlib import Path

import pytest


@pytest.mark.no_database
def test_v23_is_explicit_additive_and_guarded() -> None:
    root = Path(__file__).resolve().parents[1]
    migration = root / "database" / "migration_v23_0.py"
    tree = ast.parse(migration.read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"run_up", "run_down"} for node in tree.body)
    text = migration.read_text(encoding="utf-8")
    assert "guard_engine_before_write" in text
    assert "confirm_test_only" in text
    assert "dashboard_ai_v2_reject_mutation" in text
    assert "DROP TABLE" not in text.upper()
    for version in range(12, 23):
        assert (root / "database" / f"migration_v{version}_0.py").exists()


@pytest.mark.no_database
def test_v23_tables_are_excluded_from_create_all() -> None:
    root = Path(__file__).resolve().parents[1]
    names = {
        "dashboard_ai_proposals_v2", "dashboard_ai_proposal_versions_v2", "dashboard_ai_clarifications_v2",
        "dashboard_ai_evidence_v2", "dashboard_ai_decisions_v2", "dashboard_ai_runs_v2",
        "dashboard_ai_audit_events_v2", "dashboard_ai_evaluation_cases_v2", "dashboard_ai_evaluation_results_v2",
    }
    for path in (root / "main.py", root / "testing" / "test_database.py"):
        text = path.read_text(encoding="utf-8")
        assert all(name in text for name in names)

