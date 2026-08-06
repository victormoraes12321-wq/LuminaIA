from __future__ import annotations

import importlib.util
from pathlib import Path

import asyncpg
import pytest

from config import settings


ROOT = Path(__file__).resolve().parents[1]


def load(version: int):
    path = ROOT / "database" / f"migration_v{version}_0.py"
    spec = importlib.util.spec_from_file_location(f"lumina_migration_v{version}_for_v15", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V12 = load(12)
V13 = load(13)
V14 = load(14)
V15 = load(15)

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.security]


def dsn() -> str:
    assert settings.TEST_DATABASE_URL
    return settings.TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


@pytest.mark.asyncio
async def test_migration_v15_idempotent_down_and_chain_compatibility() -> None:
    try:
        await V15.run_down(confirm_test_only=True, dsn=dsn())
    finally:
        await V12.run_up(dsn())
        await V13.run_up(dsn=dsn())
        await V14.run_up(dsn=dsn())

    first = await V15.run_up(dsn=dsn())
    second = await V15.run_up(dsn=dsn())
    assert first["tables"] == sorted(V15.TABLES)
    assert first["tables"] == second["tables"]
    assert "fk_feedback_response_owner" in first["constraints"]
    assert "idx_feedback_duplicate" in first["indexes"]

    conn = await asyncpg.connect(dsn())
    try:
        versions = await conn.fetch(
            "SELECT version FROM lumina_schema_migrations "
            "WHERE version = ANY($1::text[])",
            ["12.0", "13.0", "14.0", "15.0"],
        )
        assert {row["version"] for row in versions} == {"12.0", "13.0", "14.0", "15.0"}
    finally:
        await conn.close()

    try:
        await V15.run_down(confirm_test_only=True, dsn=dsn())
        conn = await asyncpg.connect(dsn())
        try:
            for table in V15.TABLES:
                assert await conn.fetchval("SELECT to_regclass($1)", f"public.{table}") is None
            assert await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM lumina_schema_migrations WHERE version='14.0')"
            )
        finally:
            await conn.close()
    finally:
        await V15.run_up(dsn=dsn())


@pytest.mark.asyncio
async def test_migration_v15_has_required_constraints_and_indexes() -> None:
    result = await V15.run_up(dsn=dsn())
    required_constraints = {
        "uq_feedback_idempotency",
        "fk_feedback_response_owner",
        "ck_feedback_no_self_review",
        "fk_training_candidate_feedback",
        "fk_training_example_candidate",
        "uq_dataset_version",
        "fk_dataset_member_snapshot",
        "fk_dataset_member_example",
        "uq_feedback_deletion_idempotency",
    }
    required_indexes = {
        "idx_feedback_owner_created",
        "idx_feedback_lifecycle",
        "idx_feedback_duplicate",
        "idx_feedback_review_queue",
        "idx_training_candidates_status",
        "idx_dataset_versions",
        "idx_dataset_members_snapshot",
    }
    assert required_constraints.issubset(set(result["constraints"]))
    assert required_indexes.issubset(set(result["indexes"]))
