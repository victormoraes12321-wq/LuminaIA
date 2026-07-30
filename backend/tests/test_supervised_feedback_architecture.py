from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "migration_v15_0",
    ROOT / "database" / "migration_v15_0.py",
)
assert _SPEC and _SPEC.loader
_MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATION)
DOWN_SQL = _MIGRATION.DOWN_SQL
TABLES = _MIGRATION.TABLES
UP_SQL = _MIGRATION.UP_SQL

pytestmark = pytest.mark.unit


def test_authority_does_not_import_openai_or_oracle() -> None:
    service_root = ROOT / "services" / "supervised_feedback"
    for path in service_root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert all("openai" not in name.lower() for name in imports), path
        assert all("oracle" not in name.lower() for name in imports), path


def test_migration_v15_is_additive_explicit_and_reversible() -> None:
    assert "CREATE TABLE IF NOT EXISTS" in UP_SQL
    assert "Base.metadata.create_all" not in UP_SQL
    assert "alembic" not in UP_SQL.lower()
    for table in TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in UP_SQL
        assert f"DROP TABLE IF EXISTS {table}" in DOWN_SQL


def test_migration_contains_tenant_cas_and_immutability_primitives() -> None:
    assert "tenant_id UUID NOT NULL" in UP_SQL
    assert "lock_version BIGINT NOT NULL" in UP_SQL
    assert "uq_feedback_idempotency" in UP_SQL
    assert "fk_feedback_response_owner" in UP_SQL
    assert "ck_feedback_no_self_review" in UP_SQL
    assert "ck_dataset_published_at" in UP_SQL


def test_router_derives_identity_from_authenticated_user() -> None:
    source = (ROOT / "routers" / "supervised_feedback.py").read_text(encoding="utf-8")
    assert "Depends(enforce_password_change)" in source
    assert "payload.tenant_id" not in source
    tree = ast.parse(source)
    request_models = {
        "ExplanationUpdate",
        "LockAction",
        "ReviewerAssignment",
        "ReviewAction",
        "DeletionAction",
        "CandidateApproval",
        "DatasetCreate",
        "DatasetTransition",
        "DatasetExportAction",
    }
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in request_models:
            fields = {
                child.target.id
                for child in node.body
                if isinstance(child, ast.AnnAssign)
                and isinstance(child.target, ast.Name)
            }
            assert fields.isdisjoint({"tenant_id", "user_id", "reviewer_role"})


def test_production_defaults_are_fail_closed() -> None:
    source = (ROOT / "config.py").read_text(encoding="utf-8")
    assert 'SUPERVISED_FEEDBACK_MODE: str = Field(default="LEGACY_ONLY")' in source
    for flag in (
        "SUPERVISED_FEEDBACK_FRONTEND_ENABLED",
        "SUPERVISED_FEEDBACK_ADMIN_ENABLED",
        "SUPERVISED_FEEDBACK_DATASET_ENABLED",
        "SUPERVISED_FEEDBACK_EXPORT_ENABLED",
        "SUPERVISED_FEEDBACK_SHADOW_ENABLED",
    ):
        assert f"{flag}: bool = Field(default=False)" in source
