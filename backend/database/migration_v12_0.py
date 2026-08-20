"""
Migration v12.0 - PostgreSQL conversation state.

This script is explicit and independent from SQLAlchemy create_all. Destructive
down migration is available only for the guarded disposable test database.
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


VERSION = "12.0"
CONTRACT_VERSION = "lumina.conversation-state/1.0"
TABLES = (
    "conversation_sessions",
    "conversation_nodes",
    "conversation_state_snapshots",
    "conversation_events",
    "conversation_legacy_imports",
)

UP_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS lumina_schema_migrations (
    version VARCHAR(32) PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_id_tenant'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT uq_users_id_tenant UNIQUE (id, tenant_id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_session_id VARCHAR(128) NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.conversation-state/1.0',
    context_epoch INTEGER NOT NULL DEFAULT 0,
    context_version BIGINT NOT NULL DEFAULT 0,
    lock_version BIGINT NOT NULL DEFAULT 0,
    next_sequence BIGINT NOT NULL DEFAULT 1,
    active_head_node_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    archived_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_conversation_session_public_owner
        UNIQUE (tenant_id, user_id, public_session_id),
    CONSTRAINT uq_conversation_session_public_global UNIQUE (public_session_id),
    CONSTRAINT uq_conversation_session_owner UNIQUE (id, tenant_id, user_id),
    CONSTRAINT fk_conversation_session_user_tenant
        FOREIGN KEY (user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT ck_conversation_session_status
        CHECK (status IN ('ACTIVE','ARCHIVED','EXPIRED','DELETED')),
    CONSTRAINT ck_conversation_session_epoch CHECK (context_epoch >= 0),
    CONSTRAINT ck_conversation_session_context_version CHECK (context_version >= 0),
    CONSTRAINT ck_conversation_session_lock_version CHECK (lock_version >= 0),
    CONSTRAINT ck_conversation_session_next_sequence CHECK (next_sequence >= 1),
    CONSTRAINT ck_conversation_session_expiry CHECK (expires_at >= created_at)
);

CREATE TABLE IF NOT EXISTS conversation_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    sequence_number BIGINT NOT NULL,
    parent_node_id UUID,
    role VARCHAR(16) NOT NULL,
    node_type VARCHAR(40) NOT NULL,
    status VARCHAR(20) NOT NULL,
    client_message_id UUID,
    idempotency_key_hash VARCHAR(64),
    content_ciphertext BYTEA,
    content_key_version VARCHAR(32),
    content_fingerprint VARCHAR(64),
    search_history_id UUID REFERENCES search_history(id) ON DELETE SET NULL,
    plan_fingerprint VARCHAR(128),
    response_fingerprint VARCHAR(128),
    base_context_version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    CONSTRAINT uq_conversation_node_session UNIQUE (id, session_id),
    CONSTRAINT uq_conversation_node_sequence UNIQUE (session_id, sequence_number),
    CONSTRAINT fk_conversation_node_session_owner
        FOREIGN KEY (session_id, tenant_id, user_id)
        REFERENCES conversation_sessions(id, tenant_id, user_id) ON DELETE CASCADE,
    CONSTRAINT fk_conversation_node_parent_session
        FOREIGN KEY (parent_node_id, session_id)
        REFERENCES conversation_nodes(id, session_id) ON DELETE RESTRICT,
    CONSTRAINT ck_conversation_node_sequence CHECK (sequence_number >= 1),
    CONSTRAINT ck_conversation_node_role CHECK (role IN ('user','assistant','system')),
    CONSTRAINT ck_conversation_node_type CHECK (
        node_type IN ('USER_QUERY','ASSISTANT_RESPONSE','CLARIFICATION_REQUEST',
        'CLARIFICATION_RESPONSE','ERROR','CANCELLED','RESET','SYSTEM_EVENT')
    ),
    CONSTRAINT ck_conversation_node_status CHECK (
        status IN ('IN_PROGRESS','COMPLETED','FAILED','CANCELLED','SUPERSEDED')
    ),
    CONSTRAINT ck_conversation_node_timestamps CHECK (
        (completed_at IS NULL OR completed_at >= created_at)
        AND (failed_at IS NULL OR failed_at >= created_at)
    )
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_conversation_session_head'
    ) THEN
        ALTER TABLE conversation_sessions
        ADD CONSTRAINT fk_conversation_session_head
        FOREIGN KEY (active_head_node_id, id)
        REFERENCES conversation_nodes(id, session_id) ON DELETE RESTRICT;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS conversation_state_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    context_epoch INTEGER NOT NULL,
    context_version BIGINT NOT NULL,
    head_node_id UUID,
    schema_version VARCHAR(64) NOT NULL,
    state_json JSONB NOT NULL,
    state_checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_conversation_snapshot_version
        UNIQUE (session_id, context_epoch, context_version),
    CONSTRAINT fk_conversation_snapshot_session_owner
        FOREIGN KEY (session_id, tenant_id, user_id)
        REFERENCES conversation_sessions(id, tenant_id, user_id) ON DELETE CASCADE,
    CONSTRAINT fk_conversation_snapshot_head_session
        FOREIGN KEY (head_node_id, session_id)
        REFERENCES conversation_nodes(id, session_id) ON DELETE RESTRICT,
    CONSTRAINT ck_conversation_snapshot_epoch CHECK (context_epoch >= 0),
    CONSTRAINT ck_conversation_snapshot_version CHECK (context_version >= 0),
    CONSTRAINT ck_conversation_snapshot_checksum
        CHECK (state_checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS conversation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    schema_version VARCHAR(64) NOT NULL,
    context_epoch INTEGER NOT NULL,
    context_version BIGINT NOT NULL,
    node_id UUID,
    fingerprint VARCHAR(128),
    event_metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_conversation_event_session_owner
        FOREIGN KEY (session_id, tenant_id, user_id)
        REFERENCES conversation_sessions(id, tenant_id, user_id) ON DELETE CASCADE,
    CONSTRAINT ck_conversation_event_epoch CHECK (context_epoch >= 0),
    CONSTRAINT ck_conversation_event_version CHECK (context_version >= 0)
);

CREATE TABLE IF NOT EXISTS conversation_legacy_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES conversation_sessions(id) ON DELETE SET NULL,
    source_checksum VARCHAR(64) NOT NULL,
    schema_version VARCHAR(64) NOT NULL,
    source_format VARCHAR(40) NOT NULL,
    imported_nodes INTEGER NOT NULL DEFAULT 0,
    warnings JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_conversation_legacy_import_checksum
        UNIQUE (tenant_id, user_id, source_checksum),
    CONSTRAINT ck_conversation_legacy_import_nodes CHECK (imported_nodes >= 0)
);

CREATE INDEX IF NOT EXISTS idx_conversation_sessions_owner_status_activity
    ON conversation_sessions (tenant_id, user_id, status, last_activity_at DESC, id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_expires_at
    ON conversation_sessions (expires_at);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_deleted_at
    ON conversation_sessions (deleted_at);
CREATE INDEX IF NOT EXISTS idx_conversation_nodes_session_sequence
    ON conversation_nodes (session_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_conversation_nodes_session_parent
    ON conversation_nodes (session_id, parent_node_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_conversation_nodes_client_message
    ON conversation_nodes (session_id, client_message_id)
    WHERE client_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conversation_snapshots_current
    ON conversation_state_snapshots (session_id, context_epoch, context_version DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_events_session_time
    ON conversation_events (session_id, created_at, id);
CREATE INDEX IF NOT EXISTS idx_conversation_legacy_import_owner
    ON conversation_legacy_imports (tenant_id, user_id, created_at);

INSERT INTO lumina_schema_migrations(version, description)
VALUES ('12.0', 'PostgreSQL conversation state lumina.conversation-state/1.0')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;
"""

