"""Migration v14.0 - governed user analytical profile.

The migration is additive, independent from create_all and reversible only in
the guarded disposable PostgreSQL test environment.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Sequence

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

from config import settings


VERSION = "14.0"
CONTRACT_VERSION = "lumina.user-analytical-profile/1.0"
TABLES = (
    "user_analytical_profiles",
    "user_preference_items",
    "user_preference_consents",
    "user_profile_events",
    "user_profile_exports",
    "user_profile_deletion_requests",
)

UP_SQL = """
CREATE TABLE IF NOT EXISTS lumina_schema_migrations (
    version VARCHAR(32) PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_id_tenant') THEN
        ALTER TABLE users ADD CONSTRAINT uq_users_id_tenant UNIQUE (id, tenant_id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS user_analytical_profiles (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE',
    profile_version INTEGER NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    checksum VARCHAR(64) NOT NULL,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.user-analytical-profile/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    disabled_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_user_profile_identity UNIQUE (id, tenant_id, user_id),
    CONSTRAINT uq_user_profile_owner UNIQUE (tenant_id, user_id),
    CONSTRAINT fk_user_profile_owner_tenant
        FOREIGN KEY (user_id, tenant_id) REFERENCES users(id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT ck_user_profile_status
        CHECK (status IN ('ACTIVE','DISABLED','DELETION_PENDING','DELETED')),
    CONSTRAINT ck_user_profile_version CHECK (profile_version >= 1),
    CONSTRAINT ck_user_profile_lock CHECK (lock_version >= 0),
    CONSTRAINT ck_user_profile_checksum CHECK (checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_user_profile_disabled CHECK (
        (status = 'DISABLED' AND disabled_at IS NOT NULL) OR status <> 'DISABLED'
    ),
    CONSTRAINT ck_user_profile_deleted CHECK (
        (status = 'DELETED' AND deleted_at IS NOT NULL)
        OR (status <> 'DELETED' AND deleted_at IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS user_preference_items (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    profile_id UUID NOT NULL,
    preference_type VARCHAR(40) NOT NULL,
    preference_key VARCHAR(128) NOT NULL,
    content JSONB NOT NULL,
    risk VARCHAR(40) NOT NULL,
    origin VARCHAR(40) NOT NULL,
    origin_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE',
    created_by_user_id UUID NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    lock_version BIGINT NOT NULL DEFAULT 0,
    checksum VARCHAR(64) NOT NULL,
    effective_from TIMESTAMPTZ,
    effective_to TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.user-analytical-profile/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_user_preference_identity UNIQUE (id, profile_id, tenant_id, user_id),
    CONSTRAINT uq_user_preference_key UNIQUE (profile_id, preference_type, preference_key),
    CONSTRAINT fk_user_preference_profile_owner
        FOREIGN KEY (profile_id, tenant_id, user_id)
        REFERENCES user_analytical_profiles(id, tenant_id, user_id) ON DELETE CASCADE,
    CONSTRAINT fk_user_preference_creator_tenant
        FOREIGN KEY (created_by_user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_user_preference_type CHECK (preference_type IN (
        'PRESENTATION','LOCALE','ACCESSIBILITY','ANALYTICAL_DEFAULT',
        'FAVORITE_METRIC','FAVORITE_DIMENSION','FAVORITE_ENTITY',
        'SAVED_FILTER_REFERENCE','SAVED_QUERY_REFERENCE','SAVED_DASHBOARD_REFERENCE',
        'INTERACTION','PRIVACY','RETENTION'
    )),
    CONSTRAINT ck_user_preference_status CHECK (status IN (
        'ACTIVE','DISABLED','EXPIRED','REVOKED','DELETED','PENDING_CONFIRMATION'
    )),
    CONSTRAINT ck_user_preference_risk CHECK (risk IN (
        'SAFE_PRESENTATION','VISIBLE_ANALYTICAL_DEFAULT','REFERENCE_ONLY',
        'RESTRICTED','FORBIDDEN'
    )),
    CONSTRAINT ck_user_preference_origin CHECK (origin IN (
        'USER_EXPLICIT','SYSTEM_DEFAULT','ADMIN_POLICY','LEGACY_IMPORT','MIGRATED',
        'FEEDBACK_CANDIDATE','INFERRED_UNCONFIRMED'
    )),
    CONSTRAINT ck_user_preference_version CHECK (version >= 1),
    CONSTRAINT ck_user_preference_lock CHECK (lock_version >= 0),
    CONSTRAINT ck_user_preference_checksum CHECK (checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_user_preference_content CHECK (jsonb_typeof(content) = 'object'),
    CONSTRAINT ck_user_preference_effective_period CHECK (
        effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from
    ),
    CONSTRAINT ck_user_preference_expiration CHECK (
        expires_at IS NULL OR effective_from IS NULL OR expires_at > effective_from
    ),
    CONSTRAINT ck_user_preference_deleted CHECK (
        (status = 'DELETED' AND deleted_at IS NOT NULL)
        OR (status <> 'DELETED' AND deleted_at IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS user_preference_consents (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    profile_id UUID NOT NULL,
    preference_id UUID NOT NULL,
    purpose VARCHAR(256) NOT NULL,
    scope VARCHAR(128) NOT NULL,
    status VARCHAR(16) NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    source VARCHAR(40) NOT NULL,
    granted_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    lock_version BIGINT NOT NULL DEFAULT 0,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_preference_consent_identity
        UNIQUE (id, preference_id, profile_id, tenant_id, user_id),
    CONSTRAINT fk_user_preference_consent_item
        FOREIGN KEY (preference_id, profile_id, tenant_id, user_id)
        REFERENCES user_preference_items(id, profile_id, tenant_id, user_id) ON DELETE CASCADE,
    CONSTRAINT ck_user_preference_consent_status CHECK (status IN ('GRANTED','REVOKED')),
    CONSTRAINT ck_user_preference_consent_lock CHECK (lock_version >= 0),
    CONSTRAINT ck_user_preference_consent_checksum CHECK (checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_user_preference_consent_timestamps CHECK (
        (status = 'GRANTED' AND granted_at IS NOT NULL)
        OR (status = 'REVOKED' AND revoked_at IS NOT NULL)
    ),
    CONSTRAINT ck_user_preference_consent_order CHECK (
        revoked_at IS NULL OR granted_at IS NULL OR revoked_at >= granted_at
    )
);

CREATE TABLE IF NOT EXISTS user_profile_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    profile_id UUID NOT NULL,
    preference_id UUID,
    actor_user_id UUID NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    reason_code VARCHAR(128) NOT NULL,
    request_id VARCHAR(128),
    event_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.user-analytical-profile/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_user_profile_event_profile
        FOREIGN KEY (profile_id, tenant_id, user_id)
        REFERENCES user_analytical_profiles(id, tenant_id, user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_user_profile_event_actor
        FOREIGN KEY (actor_user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_user_profile_event_metadata CHECK (jsonb_typeof(event_metadata) = 'object')
);

CREATE TABLE IF NOT EXISTS user_profile_exports (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    profile_id UUID NOT NULL,
    format VARCHAR(16) NOT NULL DEFAULT 'JSON',
    checksum VARCHAR(64) NOT NULL,
    payload_size INTEGER NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'COMPLETED',
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.user-analytical-profile/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    CONSTRAINT fk_user_profile_export_profile
        FOREIGN KEY (profile_id, tenant_id, user_id)
        REFERENCES user_analytical_profiles(id, tenant_id, user_id) ON DELETE CASCADE,
    CONSTRAINT ck_user_profile_export_checksum CHECK (checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_user_profile_export_size CHECK (payload_size >= 0)
);

CREATE TABLE IF NOT EXISTS user_profile_deletion_requests (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    profile_id UUID NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    reason TEXT,
    idempotency_key_hash VARCHAR(64) NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.user-analytical-profile/1.0',
    CONSTRAINT uq_user_profile_deletion_idempotency
        UNIQUE (tenant_id, user_id, idempotency_key_hash),
    CONSTRAINT fk_user_profile_deletion_profile
        FOREIGN KEY (profile_id, tenant_id, user_id)
        REFERENCES user_analytical_profiles(id, tenant_id, user_id) ON DELETE RESTRICT,
    CONSTRAINT ck_user_profile_deletion_status
        CHECK (status IN ('PENDING','COMPLETED','REJECTED')),
    CONSTRAINT ck_user_profile_deletion_idempotency
        CHECK (idempotency_key_hash ~ '^[a-f0-9]{64}$')
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant_user
    ON user_analytical_profiles (tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_status
    ON user_analytical_profiles (tenant_id, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_user_preferences_tenant_user_type
    ON user_preference_items (tenant_id, user_id, preference_type, id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_tenant_user_key
    ON user_preference_items (tenant_id, user_id, preference_key, id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_active
    ON user_preference_items (tenant_id, user_id, status, updated_at)
    WHERE status = 'ACTIVE';
CREATE INDEX IF NOT EXISTS idx_user_preferences_expiration
    ON user_preference_items (tenant_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_user_preferences_saved_reference
    ON user_preference_items (tenant_id, user_id, preference_type, preference_key)
    WHERE preference_type IN (
        'SAVED_FILTER_REFERENCE','SAVED_QUERY_REFERENCE','SAVED_DASHBOARD_REFERENCE'
    );
CREATE INDEX IF NOT EXISTS idx_user_preference_consents_owner
    ON user_preference_consents (tenant_id, user_id, status, preference_id);
CREATE INDEX IF NOT EXISTS idx_user_profile_events_owner_time
    ON user_profile_events (tenant_id, user_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_user_profile_exports_owner_time
    ON user_profile_exports (tenant_id, user_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_user_profile_deletions_owner_status
    ON user_profile_deletion_requests (tenant_id, user_id, status, requested_at, id);

INSERT INTO lumina_schema_migrations(version, description)
VALUES ('14.0', 'Governed user analytical profile lumina.user-analytical-profile/1.0')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;
"""

DOWN_SQL = """
DROP TABLE IF EXISTS user_profile_deletion_requests;
DROP TABLE IF EXISTS user_profile_exports;
DROP TABLE IF EXISTS user_profile_events;
DROP TABLE IF EXISTS user_preference_consents;
DROP TABLE IF EXISTS user_preference_items;
DROP TABLE IF EXISTS user_analytical_profiles;
DO $$
BEGIN
    IF to_regclass('public.lumina_schema_migrations') IS NOT NULL THEN
        DELETE FROM lumina_schema_migrations WHERE version = '14.0';
    END IF;
END $$;
"""


def _dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


def _assert_disposable_test_target() -> None:
    if not settings.is_testing:
        raise RuntimeError("Migration v14 down is restricted to ENVIRONMENT=test.")
    if not settings.TEST_DATABASE_URL or settings.DATABASE_URL != settings.TEST_DATABASE_URL:
        raise RuntimeError("Migration v14 down requires the guarded TEST_DATABASE_URL.")


async def verify_schema(conn: asyncpg.Connection) -> dict[str, list[str]]:
    present = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "AND tablename = ANY($1::text[])",
        list(TABLES),
    )
    found = {row["tablename"] for row in present}
    missing = sorted(set(TABLES) - found)
    if missing:
        raise RuntimeError(f"Migration v14 verification failed; missing tables: {missing}")
    indexes = await conn.fetch(
        "SELECT indexname FROM pg_indexes WHERE schemaname='public' "
        "AND tablename = ANY($1::text[]) ORDER BY indexname",
        list(TABLES),
    )
    constraints = await conn.fetch(
        "SELECT conname FROM pg_constraint WHERE conrelid = ANY("
        "SELECT oid FROM pg_class WHERE relname = ANY($1::text[])) ORDER BY conname",
        list(TABLES),
    )
    return {
        "tables": sorted(found),
        "indexes": [row["indexname"] for row in indexes],
        "constraints": [row["conname"] for row in constraints],
    }


async def run_up(dsn: str | None = None) -> dict[str, list[str]]:
    conn = await asyncpg.connect(dsn or _dsn())
    try:
        async with conn.transaction():
            await conn.execute(UP_SQL)
            result = await verify_schema(conn)
        return result
    finally:
        await conn.close()


async def run_down(*, confirm_test_only: bool, dsn: str | None = None) -> None:
    if not confirm_test_only:
        raise RuntimeError("Down migration requires --confirm-test-only.")
    _assert_disposable_test_target()
    conn = await asyncpg.connect(dsn or _dsn())
    try:
        async with conn.transaction():
            await conn.execute(DOWN_SQL)
    finally:
        await conn.close()


async def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("direction", choices=("up", "verify", "down"), default="up", nargs="?")
    parser.add_argument("--confirm-test-only", action="store_true")
    args = parser.parse_args(argv)
    if args.direction == "up":
        print(await run_up())
    elif args.direction == "verify":
        conn = await asyncpg.connect(_dsn())
        try:
            print(await verify_schema(conn))
        finally:
            await conn.close()
    else:
        await run_down(confirm_test_only=args.confirm_test_only)


if __name__ == "__main__":
    asyncio.run(main())
