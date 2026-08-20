"""Migration v13.0 - governed enterprise knowledge.

The migration is additive and independent from SQLAlchemy create_all. Its down
path is restricted to the guarded disposable PostgreSQL test database.
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


VERSION = "13.0"
CONTRACT_VERSION = "lumina.enterprise-knowledge/1.0"
TABLES = (
    "enterprise_knowledge_assets",
    "enterprise_knowledge_versions",
    "enterprise_knowledge_approvals",
    "enterprise_knowledge_publications",
    "enterprise_knowledge_aliases",
    "enterprise_knowledge_relations",
    "enterprise_knowledge_events",
    "enterprise_knowledge_imports",
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

CREATE TABLE IF NOT EXISTS enterprise_knowledge_assets (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    canonical_key VARCHAR(128) NOT NULL,
    asset_type VARCHAR(40) NOT NULL,
    domain VARCHAR(128) NOT NULL,
    owner_user_id UUID NOT NULL,
    steward_label VARCHAR(256) NOT NULL,
    accountable_area VARCHAR(256) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    current_published_version_id UUID,
    lock_version BIGINT NOT NULL DEFAULT 0,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.enterprise-knowledge/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_knowledge_asset_id_tenant UNIQUE (id, tenant_id),
    CONSTRAINT uq_knowledge_asset_canonical UNIQUE (tenant_id, asset_type, canonical_key),
    CONSTRAINT fk_knowledge_asset_owner_tenant
        FOREIGN KEY (owner_user_id, tenant_id) REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_knowledge_asset_type CHECK (
        asset_type IN ('BUSINESS_TERM','METRIC','KPI','DIMENSION','ENTITY',
        'BUSINESS_RULE','ALIAS_SET','CALENDAR_POLICY','DATA_QUALITY_POLICY',
        'SEMANTIC_RELATION')
    ),
    CONSTRAINT ck_knowledge_asset_status CHECK (status IN ('ACTIVE','ARCHIVED','DELETED')),
    CONSTRAINT ck_knowledge_asset_lock CHECK (lock_version >= 0),
    CONSTRAINT ck_knowledge_asset_deleted CHECK (
        (status = 'DELETED' AND deleted_at IS NOT NULL)
        OR (status <> 'DELETED' AND deleted_at IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS enterprise_knowledge_versions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    asset_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    lifecycle VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    content JSONB NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    author_user_id UUID NOT NULL,
    previous_version_id UUID,
    source_kind VARCHAR(32) NOT NULL DEFAULT 'MANUAL',
    source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    effective_from TIMESTAMPTZ,
    effective_to TIMESTAMPTZ,
    lock_version BIGINT NOT NULL DEFAULT 0,
    rejection_comment TEXT,
    submitted_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.enterprise-knowledge/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_knowledge_version_asset_tenant UNIQUE (id, asset_id, tenant_id),
    CONSTRAINT uq_knowledge_version_number UNIQUE (asset_id, version_number),
    CONSTRAINT fk_knowledge_version_asset_tenant
        FOREIGN KEY (asset_id, tenant_id)
        REFERENCES enterprise_knowledge_assets(id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_version_author_tenant
        FOREIGN KEY (author_user_id, tenant_id) REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_knowledge_version_previous
        FOREIGN KEY (previous_version_id, asset_id, tenant_id)
        REFERENCES enterprise_knowledge_versions(id, asset_id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_knowledge_version_number CHECK (version_number >= 1),
    CONSTRAINT ck_knowledge_version_lock CHECK (lock_version >= 0),
    CONSTRAINT ck_knowledge_version_lifecycle CHECK (
        lifecycle IN ('DRAFT','IN_REVIEW','APPROVED','PUBLISHED',
        'REJECTED','DEPRECATED','ARCHIVED')
    ),
    CONSTRAINT ck_knowledge_version_checksum CHECK (checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_knowledge_version_content_object CHECK (jsonb_typeof(content) = 'object'),
    CONSTRAINT ck_knowledge_version_effective_period CHECK (
        effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from
    )
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_knowledge_asset_published_version'
    ) THEN
        ALTER TABLE enterprise_knowledge_assets
        ADD CONSTRAINT fk_knowledge_asset_published_version
        FOREIGN KEY (current_published_version_id, id, tenant_id)
        REFERENCES enterprise_knowledge_versions(id, asset_id, tenant_id) ON DELETE RESTRICT;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS enterprise_knowledge_approvals (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    asset_id UUID NOT NULL,
    version_id UUID NOT NULL,
    reviewer_user_id UUID NOT NULL,
    decision VARCHAR(16) NOT NULL,
    comment TEXT NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    version_checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_knowledge_approval_reviewer UNIQUE (tenant_id, version_id, reviewer_user_id),
    CONSTRAINT fk_knowledge_approval_version_tenant
        FOREIGN KEY (version_id, asset_id, tenant_id)
        REFERENCES enterprise_knowledge_versions(id, asset_id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_approval_reviewer_tenant
        FOREIGN KEY (reviewer_user_id, tenant_id) REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_knowledge_approval_decision CHECK (decision IN ('APPROVED','REJECTED')),
    CONSTRAINT ck_knowledge_approval_checksum CHECK (version_checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_knowledge_approval_comment CHECK (length(btrim(comment)) > 0)
);

CREATE TABLE IF NOT EXISTS enterprise_knowledge_publications (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    asset_id UUID NOT NULL,
    version_id UUID NOT NULL,
    publisher_user_id UUID NOT NULL,
    effective_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    superseded_version_id UUID,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.enterprise-knowledge/1.0',
    CONSTRAINT uq_knowledge_publication_version UNIQUE (tenant_id, version_id),
    CONSTRAINT fk_knowledge_publication_version_tenant
        FOREIGN KEY (version_id, asset_id, tenant_id)
        REFERENCES enterprise_knowledge_versions(id, asset_id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_knowledge_publication_publisher_tenant
        FOREIGN KEY (publisher_user_id, tenant_id) REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_knowledge_publication_superseded
        FOREIGN KEY (superseded_version_id, asset_id, tenant_id)
        REFERENCES enterprise_knowledge_versions(id, asset_id, tenant_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS enterprise_knowledge_aliases (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    asset_id UUID NOT NULL,
    version_id UUID NOT NULL,
    alias VARCHAR(256) NOT NULL,
    normalized_alias VARCHAR(256) NOT NULL,
    locale VARCHAR(16) NOT NULL DEFAULT 'pt-BR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_knowledge_alias_version
        UNIQUE (tenant_id, version_id, locale, normalized_alias),
    CONSTRAINT fk_knowledge_alias_version_tenant
        FOREIGN KEY (version_id, asset_id, tenant_id)
        REFERENCES enterprise_knowledge_versions(id, asset_id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT ck_knowledge_alias_nonempty CHECK (
        length(btrim(alias)) > 0 AND length(btrim(normalized_alias)) > 0
    )
);

CREATE TABLE IF NOT EXISTS enterprise_knowledge_relations (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    source_asset_id UUID NOT NULL,
    target_asset_id UUID NOT NULL,
    source_version_id UUID NOT NULL,
    relation_type VARCHAR(40) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_knowledge_relation_version
        UNIQUE (tenant_id, source_asset_id, target_asset_id, relation_type, source_version_id),
    CONSTRAINT fk_knowledge_relation_source_tenant
        FOREIGN KEY (source_asset_id, tenant_id)
        REFERENCES enterprise_knowledge_assets(id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_relation_target_tenant
        FOREIGN KEY (target_asset_id, tenant_id)
        REFERENCES enterprise_knowledge_assets(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_knowledge_relation_version_tenant
        FOREIGN KEY (source_version_id, source_asset_id, tenant_id)
        REFERENCES enterprise_knowledge_versions(id, asset_id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT ck_knowledge_relation_type CHECK (
        relation_type IN ('SYNONYM_OF','BROADER_THAN','NARROWER_THAN','RELATED_TO',
        'CALCULATED_FROM','ALLOWED_DIMENSION','INCOMPATIBLE_WITH','OWNED_BY',
        'SUPERSEDES','DEPENDS_ON')
    ),
    CONSTRAINT ck_knowledge_relation_self CHECK (source_asset_id <> target_asset_id)
);

CREATE TABLE IF NOT EXISTS enterprise_knowledge_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    asset_id UUID,
    version_id UUID,
    actor_user_id UUID NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    reason_code VARCHAR(128) NOT NULL,
    event_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.enterprise-knowledge/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_knowledge_event_actor_tenant
        FOREIGN KEY (actor_user_id, tenant_id) REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_knowledge_event_asset_tenant
        FOREIGN KEY (asset_id, tenant_id)
        REFERENCES enterprise_knowledge_assets(id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_event_version_tenant
        FOREIGN KEY (version_id, asset_id, tenant_id)
        REFERENCES enterprise_knowledge_versions(id, asset_id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT ck_knowledge_event_metadata CHECK (jsonb_typeof(event_metadata) = 'object')
);

CREATE TABLE IF NOT EXISTS enterprise_knowledge_imports (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    author_user_id UUID NOT NULL,
    source_format VARCHAR(16) NOT NULL,
    source_checksum VARCHAR(64) NOT NULL,
    idempotency_key_hash VARCHAR(64) NOT NULL,
    dry_run BOOLEAN NOT NULL DEFAULT TRUE,
    accepted_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.enterprise-knowledge/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_knowledge_import_idempotency UNIQUE (tenant_id, idempotency_key_hash),
    CONSTRAINT uq_knowledge_import_checksum_mode UNIQUE (tenant_id, source_checksum, dry_run),
    CONSTRAINT fk_knowledge_import_author_tenant
        FOREIGN KEY (author_user_id, tenant_id) REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_knowledge_import_format CHECK (source_format IN ('JSON','CSV','LEGACY')),
    CONSTRAINT ck_knowledge_import_checksum CHECK (source_checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_knowledge_import_idempotency CHECK (idempotency_key_hash ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_knowledge_import_counts CHECK (accepted_count >= 0 AND rejected_count >= 0),
    CONSTRAINT ck_knowledge_import_warnings CHECK (jsonb_typeof(warnings) = 'array')
);

CREATE OR REPLACE FUNCTION reject_published_knowledge_content_mutation()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.lifecycle IN ('APPROVED','PUBLISHED','DEPRECATED','ARCHIVED')
       AND (
           NEW.content IS DISTINCT FROM OLD.content
           OR NEW.checksum IS DISTINCT FROM OLD.checksum
           OR NEW.version_number IS DISTINCT FROM OLD.version_number
           OR NEW.author_user_id IS DISTINCT FROM OLD.author_user_id
           OR NEW.previous_version_id IS DISTINCT FROM OLD.previous_version_id
           OR NEW.source_kind IS DISTINCT FROM OLD.source_kind
           OR NEW.source_metadata IS DISTINCT FROM OLD.source_metadata
       )
    THEN
        RAISE EXCEPTION 'immutable enterprise knowledge version';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_knowledge_version_immutable ON enterprise_knowledge_versions;
CREATE TRIGGER trg_knowledge_version_immutable
BEFORE UPDATE ON enterprise_knowledge_versions
FOR EACH ROW EXECUTE FUNCTION reject_published_knowledge_content_mutation();

CREATE INDEX IF NOT EXISTS idx_knowledge_assets_tenant_type_key
    ON enterprise_knowledge_assets (tenant_id, asset_type, canonical_key);
CREATE INDEX IF NOT EXISTS idx_knowledge_assets_tenant_domain
    ON enterprise_knowledge_assets (tenant_id, domain, id);
CREATE INDEX IF NOT EXISTS idx_knowledge_assets_tenant_owner
    ON enterprise_knowledge_assets (tenant_id, owner_user_id, id);
CREATE INDEX IF NOT EXISTS idx_knowledge_assets_published
    ON enterprise_knowledge_assets (tenant_id, current_published_version_id)
    WHERE current_published_version_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_knowledge_versions_asset_version
    ON enterprise_knowledge_versions (tenant_id, asset_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_versions_tenant_lifecycle
    ON enterprise_knowledge_versions (tenant_id, lifecycle, updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_versions_effective
    ON enterprise_knowledge_versions (tenant_id, effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_knowledge_approvals_pending
    ON enterprise_knowledge_approvals (tenant_id, decision, created_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_publications_asset_time
    ON enterprise_knowledge_publications (tenant_id, asset_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_alias_lookup
    ON enterprise_knowledge_aliases (tenant_id, locale, normalized_alias, id);
CREATE INDEX IF NOT EXISTS idx_knowledge_relations_source
    ON enterprise_knowledge_relations (tenant_id, source_asset_id, relation_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_events_asset_time
    ON enterprise_knowledge_events (tenant_id, asset_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_events_type_time
    ON enterprise_knowledge_events (tenant_id, event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_imports_tenant_time
    ON enterprise_knowledge_imports (tenant_id, created_at DESC, id DESC);

INSERT INTO lumina_schema_migrations(version, description)
VALUES ('13.0', 'Governed enterprise knowledge lumina.enterprise-knowledge/1.0')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;
"""

