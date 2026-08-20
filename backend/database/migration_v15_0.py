"""Migration v15.0 - governed feedback and supervised learning datasets.

Additive and independent from ``create_all``. Downgrade is restricted to the
guarded disposable PostgreSQL test environment.
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


VERSION = "15.0"
CONTRACT_VERSION = "lumina.supervised-feedback/1.0"
TABLES = (
    "governed_feedback_records",
    "governed_feedback_corrections",
    "governed_feedback_redactions",
    "governed_feedback_reviews",
    "governed_feedback_events",
    "supervised_training_candidates",
    "supervised_training_examples",
    "training_dataset_snapshots",
    "training_dataset_members",
    "training_dataset_exports",
    "feedback_deletion_requests",
)

UP_SQL = r"""
CREATE TABLE IF NOT EXISTS lumina_schema_migrations (
    version VARCHAR(32) PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_conversation_node_owner') THEN
        ALTER TABLE conversation_nodes
            ADD CONSTRAINT uq_conversation_node_owner UNIQUE (id, tenant_id, user_id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS governed_feedback_records (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    response_node_id UUID NOT NULL,
    session_id UUID NOT NULL,
    public_session_id VARCHAR(128) NOT NULL,
    query_node_id UUID,
    response_checksum VARCHAR(64) NOT NULL,
    response_contract_version VARCHAR(64) NOT NULL,
    category VARCHAR(40) NOT NULL,
    explanation TEXT,
    lifecycle VARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
    severity VARCHAR(16),
    priority VARCHAR(8),
    review_queue VARCHAR(32),
    triage_data JSONB,
    duplicate_fingerprint VARCHAR(64) NOT NULL,
    redaction_manifest_id UUID NOT NULL,
    reviewer_user_id UUID,
    review_decision VARCHAR(32),
    idempotency_key_hash VARCHAR(64) NOT NULL,
    lock_version BIGINT NOT NULL DEFAULT 0,
    checksum VARCHAR(64) NOT NULL,
    schema_version VARCHAR(64) NOT NULL DEFAULT 'lumina.supervised-feedback/1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retention_at TIMESTAMPTZ,
    withdrawn_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    CONSTRAINT uq_feedback_tenant UNIQUE (id, tenant_id),
    CONSTRAINT uq_feedback_owner UNIQUE (id, tenant_id, user_id),
    CONSTRAINT uq_feedback_idempotency UNIQUE (tenant_id, user_id, idempotency_key_hash),
    CONSTRAINT fk_feedback_author_tenant FOREIGN KEY (user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_feedback_response_owner FOREIGN KEY (response_node_id, tenant_id, user_id)
        REFERENCES conversation_nodes(id, tenant_id, user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_feedback_reviewer_tenant FOREIGN KEY (reviewer_user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_feedback_lifecycle CHECK (lifecycle IN (
        'RECEIVED','VALIDATED','TRIAGED','IN_REVIEW','APPROVED','REJECTED',
        'NEEDS_INFORMATION','WITHDRAWN','EXPIRED','ARCHIVED'
    )),
    CONSTRAINT ck_feedback_category CHECK (category IN (
        'POSITIVE','NEGATIVE','PARTIALLY_CORRECT','INCORRECT_VALUE','INCORRECT_FILTER',
        'INCORRECT_PERIOD','INCORRECT_METRIC','INCORRECT_ENTITY','INCORRECT_DIMENSION',
        'INCORRECT_COMPARISON','INCORRECT_VISUALIZATION','MISSING_CONTEXT',
        'UNWANTED_INHERITANCE','MISSING_INHERITANCE','AMBIGUOUS','OUT_OF_SCOPE',
        'UNSAFE_OUTPUT','PERFORMANCE','OTHER'
    )),
    CONSTRAINT ck_feedback_lock CHECK (lock_version >= 0),
    CONSTRAINT ck_feedback_checksum CHECK (checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_feedback_response_checksum CHECK (response_checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_feedback_duplicate CHECK (duplicate_fingerprint ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_feedback_idempotency CHECK (idempotency_key_hash ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_feedback_no_self_review CHECK (
        reviewer_user_id IS NULL OR reviewer_user_id <> user_id
    ),
    CONSTRAINT ck_feedback_timestamps CHECK (updated_at >= created_at),
    CONSTRAINT ck_feedback_triage_json CHECK (
        triage_data IS NULL OR jsonb_typeof(triage_data) = 'object'
    )
);

CREATE TABLE IF NOT EXISTS governed_feedback_corrections (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    feedback_id UUID NOT NULL,
    correction JSONB NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_feedback_correction UNIQUE (feedback_id, tenant_id, user_id),
    CONSTRAINT fk_feedback_correction_owner FOREIGN KEY (feedback_id, tenant_id, user_id)
        REFERENCES governed_feedback_records(id, tenant_id, user_id) ON DELETE CASCADE,
    CONSTRAINT ck_feedback_correction_json CHECK (jsonb_typeof(correction) = 'object'),
    CONSTRAINT ck_feedback_correction_checksum CHECK (checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS governed_feedback_redactions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    feedback_id UUID NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    manifest JSONB NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_feedback_redaction_tenant UNIQUE (id, tenant_id),
    CONSTRAINT fk_feedback_redaction_owner FOREIGN KEY (feedback_id, tenant_id, user_id)
        REFERENCES governed_feedback_records(id, tenant_id, user_id) ON DELETE CASCADE,
    CONSTRAINT ck_feedback_redaction_json CHECK (jsonb_typeof(manifest) = 'object'),
    CONSTRAINT ck_feedback_redaction_checksum CHECK (checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS governed_feedback_reviews (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    feedback_id UUID NOT NULL,
    reviewer_user_id UUID NOT NULL,
    decision VARCHAR(32) NOT NULL,
    rationale TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_feedback_review_scope UNIQUE (id, feedback_id, tenant_id),
    CONSTRAINT fk_feedback_review_record FOREIGN KEY (feedback_id, tenant_id)
        REFERENCES governed_feedback_records(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_feedback_review_reviewer FOREIGN KEY (reviewer_user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_feedback_review_decision CHECK (decision IN (
        'CORRECT','ACCEPTABLE','PARTIALLY_CORRECT','INCORRECT','UNVERIFIABLE',
        'AMBIGUOUS','OUT_OF_SCOPE','UNSAFE','TECHNICAL_FAILURE'
    )),
    CONSTRAINT ck_feedback_review_evidence CHECK (jsonb_typeof(evidence) = 'array'),
    CONSTRAINT ck_feedback_review_checksum CHECK (checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS governed_feedback_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    feedback_id UUID,
    actor_user_id UUID NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    reason_code VARCHAR(128) NOT NULL,
    request_id VARCHAR(128),
    event_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_feedback_event_actor FOREIGN KEY (actor_user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_feedback_event_json CHECK (jsonb_typeof(event_metadata) = 'object'),
    CONSTRAINT ck_feedback_event_checksum CHECK (checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS supervised_training_candidates (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    feedback_id UUID NOT NULL,
    created_by_user_id UUID NOT NULL,
    reviewed_by_user_id UUID,
    status VARCHAR(24) NOT NULL DEFAULT 'CANDIDATE',
    input_data JSONB NOT NULL,
    expected_output JSONB NOT NULL,
    quality_status VARCHAR(32) NOT NULL,
    quality_rule_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    lock_version BIGINT NOT NULL DEFAULT 0,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_training_candidate_tenant UNIQUE (id, tenant_id),
    CONSTRAINT uq_training_candidate_feedback UNIQUE (feedback_id, tenant_id),
    CONSTRAINT fk_training_candidate_feedback FOREIGN KEY (feedback_id, tenant_id)
        REFERENCES governed_feedback_records(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_training_candidate_creator FOREIGN KEY (created_by_user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_training_candidate_status CHECK (status IN (
        'CANDIDATE','VALIDATED','APPROVED','REJECTED','IN_DATASET','DEPRECATED','ARCHIVED'
    )),
    CONSTRAINT ck_training_candidate_quality CHECK (quality_status IN (
        'VALID','INCOMPLETE','AMBIGUOUS','SENSITIVE','CONFLICTING','OUTDATED_CONTRACT','BLOCKED'
    )),
    CONSTRAINT ck_training_candidate_lock CHECK (lock_version >= 0),
    CONSTRAINT ck_training_candidate_checksum CHECK (checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_training_candidate_input CHECK (jsonb_typeof(input_data) = 'object'),
    CONSTRAINT ck_training_candidate_output CHECK (jsonb_typeof(expected_output) = 'object'),
    CONSTRAINT ck_training_candidate_rules CHECK (jsonb_typeof(quality_rule_ids) = 'array')
);

CREATE TABLE IF NOT EXISTS supervised_training_examples (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    candidate_id UUID NOT NULL,
    reviewer_user_id UUID NOT NULL,
    curator_user_id UUID NOT NULL,
    example_data JSONB NOT NULL,
    quality_score INTEGER NOT NULL,
    restrictions JSONB NOT NULL DEFAULT '[]'::jsonb,
    checksum VARCHAR(64) NOT NULL,
    deprecated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_training_example_tenant UNIQUE (id, tenant_id),
    CONSTRAINT uq_training_example_candidate UNIQUE (candidate_id, tenant_id),
    CONSTRAINT fk_training_example_candidate FOREIGN KEY (candidate_id, tenant_id)
        REFERENCES supervised_training_candidates(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_training_example_quality CHECK (quality_score BETWEEN 0 AND 100),
    CONSTRAINT ck_training_example_data CHECK (jsonb_typeof(example_data) = 'object'),
    CONSTRAINT ck_training_example_restrictions CHECK (jsonb_typeof(restrictions) = 'array'),
    CONSTRAINT ck_training_example_checksum CHECK (checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS training_dataset_snapshots (
    id UUID PRIMARY KEY,
    dataset_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    version INTEGER NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    purpose VARCHAR(500) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'DRAFT',
    manifest JSONB NOT NULL,
    created_by_user_id UUID NOT NULL,
    reviewed_by_user_id UUID,
    approved_by_user_id UUID,
    lock_version BIGINT NOT NULL DEFAULT 0,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    CONSTRAINT uq_dataset_snapshot_tenant UNIQUE (id, tenant_id),
    CONSTRAINT uq_dataset_version UNIQUE (dataset_id, tenant_id, version),
    CONSTRAINT fk_dataset_creator FOREIGN KEY (created_by_user_id, tenant_id)
        REFERENCES users(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_dataset_version CHECK (version >= 1),
    CONSTRAINT ck_dataset_lock CHECK (lock_version >= 0),
    CONSTRAINT ck_dataset_checksum CHECK (checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_dataset_manifest CHECK (jsonb_typeof(manifest) = 'object'),
    CONSTRAINT ck_dataset_status CHECK (status IN (
        'DRAFT','IN_REVIEW','APPROVED','PUBLISHED','REJECTED','DEPRECATED','ARCHIVED'
    )),
    CONSTRAINT ck_dataset_published_at CHECK (
        (status = 'PUBLISHED' AND published_at IS NOT NULL) OR status <> 'PUBLISHED'
    )
);

CREATE TABLE IF NOT EXISTS training_dataset_members (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    snapshot_id UUID NOT NULL,
    example_id UUID NOT NULL,
    position INTEGER NOT NULL,
    example_checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_dataset_member UNIQUE (snapshot_id, example_id, tenant_id),
    CONSTRAINT fk_dataset_member_snapshot FOREIGN KEY (snapshot_id, tenant_id)
        REFERENCES training_dataset_snapshots(id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_dataset_member_example FOREIGN KEY (example_id, tenant_id)
        REFERENCES supervised_training_examples(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_dataset_member_position CHECK (position >= 0),
    CONSTRAINT ck_dataset_member_checksum CHECK (example_checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS training_dataset_exports (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    snapshot_id UUID NOT NULL,
    created_by_user_id UUID NOT NULL,
    format VARCHAR(16) NOT NULL,
    purpose VARCHAR(500) NOT NULL,
    record_count INTEGER NOT NULL,
    payload_size INTEGER NOT NULL,
    manifest_checksum VARCHAR(64) NOT NULL,
    content_checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_dataset_export_snapshot FOREIGN KEY (snapshot_id, tenant_id)
        REFERENCES training_dataset_snapshots(id, tenant_id) ON DELETE RESTRICT,
    CONSTRAINT ck_dataset_export_format CHECK (format IN ('JSONL','CSV')),
    CONSTRAINT ck_dataset_export_count CHECK (record_count >= 0),
    CONSTRAINT ck_dataset_export_size CHECK (payload_size >= 0),
    CONSTRAINT ck_dataset_export_manifest CHECK (manifest_checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_dataset_export_checksum CHECK (content_checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS feedback_deletion_requests (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    feedback_id UUID NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    reason TEXT,
    idempotency_key_hash VARCHAR(64) NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_feedback_deletion_idempotency
        UNIQUE (tenant_id, user_id, idempotency_key_hash),
    CONSTRAINT fk_feedback_deletion_owner FOREIGN KEY (feedback_id, tenant_id, user_id)
        REFERENCES governed_feedback_records(id, tenant_id, user_id) ON DELETE RESTRICT,
    CONSTRAINT ck_feedback_deletion_status CHECK (status IN ('PENDING','COMPLETED','REJECTED')),
    CONSTRAINT ck_feedback_deletion_idempotency CHECK (
        idempotency_key_hash ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT ck_feedback_deletion_time CHECK (
        completed_at IS NULL OR completed_at >= requested_at
    )
);

CREATE INDEX IF NOT EXISTS idx_feedback_owner_created
    ON governed_feedback_records (tenant_id, user_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_lifecycle
    ON governed_feedback_records (tenant_id, lifecycle, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_category
    ON governed_feedback_records (tenant_id, category, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_severity
    ON governed_feedback_records (tenant_id, severity, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_target
    ON governed_feedback_records (tenant_id, response_node_id);
CREATE INDEX IF NOT EXISTS idx_feedback_duplicate
    ON governed_feedback_records (tenant_id, duplicate_fingerprint);
CREATE INDEX IF NOT EXISTS idx_feedback_review_queue
    ON governed_feedback_records (tenant_id, review_queue, lifecycle);
CREATE INDEX IF NOT EXISTS idx_feedback_reviewer
    ON governed_feedback_records (tenant_id, reviewer_user_id, lifecycle);
CREATE INDEX IF NOT EXISTS idx_feedback_retention
    ON governed_feedback_records (tenant_id, retention_at);
CREATE INDEX IF NOT EXISTS idx_feedback_reviews_reviewer
    ON governed_feedback_reviews (tenant_id, reviewer_user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_events_tenant_time
    ON governed_feedback_events (tenant_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_events_record
    ON governed_feedback_events (tenant_id, feedback_id, created_at);
CREATE INDEX IF NOT EXISTS idx_training_candidates_status
    ON supervised_training_candidates (tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_training_examples_tenant
    ON supervised_training_examples (tenant_id, created_at, id);
CREATE INDEX IF NOT EXISTS idx_dataset_versions
    ON training_dataset_snapshots (tenant_id, dataset_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_dataset_status
    ON training_dataset_snapshots (tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_dataset_members_snapshot
    ON training_dataset_members (tenant_id, snapshot_id, position);
CREATE INDEX IF NOT EXISTS idx_dataset_exports_tenant
    ON training_dataset_exports (tenant_id, created_at, id);
CREATE INDEX IF NOT EXISTS idx_feedback_deletions_status
    ON feedback_deletion_requests (tenant_id, status, requested_at, id);

INSERT INTO lumina_schema_migrations(version, description)
VALUES ('15.0', 'Governed feedback and supervised learning lumina.supervised-feedback/1.0')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;
"""

DOWN_SQL = r"""
DROP TABLE IF EXISTS feedback_deletion_requests;
DROP TABLE IF EXISTS training_dataset_exports;
DROP TABLE IF EXISTS training_dataset_members;
DROP TABLE IF EXISTS training_dataset_snapshots;
DROP TABLE IF EXISTS supervised_training_examples;
DROP TABLE IF EXISTS supervised_training_candidates;
DROP TABLE IF EXISTS governed_feedback_events;
DROP TABLE IF EXISTS governed_feedback_reviews;
DROP TABLE IF EXISTS governed_feedback_redactions;
DROP TABLE IF EXISTS governed_feedback_corrections;
DROP TABLE IF EXISTS governed_feedback_records;
ALTER TABLE IF EXISTS conversation_nodes
    DROP CONSTRAINT IF EXISTS uq_conversation_node_owner;
DO $$
BEGIN
    IF to_regclass('public.lumina_schema_migrations') IS NOT NULL THEN
        DELETE FROM lumina_schema_migrations WHERE version = '15.0';
    END IF;
END $$;
"""


def _dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


def _assert_disposable_test_target() -> None:
    if not settings.is_testing:
        raise RuntimeError("Migration v15 down is restricted to ENVIRONMENT=test.")
    if not settings.TEST_DATABASE_URL or settings.DATABASE_URL != settings.TEST_DATABASE_URL:
        raise RuntimeError("Migration v15 down requires the guarded TEST_DATABASE_URL.")


async def verify_schema(conn: asyncpg.Connection) -> dict[str, list[str]]:
    present = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "AND tablename = ANY($1::text[])",
        list(TABLES),
    )
    found = {row["tablename"] for row in present}
    missing = sorted(set(TABLES) - found)
    if missing:
        raise RuntimeError(f"Migration v15 verification failed; missing tables: {missing}")
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
