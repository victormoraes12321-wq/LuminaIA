"""Static AST and structure tests for migration_v24_0.py.

These tests do not require a live database connection — they only validate
the static structure of the migration file.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_v24():
    path = ROOT / "database" / "migration_v24_0.py"
    spec = importlib.util.spec_from_file_location("mig_v24_static", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.no_database
def test_migration_v24_0_ast_and_tables():
    mig_path = ROOT / "database" / "migration_v24_0.py"
    assert mig_path.exists()

    tree = ast.parse(mig_path.read_text(encoding="utf-8"))
    assert tree is not None

    mig = _load_v24()
    assert len(mig.TABLES) == 11
    assert len(mig.MODEL_TABLES) == 11
    assert len(mig.IMMUTABLE_TABLES) == 4


@pytest.mark.no_database
def test_migration_v24_immutable_tables():
    mig = _load_v24()
    expected_immutable = {
        "post_sync_insights_v2",
        "post_sync_insight_evidence_v2",
        "post_sync_insight_audit_events_v2",
        "post_sync_insight_evaluation_results_v2",
    }
    assert set(mig.IMMUTABLE_TABLES) == expected_immutable


@pytest.mark.no_database
def test_migration_v24_has_run_up_and_down():
    mig = _load_v24()
    assert callable(mig.run_up)
    assert callable(mig.run_down)


@pytest.mark.no_database
def test_migration_v24_all_table_names():
    mig = _load_v24()
    expected_tables = {
        "post_sync_insight_policies_v2",
        "post_sync_insight_outbox_v2",
        "post_sync_insight_runs_v2",
        "post_sync_insight_detector_executions_v2",
        "post_sync_insight_candidates_v2",
        "post_sync_insights_v2",
        "post_sync_insight_evidence_v2",
        "post_sync_insight_user_states_v2",
        "post_sync_insight_audit_events_v2",
        "post_sync_insight_evaluation_cases_v2",
        "post_sync_insight_evaluation_results_v2",
    }
    assert set(mig.TABLES) == expected_tables