DOWN_SQL = """
ALTER TABLE IF EXISTS conversation_sessions
    DROP CONSTRAINT IF EXISTS fk_conversation_session_head;
DROP TABLE IF EXISTS conversation_legacy_imports;
DROP TABLE IF EXISTS conversation_events;
DROP TABLE IF EXISTS conversation_state_snapshots;
DROP TABLE IF EXISTS conversation_nodes;
DROP TABLE IF EXISTS conversation_sessions;
ALTER TABLE IF EXISTS users DROP CONSTRAINT IF EXISTS uq_users_id_tenant;
DELETE FROM lumina_schema_migrations WHERE version = '12.0';
"""


def _dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


def _assert_disposable_test_target() -> None:
    if not settings.is_testing:
        raise RuntimeError("Migration v12 down is restricted to ENVIRONMENT=test.")
    if not settings.TEST_DATABASE_URL or settings.DATABASE_URL != settings.TEST_DATABASE_URL:
        raise RuntimeError("Migration v12 down requires the guarded TEST_DATABASE_URL.")


async def verify_schema(conn: asyncpg.Connection) -> dict[str, list[str]]:
    present = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename = ANY($1::text[])",
        list(TABLES),
    )
    found = {row["tablename"] for row in present}
    missing = sorted(set(TABLES) - found)
    if missing:
        raise RuntimeError(f"Migration v12 verification failed; missing tables: {missing}")
    indexes = await conn.fetch(
        "SELECT indexname FROM pg_indexes WHERE schemaname='public' "
        "AND tablename = ANY($1::text[]) ORDER BY indexname",
        list(TABLES),
    )
    return {"tables": sorted(found), "indexes": [row["indexname"] for row in indexes]}


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
