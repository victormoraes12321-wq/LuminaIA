from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from database import get_db_context


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _load(version: int):
    path = BACKEND_ROOT / "database" / f"migration_v{version}_0.py"
    spec = importlib.util.spec_from_file_location(f"prompt18_migration_v{version}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _down(module) -> None:
    parameters = inspect.signature(module.run_down).parameters
    if "confirm_test_only" in parameters:
        await module.run_down(confirm_test_only=True)
    else:
        await module.run_down()


@pytest.mark.asyncio
async def test_v21_up_idempotency_schema_constraints_indexes_and_down() -> None:
    migration = _load(21)
    first = await migration.run_up()
    second = await migration.run_up()
    assert first["status"] == second["status"] == "SUCCESS"

    async with get_db_context() as session:
        tables = set(
            (await session.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )).scalars()
        )
        assert set(migration.TABLES) <= tables
        assert "materialization_versions" not in tables

        constraints = (await session.execute(
            text(
                """
                SELECT conname, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid::regclass::text = ANY(:tables)
                """
            ),
            {"tables": migration.TABLES},
        )).all()
        definitions = "\n".join(str(item[1]) for item in constraints)
        assert "FOREIGN KEY (entry_id, tenant_id)" in definitions
        assert "FOREIGN KEY (tenant_id, definition_id, definition_version)" in definitions
        assert "expires_at > created_at" in definitions
        assert "expires_at > acquired_at" in definitions

        indexes = (await session.execute(
            text(
                "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename = ANY(:tables)"
            ),
            {"tables": migration.TABLES},
        )).scalars().all()
        assert len(indexes) >= 25
        assert "idx_smart_cache_entry_lookup" in indexes
        assert "idx_materialization_snapshot_state" in indexes

    await migration.run_down(confirm_test_only=True)
    async with get_db_context() as session:
        remaining = set(
            (await session.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            )).scalars()
        )
    assert not (set(migration.TABLES) & remaining)
    assert "result_certifications" in remaining
    await migration.run_up()


@pytest.mark.asyncio
async def test_v21_rejects_cross_tenant_dependency_fk() -> None:
    migration = _load(21)
    await migration.run_up()
    tenant_a = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    tenant_b = "b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"
    entry_id = "aaaaaaaa-0000-4000-8000-000000000001"
    async with get_db_context() as session:
        await session.execute(
            text(
                """
                INSERT INTO smart_cache_entries (
                    id, tenant_id, cache_type, cache_key_checksum, scope_fingerprint,
                    permission_fingerprint, query_fingerprint, analytical_catalog_version,
                    source_sync_version, source_watermark, validation_policy_version,
                    compiler_version, tool_registry_snapshot, certification_id,
                    tenant_proof_id, payload_json, payload_checksum, entry_checksum,
                    expires_at
                ) VALUES (
                    :id, :tenant, 'CERTIFIED_ANALYTICAL_RESULT', :hash, :hash,
                    :hash, :hash, 'catalog-v1', 'sync-v1', 'watermark-v1', 'policy-v1',
                    'compiler-v1', 'tools-v1', 'cert-1', 'proof-1', '{}'::jsonb,
                    :hash, :hash, NOW() + INTERVAL '5 minutes'
                )
                """
            ),
            {"id": entry_id, "tenant": tenant_a, "hash": "a" * 64},
        )
    with pytest.raises(DBAPIError):
        async with get_db_context() as session:
            await session.execute(
                text(
                    "INSERT INTO smart_cache_entry_dependencies (id, tenant_id, entry_id, tag) VALUES (gen_random_uuid(), :tenant, :entry, 'metric:sales')"
                ),
                {"tenant": tenant_b, "entry": entry_id},
            )
    await migration.run_down(confirm_test_only=True)
    await migration.run_up()


@pytest.mark.asyncio
async def test_v21_ddl_rolls_back_transactionally_on_synthetic_failure() -> None:
    migration = _load(21)
    await migration.run_down(confirm_test_only=True)
    with pytest.raises(DBAPIError):
        await migration.run_up(
            statements=[migration.UP_STATEMENTS[0], "SELECT 1 / 0;"]
        )
    async with get_db_context() as session:
        exists = await session.scalar(
            text("SELECT to_regclass('public.smart_cache_policies') IS NOT NULL")
        )
    assert exists is False
    await migration.run_up()


@pytest.mark.asyncio
async def test_complete_chain_v21_to_v12_and_v12_to_v21() -> None:
    modules = {version: _load(version) for version in range(13, 22)}
    for version in range(13, 22):
        await modules[version].run_up()
    for version in range(21, 12, -1):
        await _down(modules[version])
    for version in range(13, 22):
        await modules[version].run_up()

    async with get_db_context() as session:
        tables = set(
            (await session.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            )).scalars()
        )
    assert set(modules[21].TABLES) <= tables
    assert "validation_policies" in tables
    assert "ai_orchestration_policies" in tables