DOWN_SQL = """
ALTER TABLE IF EXISTS enterprise_knowledge_assets
    DROP CONSTRAINT IF EXISTS fk_knowledge_asset_published_version;
DROP TABLE IF EXISTS enterprise_knowledge_imports;
DROP TABLE IF EXISTS enterprise_knowledge_events;
DROP TABLE IF EXISTS enterprise_knowledge_relations;
DROP TABLE IF EXISTS enterprise_knowledge_aliases;
DROP TABLE IF EXISTS enterprise_knowledge_publications;
DROP TABLE IF EXISTS enterprise_knowledge_approvals;
DROP TRIGGER IF EXISTS trg_knowledge_version_immutable ON enterprise_knowledge_versions;
DROP TABLE IF EXISTS enterprise_knowledge_versions;
DROP TABLE IF EXISTS enterprise_knowledge_assets;
DROP FUNCTION IF EXISTS reject_published_knowledge_content_mutation();
DO $$
BEGIN
    IF to_regclass('public.lumina_schema_migrations') IS NOT NULL THEN
        DELETE FROM lumina_schema_migrations WHERE version = '13.0';
    END IF;
END $$;
"""


def _dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


def _assert_disposable_test_target() -> None:
    if not settings.is_testing:
        raise RuntimeError("Migration v13 down is restricted to ENVIRONMENT=test.")
    if not settings.TEST_DATABASE_URL or settings.DATABASE_URL != settings.TEST_DATABASE_URL:
        raise RuntimeError("Migration v13 down requires the guarded TEST_DATABASE_URL.")


async def verify_schema(conn: asyncpg.Connection) -> dict[str, list[str]]:
    present = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "AND tablename = ANY($1::text[])",
        list(TABLES),
    )
    found = {row["tablename"] for row in present}
    missing = sorted(set(TABLES) - found)
    if missing:
        raise RuntimeError(f"Migration v13 verification failed; missing tables: {missing}")
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
