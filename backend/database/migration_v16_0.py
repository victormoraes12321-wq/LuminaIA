"""Migration v16.0 - governed semantic retrieval and entity resolution.

Additive, extension-free and independent from ``create_all``. Downgrade is
restricted to the guarded disposable PostgreSQL test environment.
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


VERSION = "16.0"
CONTRACT_VERSION = "lumina.semantic-retrieval/1.0"
TABLES = (
    "semantic_index_definitions",
    "semantic_index_versions",
    "semantic_documents",
    "semantic_document_aliases",
    "semantic_document_relations",
    "semantic_document_terms",
    "semantic_document_representations",
    "semantic_index_publications",
    "semantic_index_events",
    "semantic_evaluation_cases",
    "semantic_evaluation_results",
    "semantic_clarifications",
)

UP_SQL = r"""
CREATE TABLE IF NOT EXISTS lumina_schema_migrations (
    version VARCHAR(32) PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS semantic_index_definitions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(128) NOT NULL,
    locale VARCHAR(16) NOT NULL DEFAULT 'pt-BR',
    document_types JSONB NOT NULL,
    entity_policies JSONB NOT NULL,
    source_policies JSONB NOT NULL,
    classification_policy JSONB NOT NULL,
    representation_provider VARCHAR(64) NOT NULL,
    representation_version VARCHAR(128) NOT NULL,
    representation_dimension INTEGER NOT NULL,
    ranking_policy JSONB NOT NULL,
    threshold_policy JSONB NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    owner_user_id UUID NOT NULL,
    active_version_id UUID,
    lock_version BIGINT NOT NULL DEFAULT 0,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.semantic-retrieval/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_semantic_index_tenant UNIQUE (id, tenant_id),
    CONSTRAINT uq_semantic_index_name UNIQUE (tenant_id, name),
    CONSTRAINT fk_semantic_index_owner FOREIGN KEY (owner_user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_semantic_index_status CHECK (status IN ('ACTIVE','DISABLED','ARCHIVED')),
    CONSTRAINT ck_semantic_index_lock CHECK (lock_version >= 0),
    CONSTRAINT ck_semantic_index_dimension CHECK (representation_dimension BETWEEN 32 AND 4096),
    CONSTRAINT ck_semantic_index_json CHECK (
        jsonb_typeof(document_types) = 'array'
        AND jsonb_typeof(entity_policies) = 'array'
        AND jsonb_typeof(source_policies) = 'array'
        AND jsonb_typeof(classification_policy) = 'array'
        AND jsonb_typeof(ranking_policy) = 'object'
        AND jsonb_typeof(threshold_policy) = 'object'
    )
);

CREATE TABLE IF NOT EXISTS semantic_index_versions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    index_id UUID NOT NULL,
    version INTEGER NOT NULL,
    lifecycle VARCHAR(24) NOT NULL DEFAULT 'DRAFT',
    source_manifest JSONB NOT NULL,
    document_count INTEGER NOT NULL DEFAULT 0,
    entity_count INTEGER NOT NULL DEFAULT 0,
    alias_count INTEGER NOT NULL DEFAULT 0,
    relation_count INTEGER NOT NULL DEFAULT 0,
    representation_version VARCHAR(128) NOT NULL,
    build_mode VARCHAR(16) NOT NULL DEFAULT 'FULL',
    idempotency_key_hash VARCHAR(64) NOT NULL,
    watermark VARCHAR(256),
    build_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    build_completed_at TIMESTAMPTZ,
    checksum VARCHAR(64),
    created_by UUID NOT NULL,
    reviewed_by UUID,
    published_by UUID,
    published_at TIMESTAMPTZ,
    superseded_version_id UUID,
    failure_summary VARCHAR(256),
    lock_version BIGINT NOT NULL DEFAULT 0,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.semantic-retrieval/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_semantic_version_scope UNIQUE (id, index_id, tenant_id),
    CONSTRAINT uq_semantic_version_number UNIQUE (tenant_id, index_id, version),
    CONSTRAINT uq_semantic_version_idempotency UNIQUE (
        tenant_id, index_id, idempotency_key_hash
    ),
    CONSTRAINT fk_semantic_version_index FOREIGN KEY (index_id, tenant_id)
        REFERENCES semantic_index_definitions(id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_semantic_version_creator FOREIGN KEY (created_by, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_semantic_version_reviewer FOREIGN KEY (reviewed_by, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_semantic_version_publisher FOREIGN KEY (published_by, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_semantic_version_positive CHECK (version > 0),
    CONSTRAINT ck_semantic_version_lock CHECK (lock_version >= 0),
    CONSTRAINT ck_semantic_version_lifecycle CHECK (
        lifecycle IN ('DRAFT','BUILDING','VALIDATING','READY','PUBLISHED',
                      'FAILED','DEPRECATED','ARCHIVED')
    ),
    CONSTRAINT ck_semantic_version_build_mode CHECK (build_mode IN ('FULL','INCREMENTAL')),
    CONSTRAINT ck_semantic_version_idempotency CHECK (
        idempotency_key_hash ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT ck_semantic_version_counts CHECK (
        document_count >= 0 AND entity_count >= 0
        AND alias_count >= 0 AND relation_count >= 0
    ),
    CONSTRAINT ck_semantic_version_checksum CHECK (
        checksum IS NULL OR checksum ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT ck_semantic_version_manifest CHECK (jsonb_typeof(source_manifest) = 'object'),
    CONSTRAINT ck_semantic_version_timestamps CHECK (
        build_completed_at IS NULL OR build_completed_at >= build_started_at
    )
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_semantic_index_active_version'
    ) THEN
        ALTER TABLE semantic_index_definitions
            ADD CONSTRAINT fk_semantic_index_active_version
            FOREIGN KEY (active_version_id, id, tenant_id)
            REFERENCES semantic_index_versions(id, index_id, tenant_id)
            ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS semantic_documents (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    index_id UUID NOT NULL,
    index_version_id UUID NOT NULL,
    document_type VARCHAR(40) NOT NULL,
    canonical_key VARCHAR(256) NOT NULL,
    display_label VARCHAR(256) NOT NULL,
    normalized_label VARCHAR(256) NOT NULL,
    locale VARCHAR(16) NOT NULL,
    domain VARCHAR(128) NOT NULL,
    entity_type VARCHAR(40) NOT NULL,
    description TEXT,
    source_type VARCHAR(48) NOT NULL,
    source_id VARCHAR(256) NOT NULL,
    source_version VARCHAR(128) NOT NULL,
    source_checksum VARCHAR(64) NOT NULL,
    lifecycle VARCHAR(24) NOT NULL DEFAULT 'ACTIVE',
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,
    classification VARCHAR(48) NOT NULL,
    permission_requirement VARCHAR(64),
    representation_version VARCHAR(128) NOT NULL,
    content JSONB NOT NULL,
    provenance JSONB NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.semantic-retrieval/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_semantic_document_scope UNIQUE (id, tenant_id, index_version_id),
    CONSTRAINT uq_semantic_document_canonical UNIQUE (
        tenant_id, index_version_id, canonical_key, document_type
    ),
    CONSTRAINT fk_semantic_document_version FOREIGN KEY (
        index_version_id, index_id, tenant_id
    ) REFERENCES semantic_index_versions(id, index_id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT ck_semantic_document_type CHECK (
        document_type IN ('BUSINESS_TERM','METRIC','KPI','DIMENSION','ENTITY_TYPE',
                          'ENTITY_INSTANCE','BUSINESS_RULE','ALIAS','RELATION',
                          'CALENDAR_POLICY','APPROVED_TRAINING_EXAMPLE','SYSTEM_CONCEPT')
    ),
    CONSTRAINT ck_semantic_document_entity_type CHECK (
        entity_type IN ('METRIC','DIMENSION','BUSINESS_CONCEPT','BRANCH','PRODUCT',
                        'PRODUCT_GROUP','CUSTOMER','SUPPLIER','SELLER','REGION','CITY',
                        'STATE','COST_CENTER','WAREHOUSE','PAYMENT_METHOD',
                        'RECEIVABLE_STATUS','STOCK_LOCATION','UNKNOWN')
    ),
    CONSTRAINT ck_semantic_document_classification CHECK (
        classification IN ('PUBLIC_BUSINESS_METADATA','TENANT_BUSINESS_METADATA',
                           'RESTRICTED_BUSINESS_METADATA','PERSONAL_DATA')
    ),
    CONSTRAINT ck_semantic_document_lifecycle CHECK (
        lifecycle IN ('ACTIVE','DEPRECATED','TOMBSTONED')
    ),
    CONSTRAINT ck_semantic_document_checksum CHECK (checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_semantic_document_source_checksum CHECK (
        source_checksum ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT ck_semantic_document_effective CHECK (
        valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from
    ),
    CONSTRAINT ck_semantic_document_json CHECK (
        jsonb_typeof(content) = 'object' AND jsonb_typeof(provenance) = 'object'
    )
);

CREATE TABLE IF NOT EXISTS semantic_document_aliases (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    index_version_id UUID NOT NULL,
    document_id UUID NOT NULL,
    alias VARCHAR(256) NOT NULL,
    normalized_alias VARCHAR(256) NOT NULL,
    locale VARCHAR(16) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_semantic_alias_scope UNIQUE (id, tenant_id),
    CONSTRAINT uq_semantic_alias_document UNIQUE (
        tenant_id, index_version_id, document_id, normalized_alias
    ),
    CONSTRAINT fk_semantic_alias_document FOREIGN KEY (
        document_id, tenant_id, index_version_id
    ) REFERENCES semantic_documents(id, tenant_id, index_version_id) ON DELETE CASCADE,
    CONSTRAINT ck_semantic_alias_checksum CHECK (checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS semantic_document_relations (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    index_version_id UUID NOT NULL,
    source_document_id UUID NOT NULL,
    target_document_id UUID NOT NULL,
    relation_type VARCHAR(48) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_semantic_relation UNIQUE (
        tenant_id, index_version_id, source_document_id, target_document_id, relation_type
    ),
    CONSTRAINT fk_semantic_relation_source FOREIGN KEY (
        source_document_id, tenant_id, index_version_id
    ) REFERENCES semantic_documents(id, tenant_id, index_version_id) ON DELETE CASCADE,
    CONSTRAINT fk_semantic_relation_target FOREIGN KEY (
        target_document_id, tenant_id, index_version_id
    ) REFERENCES semantic_documents(id, tenant_id, index_version_id) ON DELETE CASCADE,
    CONSTRAINT ck_semantic_relation_distinct CHECK (source_document_id <> target_document_id)
);

CREATE TABLE IF NOT EXISTS semantic_document_terms (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    index_version_id UUID NOT NULL,
    document_id UUID NOT NULL,
    term VARCHAR(256) NOT NULL,
    term_kind VARCHAR(24) NOT NULL,
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    CONSTRAINT uq_semantic_term UNIQUE (
        tenant_id, index_version_id, document_id, term, term_kind
    ),
    CONSTRAINT fk_semantic_term_document FOREIGN KEY (
        document_id, tenant_id, index_version_id
    ) REFERENCES semantic_documents(id, tenant_id, index_version_id) ON DELETE CASCADE,
    CONSTRAINT ck_semantic_term_weight CHECK (weight BETWEEN 0 AND 1)
);

CREATE TABLE IF NOT EXISTS semantic_document_representations (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    index_version_id UUID NOT NULL,
    document_id UUID NOT NULL,
    representation_type VARCHAR(48) NOT NULL,
    representation_version VARCHAR(128) NOT NULL,
    dimension INTEGER,
    representation JSONB NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    CONSTRAINT uq_semantic_representation UNIQUE (
        tenant_id, index_version_id, document_id,
        representation_type, representation_version
    ),
    CONSTRAINT fk_semantic_representation_document FOREIGN KEY (
        document_id, tenant_id, index_version_id
    ) REFERENCES semantic_documents(id, tenant_id, index_version_id) ON DELETE CASCADE,
    CONSTRAINT ck_semantic_representation_type CHECK (
        representation_type IN ('LEXICAL','DETERMINISTIC_FEATURE_HASH')
    ),
    CONSTRAINT ck_semantic_representation_dimension CHECK (
        dimension IS NULL OR dimension BETWEEN 32 AND 4096
    ),
    CONSTRAINT ck_semantic_representation_json CHECK (
        jsonb_typeof(representation) = 'object'
    ),
    CONSTRAINT ck_semantic_representation_checksum CHECK (
        checksum ~ '^[a-f0-9]{64}$'
    )
);

CREATE TABLE IF NOT EXISTS semantic_index_publications (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    index_id UUID NOT NULL,
    version_id UUID NOT NULL,
    previous_version_id UUID,
    published_by UUID NOT NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason VARCHAR(256) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    CONSTRAINT uq_semantic_publication_scope UNIQUE (id, tenant_id),
    CONSTRAINT fk_semantic_publication_version FOREIGN KEY (
        version_id, index_id, tenant_id
    ) REFERENCES semantic_index_versions(id, index_id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_semantic_publication_user FOREIGN KEY (published_by, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_semantic_publication_checksum CHECK (checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS semantic_index_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    index_id UUID,
    version_id UUID,
    actor_user_id UUID NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    reason_code VARCHAR(128) NOT NULL,
    structural_fingerprint VARCHAR(64) NOT NULL,
    event_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.semantic-retrieval/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_semantic_event_scope UNIQUE (id, tenant_id),
    CONSTRAINT fk_semantic_event_actor FOREIGN KEY (actor_user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_semantic_event_fingerprint CHECK (
        structural_fingerprint ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT ck_semantic_event_json CHECK (jsonb_typeof(event_metadata) = 'object')
);

CREATE TABLE IF NOT EXISTS semantic_evaluation_cases (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    corpus_version VARCHAR(128) NOT NULL,
    case_key VARCHAR(256) NOT NULL,
    case_data JSONB NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_semantic_evaluation_case UNIQUE (
        tenant_id, corpus_version, case_key
    ),
    CONSTRAINT ck_semantic_evaluation_case_json CHECK (
        jsonb_typeof(case_data) = 'object'
    ),
    CONSTRAINT ck_semantic_case_checksum CHECK (checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS semantic_evaluation_results (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    index_id UUID NOT NULL,
    index_version_id UUID NOT NULL,
    corpus_version VARCHAR(128) NOT NULL,
    case_count INTEGER NOT NULL,
    passed BOOLEAN NOT NULL,
    metrics JSONB NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_semantic_evaluation_result UNIQUE (id, tenant_id),
    CONSTRAINT fk_semantic_evaluation_version FOREIGN KEY (
        index_version_id, index_id, tenant_id
    ) REFERENCES semantic_index_versions(id, index_id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT ck_semantic_evaluation_metrics CHECK (jsonb_typeof(metrics) = 'array'),
    CONSTRAINT ck_semantic_evaluation_checksum CHECK (checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS semantic_clarifications (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    mention_id UUID NOT NULL,
    options JSONB NOT NULL,
    options_checksum VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    expires_at TIMESTAMPTZ NOT NULL,
    resolved_document_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT uq_semantic_clarification UNIQUE (id, tenant_id, user_id),
    CONSTRAINT fk_semantic_clarification_user FOREIGN KEY (user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT ck_semantic_clarification_status CHECK (
        status IN ('PENDING','RESOLVED','EXPIRED','CANCELLED')
    ),
    CONSTRAINT ck_semantic_clarification_checksum CHECK (
        options_checksum ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT ck_semantic_clarification_options CHECK (jsonb_typeof(options) = 'array'),
    CONSTRAINT ck_semantic_clarification_expiry CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_semantic_index_tenant_status
    ON semantic_index_definitions(tenant_id, status, id);
CREATE INDEX IF NOT EXISTS idx_semantic_index_active
    ON semantic_index_definitions(tenant_id, active_version_id);
CREATE INDEX IF NOT EXISTS idx_semantic_versions_index
    ON semantic_index_versions(tenant_id, index_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_versions_lifecycle
    ON semantic_index_versions(tenant_id, lifecycle, id);
CREATE INDEX IF NOT EXISTS idx_semantic_document_type
    ON semantic_documents(tenant_id, index_version_id, document_type);
CREATE INDEX IF NOT EXISTS idx_semantic_document_canonical
    ON semantic_documents(tenant_id, index_version_id, canonical_key);
CREATE INDEX IF NOT EXISTS idx_semantic_document_label
    ON semantic_documents(tenant_id, index_version_id, normalized_label);
CREATE INDEX IF NOT EXISTS idx_semantic_document_entity
    ON semantic_documents(tenant_id, index_version_id, entity_type, domain);
CREATE INDEX IF NOT EXISTS idx_semantic_document_source
    ON semantic_documents(tenant_id, source_type, source_id, source_version);
CREATE INDEX IF NOT EXISTS idx_semantic_document_effective
    ON semantic_documents(tenant_id, lifecycle, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_semantic_alias_lookup
    ON semantic_document_aliases(tenant_id, index_version_id, normalized_alias);
CREATE INDEX IF NOT EXISTS idx_semantic_relation_source
    ON semantic_document_relations(tenant_id, index_version_id, source_document_id);
CREATE INDEX IF NOT EXISTS idx_semantic_relation_target
    ON semantic_document_relations(tenant_id, index_version_id, target_document_id);
CREATE INDEX IF NOT EXISTS idx_semantic_term_lookup
    ON semantic_document_terms(tenant_id, index_version_id, term, term_kind);
CREATE INDEX IF NOT EXISTS idx_semantic_representation_lookup
    ON semantic_document_representations(
        tenant_id, index_version_id, representation_type
    );
CREATE INDEX IF NOT EXISTS idx_semantic_publication_index
    ON semantic_index_publications(tenant_id, index_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_event_timeline
    ON semantic_index_events(tenant_id, index_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_event_type
    ON semantic_index_events(tenant_id, event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_semantic_evaluation_corpus
    ON semantic_evaluation_cases(tenant_id, corpus_version, case_key);
CREATE INDEX IF NOT EXISTS idx_semantic_evaluation_version
    ON semantic_evaluation_results(tenant_id, index_version_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_clarification_pending
    ON semantic_clarifications(
        tenant_id, user_id, session_id, status, expires_at
    );

CREATE OR REPLACE FUNCTION prevent_published_semantic_mutation()
RETURNS trigger AS $$
BEGIN
    IF OLD.lifecycle IN ('PUBLISHED','DEPRECATED','ARCHIVED') AND (
        NEW.index_id IS DISTINCT FROM OLD.index_id
        OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
        OR NEW.version IS DISTINCT FROM OLD.version
        OR NEW.source_manifest IS DISTINCT FROM OLD.source_manifest
        OR NEW.document_count IS DISTINCT FROM OLD.document_count
        OR NEW.entity_count IS DISTINCT FROM OLD.entity_count
        OR NEW.alias_count IS DISTINCT FROM OLD.alias_count
        OR NEW.relation_count IS DISTINCT FROM OLD.relation_count
        OR NEW.representation_version IS DISTINCT FROM OLD.representation_version
        OR NEW.checksum IS DISTINCT FROM OLD.checksum
    ) THEN
        RAISE EXCEPTION 'published semantic index version is immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_semantic_version_immutable ON semantic_index_versions;
CREATE TRIGGER trg_semantic_version_immutable
BEFORE UPDATE ON semantic_index_versions
FOR EACH ROW EXECUTE FUNCTION prevent_published_semantic_mutation();

INSERT INTO lumina_schema_migrations(version, description)
VALUES ('16.0', 'Governed semantic retrieval and entity resolution')
ON CONFLICT (version) DO NOTHING;
"""

DOWN_SQL = r"""
DROP TABLE IF EXISTS semantic_clarifications;
DROP TABLE IF EXISTS semantic_evaluation_results;
DROP TABLE IF EXISTS semantic_evaluation_cases;
DROP TABLE IF EXISTS semantic_index_events;
DROP TABLE IF EXISTS semantic_index_publications;
DROP TABLE IF EXISTS semantic_document_representations;
DROP TABLE IF EXISTS semantic_document_terms;
DROP TABLE IF EXISTS semantic_document_relations;
DROP TABLE IF EXISTS semantic_document_aliases;
DROP TABLE IF EXISTS semantic_documents;
ALTER TABLE IF EXISTS semantic_index_definitions
    DROP CONSTRAINT IF EXISTS fk_semantic_index_active_version;
DROP TRIGGER IF EXISTS trg_semantic_version_immutable ON semantic_index_versions;
DROP FUNCTION IF EXISTS prevent_published_semantic_mutation();
DROP TABLE IF EXISTS semantic_index_versions;
DROP TABLE IF EXISTS semantic_index_definitions;
DO $$
BEGIN
    IF to_regclass('public.lumina_schema_migrations') IS NOT NULL THEN
        DELETE FROM lumina_schema_migrations WHERE version = '16.0';
    END IF;
END $$;
"""


def _dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


def _assert_disposable_test_target() -> None:
    if not settings.is_testing:
        raise RuntimeError("Migration v16 down is restricted to ENVIRONMENT=test.")
    if not settings.TEST_DATABASE_URL or settings.DATABASE_URL != settings.TEST_DATABASE_URL:
        raise RuntimeError("Migration v16 down requires the guarded TEST_DATABASE_URL.")


async def verify_schema(conn: asyncpg.Connection) -> dict[str, list[str]]:
    present = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "AND tablename = ANY($1::text[])",
        list(TABLES),
    )
    found = {row["tablename"] for row in present}
    missing = sorted(set(TABLES) - found)
    if missing:
        raise RuntimeError(f"Migration v16 verification failed; missing tables: {missing}")
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
