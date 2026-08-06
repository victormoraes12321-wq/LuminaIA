from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

import asyncpg
import pytest

from config import settings


_PATH = Path(__file__).resolve().parents[1] / "database" / "migration_v14_0.py"
_SPEC = importlib.util.spec_from_file_location("lumina_migration_v14_0", _PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
_V13_PATH = Path(__file__).resolve().parents[1] / "database" / "migration_v13_0.py"
_V13_SPEC = importlib.util.spec_from_file_location("lumina_migration_v13_for_v14", _V13_PATH)
assert _V13_SPEC and _V13_SPEC.loader
_V13 = importlib.util.module_from_spec(_V13_SPEC)
_V13_SPEC.loader.exec_module(_V13)


def _dsn() -> str:
    return settings.TEST_DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )


@pytest.mark.asyncio
async def test_migration_v14_up_idempotent_down_and_v13_compatibility() -> None:
    try:
        await _MODULE.run_down(confirm_test_only=True, dsn=_dsn())
    finally:
        await _V13.run_up(dsn=_dsn())
        first = await _MODULE.run_up(dsn=_dsn())
    second = await _MODULE.run_up(dsn=_dsn())
    assert first["tables"] == sorted(_MODULE.TABLES)
    assert second["tables"] == first["tables"]
    assert "idx_user_preferences_active" in first["indexes"]
    assert "fk_user_preference_consent_item" in first["constraints"]

    conn = await asyncpg.connect(_dsn())
    try:
        assert await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM lumina_schema_migrations WHERE version='13.0')"
        )
        assert await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM lumina_schema_migrations WHERE version='14.0')"
        )
    finally:
        await conn.close()

    try:
        await _MODULE.run_down(confirm_test_only=True, dsn=_dsn())
        conn = await asyncpg.connect(_dsn())
        try:
            for table in _MODULE.TABLES:
                assert await conn.fetchval("SELECT to_regclass($1)", f"public.{table}") is None
            assert await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM lumina_schema_migrations WHERE version='13.0')"
            )
        finally:
            await conn.close()
    finally:
        await _MODULE.run_up(dsn=_dsn())


@pytest.mark.asyncio
async def test_migration_v14_constraints_reject_cross_user_consent() -> None:
    await _MODULE.run_up(dsn=_dsn())
    conn = await asyncpg.connect(_dsn())
    try:
        tenant = await conn.fetchval(
            "SELECT tenant_id FROM users WHERE email='consulta.a@lumina.internal'"
        )
        user_a = await conn.fetchval(
            "SELECT id FROM users WHERE email='consulta.a@lumina.internal'"
        )
        user_b = await conn.fetchval(
            "SELECT id FROM users WHERE email='gestor.a@lumina.internal'"
        )
        profile_id = uuid.UUID("51000000-0000-0000-0000-000000000001")
        preference_id = uuid.UUID("61000000-0000-0000-0000-000000000001")
        await conn.execute(
            """
            INSERT INTO user_analytical_profiles
                (id, tenant_id, user_id, checksum)
            VALUES ($1, $2, $3, $4)
            """,
            profile_id, tenant, user_a, "a" * 64,
        )
        await conn.execute(
            """
            INSERT INTO user_preference_items
                (id, tenant_id, user_id, profile_id, preference_type,
                 preference_key, content, risk, origin, created_by_user_id, checksum)
            VALUES ($1, $2, $3, $4, 'LOCALE', 'locale',
                    '{"kind":"LOCALE","locale":"pt-BR","timezone":"UTC",
                      "currency_display":"BRL","date_format":"DD/MM/YYYY",
                      "number_format":"pt-BR"}'::jsonb,
                    'SAFE_PRESENTATION', 'USER_EXPLICIT', $3, $5)
            """,
            preference_id, tenant, user_a, profile_id, "b" * 64,
        )
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            await conn.execute(
                """
                INSERT INTO user_preference_consents
                    (id, tenant_id, user_id, profile_id, preference_id,
                     purpose, scope, status, policy_version, source,
                     granted_at, checksum)
                VALUES ($1, $2, $3, $4, $5, 'forged', 'filters', 'GRANTED',
                        'v1', 'USER_ACTION', NOW(), $6)
                """,
                uuid.UUID("71000000-0000-0000-0000-000000000001"),
                tenant, user_b, profile_id, preference_id, "c" * 64,
            )
    finally:
        await conn.close()
