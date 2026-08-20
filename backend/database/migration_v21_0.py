"""Migration v21: governed smart cache and immutable materializations.

The migration is additive and idempotent. Both directions are restricted to a
connected, disposable PostgreSQL test target; production rollout is explicitly
outside this module's certification scope.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from sqlalchemy import text

from database import engine, get_db_context
from testing.database_guard import guard_engine_before_write


logger = logging.getLogger("luminaai.database.migration_v21_0")
MIGRATION_NAME = "v21_0_smart_cache_materialization"

TABLES = [
    "smart_cache_policies",
    "smart_cache_generations",
    "smart_cache_entries",
    "smart_cache_entry_dependencies",
    "smart_cache_leases",
    "smart_cache_events",
    "materialization_definitions",
    "materialization_builds",
    "materialization_snapshots",
    "materialization_publications",
    "materialization_dependencies",
    "materialization_events",
    "smart_cache_evaluation_cases",
    "smart_cache_evaluation_results",
]

UP_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS smart_cache_policies (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        policy_id VARCHAR(128) NOT NULL,
        policy_version VARCHAR(64) NOT NULL,
        contract_version VARCHAR(64) NOT NULL DEFAULT 'lumina.smart-cache-materialization/1.0',
        config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        checksum VARCHAR(64) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT true,
        lock_version BIGINT NOT NULL DEFAULT 1,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_smart_cache_policy_version UNIQUE (tenant_id, policy_id, policy_version),
        CONSTRAINT ck_smart_cache_policy_lock_version CHECK (lock_version >= 1),
        CONSTRAINT ck_smart_cache_policy_checksum CHECK (length(checksum) = 64),
        CONSTRAINT ck_smart_cache_policy_config_object CHECK (jsonb_typeof(config_json) = 'object')
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_policy_active ON smart_cache_policies (tenant_id, is_active, policy_id);",
    """
    CREATE TABLE IF NOT EXISTS smart_cache_generations (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        target_scope VARCHAR(128) NOT NULL,
        generation BIGINT NOT NULL DEFAULT 1,
        reason VARCHAR(256) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_smart_cache_generation_target UNIQUE (tenant_id, target_scope),
        CONSTRAINT ck_smart_cache_generation_counter CHECK (generation >= 0)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_generation_lookup ON smart_cache_generations (tenant_id, target_scope, generation);",
    """
    CREATE TABLE IF NOT EXISTS smart_cache_entries (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        cache_type VARCHAR(64) NOT NULL,
        cache_key_checksum VARCHAR(64) NOT NULL,
        scope_fingerprint VARCHAR(64) NOT NULL,
        permission_fingerprint VARCHAR(64) NOT NULL,
        query_fingerprint VARCHAR(64) NOT NULL,
        analytical_catalog_version VARCHAR(64) NOT NULL,
        source_sync_version VARCHAR(64) NOT NULL,
        source_watermark VARCHAR(128) NOT NULL,
        validation_policy_version VARCHAR(64) NOT NULL,
        compiler_version VARCHAR(64) NOT NULL,
        tool_registry_snapshot VARCHAR(128) NOT NULL,
        certification_id VARCHAR(128),
        tenant_proof_id VARCHAR(128),
        status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
        freshness VARCHAR(32) NOT NULL DEFAULT 'FRESH',
        generation BIGINT NOT NULL DEFAULT 1,
        hit_count BIGINT NOT NULL DEFAULT 0,
        payload_size_bytes INTEGER NOT NULL DEFAULT 0,
        classification VARCHAR(64) NOT NULL DEFAULT 'INTERNAL',
        payload_json JSONB NOT NULL,
        payload_checksum VARCHAR(64) NOT NULL,
        entry_checksum VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at TIMESTAMPTZ NOT NULL,
        invalidated_at TIMESTAMPTZ,
        CONSTRAINT uq_smart_cache_entry_key UNIQUE (tenant_id, cache_key_checksum),
        CONSTRAINT uq_smart_cache_entry_owner UNIQUE (id, tenant_id),
        CONSTRAINT ck_smart_cache_entry_payload_size CHECK (payload_size_bytes >= 0),
        CONSTRAINT ck_smart_cache_entry_generation CHECK (generation >= 0),
        CONSTRAINT ck_smart_cache_entry_hit_count CHECK (hit_count >= 0),
        CONSTRAINT ck_smart_cache_entry_ttl CHECK (expires_at > created_at),
        CONSTRAINT ck_smart_cache_entry_checksum CHECK (length(entry_checksum) = 64 AND length(payload_checksum) = 64),
        CONSTRAINT ck_smart_cache_entry_fingerprints CHECK (length(cache_key_checksum) = 64 AND length(scope_fingerprint) = 64 AND length(permission_fingerprint) = 64 AND length(query_fingerprint) = 64),
        CONSTRAINT ck_smart_cache_entry_type CHECK (cache_type <> 'FORBIDDEN'),
        CONSTRAINT ck_smart_cache_entry_classification CHECK (classification IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL')),
        CONSTRAINT ck_smart_cache_entry_status CHECK (status IN ('ACTIVE', 'STALE', 'EXPIRED', 'INVALIDATED', 'CORRUPTED', 'SUPERSEDED')),
        CONSTRAINT ck_smart_cache_entry_freshness CHECK (freshness IN ('FRESH', 'STALE_SOFT', 'STALE_HARD', 'UNKNOWN', 'INVALIDATED')),
        CONSTRAINT ck_smart_cache_certified_refs CHECK (cache_type NOT IN ('CERTIFIED_ANALYTICAL_RESULT', 'CERTIFICATION_ENVELOPE', 'PUBLIC_PROVENANCE') OR (certification_id IS NOT NULL AND tenant_proof_id IS NOT NULL))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_entry_lookup ON smart_cache_entries (tenant_id, cache_key_checksum, status, expires_at);",
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_entry_type_status ON smart_cache_entries (tenant_id, cache_type, status);",
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_entry_query ON smart_cache_entries (tenant_id, query_fingerprint);",
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_entry_generation ON smart_cache_entries (tenant_id, generation);",
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_entry_certification ON smart_cache_entries (tenant_id, certification_id);",
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_entry_expiration ON smart_cache_entries (tenant_id, expires_at) WHERE status IN ('ACTIVE', 'STALE');",
    """
    CREATE TABLE IF NOT EXISTS smart_cache_entry_dependencies (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        entry_id UUID NOT NULL,
        tag VARCHAR(256) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_smart_cache_dep_entry_tenant FOREIGN KEY (entry_id, tenant_id) REFERENCES smart_cache_entries(id, tenant_id) ON DELETE CASCADE,
        CONSTRAINT uq_smart_cache_entry_tag UNIQUE (tenant_id, entry_id, tag)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_entry_dep_tag ON smart_cache_entry_dependencies (tenant_id, tag, entry_id);",
    """
    CREATE TABLE IF NOT EXISTS smart_cache_leases (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        cache_key_checksum VARCHAR(64) NOT NULL,
        owner_token_checksum VARCHAR(64) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'HELD',
        lock_version BIGINT NOT NULL DEFAULT 1,
        acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at TIMESTAMPTZ NOT NULL,
        CONSTRAINT uq_smart_cache_lease_key UNIQUE (tenant_id, cache_key_checksum),
        CONSTRAINT ck_smart_cache_lease_key CHECK (length(cache_key_checksum) = 64),
        CONSTRAINT ck_smart_cache_lease_owner CHECK (length(owner_token_checksum) = 64),
        CONSTRAINT ck_smart_cache_lease_lock_version CHECK (lock_version >= 1),
        CONSTRAINT ck_smart_cache_lease_expiry CHECK (expires_at > acquired_at),
        CONSTRAINT ck_smart_cache_lease_status CHECK (status IN ('HELD', 'RELEASED', 'EXPIRED'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_lease_expiry ON smart_cache_leases (tenant_id, expires_at, status);",
    """
    CREATE TABLE IF NOT EXISTS smart_cache_events (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        event_type VARCHAR(64) NOT NULL,
        cache_key_checksum VARCHAR(64),
        user_id UUID,
        decision VARCHAR(32),
        reason_code VARCHAR(128) NOT NULL,
        details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT ck_smart_cache_event_details CHECK (jsonb_typeof(details_json) = 'object')
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_event_tenant_type ON smart_cache_events (tenant_id, event_type, created_at DESC);",
    """
    CREATE TABLE IF NOT EXISTS materialization_definitions (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        definition_id VARCHAR(128) NOT NULL,
        canonical_name VARCHAR(128) NOT NULL,
        materialization_type VARCHAR(64) NOT NULL,
        classification VARCHAR(64) NOT NULL DEFAULT 'INTERNAL',
        lifecycle VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
        version INTEGER NOT NULL DEFAULT 1,
        lock_version BIGINT NOT NULL DEFAULT 1,
        query_json JSONB NOT NULL,
        source_json JSONB NOT NULL,
        query_fingerprint VARCHAR(64) NOT NULL,
        checksum VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_materialization_definition_version UNIQUE (tenant_id, definition_id, version),
        CONSTRAINT ck_materialization_definition_version CHECK (version >= 1),
        CONSTRAINT ck_materialization_definition_lock_version CHECK (lock_version >= 1),
        CONSTRAINT ck_materialization_definition_checksum CHECK (length(checksum) = 64 AND length(query_fingerprint) = 64),
        CONSTRAINT ck_materialization_definition_type CHECK (materialization_type NOT IN ('ROW_LEVEL_DETAIL', 'FORBIDDEN')),
        CONSTRAINT ck_materialization_definition_classification CHECK (classification IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL')),
        CONSTRAINT ck_materialization_definition_lifecycle CHECK (lifecycle IN ('DRAFT','IN_REVIEW','APPROVED','BUILDING','VALIDATING','READY','PUBLISHED','STALE','FAILED','DISABLED','DEPRECATED','ARCHIVED'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_materialization_definition_state ON materialization_definitions (tenant_id, lifecycle, definition_id, version DESC);",
    "CREATE INDEX IF NOT EXISTS idx_materialization_definition_query ON materialization_definitions (tenant_id, query_fingerprint);",
    """
    CREATE TABLE IF NOT EXISTS materialization_builds (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        build_id VARCHAR(128) NOT NULL,
        definition_id VARCHAR(128) NOT NULL,
        definition_version INTEGER NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'BUILDING',
        error_code VARCHAR(128),
        build_duration_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
        snapshot_id VARCHAR(128),
        lock_version BIGINT NOT NULL DEFAULT 1,
        started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        completed_at TIMESTAMPTZ,
        CONSTRAINT fk_materialization_build_definition FOREIGN KEY (tenant_id, definition_id, definition_version) REFERENCES materialization_definitions(tenant_id, definition_id, version) ON DELETE CASCADE,
        CONSTRAINT uq_materialization_build_id UNIQUE (tenant_id, build_id),
        CONSTRAINT ck_materialization_build_version CHECK (definition_version >= 1),
        CONSTRAINT ck_materialization_build_duration CHECK (build_duration_ms >= 0),
        CONSTRAINT ck_materialization_build_lock CHECK (lock_version >= 1),
        CONSTRAINT ck_materialization_build_status CHECK (status IN ('BUILDING','VALIDATING','READY','FAILED','CANCELLED'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_materialization_build_state ON materialization_builds (tenant_id, definition_id, status, started_at DESC);",
    """
    CREATE TABLE IF NOT EXISTS materialization_snapshots (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        snapshot_id VARCHAR(128) NOT NULL,
        definition_id VARCHAR(128) NOT NULL,
        definition_version INTEGER NOT NULL,
        row_count INTEGER NOT NULL DEFAULT 0,
        fact_count INTEGER NOT NULL DEFAULT 0,
        payload_size_bytes INTEGER NOT NULL DEFAULT 0,
        certification_id VARCHAR(128) NOT NULL,
        certification_status VARCHAR(32) NOT NULL,
        tenant_proof_id VARCHAR(128) NOT NULL,
        watermark VARCHAR(128) NOT NULL,
        source_sync_version VARCHAR(64) NOT NULL,
        freshness VARCHAR(32) NOT NULL DEFAULT 'FRESH',
        payload_json JSONB NOT NULL,
        payload_checksum VARCHAR(64) NOT NULL,
        checksum VARCHAR(64) NOT NULL,
        built_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at TIMESTAMPTZ,
        CONSTRAINT fk_materialization_snapshot_definition FOREIGN KEY (tenant_id, definition_id, definition_version) REFERENCES materialization_definitions(tenant_id, definition_id, version) ON DELETE RESTRICT,
        CONSTRAINT uq_materialization_snapshot_id UNIQUE (tenant_id, snapshot_id),
        CONSTRAINT uq_materialization_snapshot_definition UNIQUE (tenant_id, definition_id, snapshot_id),
        CONSTRAINT ck_materialization_snapshot_version CHECK (definition_version >= 1),
        CONSTRAINT ck_materialization_snapshot_counts CHECK (row_count >= 0 AND fact_count >= 0 AND payload_size_bytes >= 0),
        CONSTRAINT ck_materialization_snapshot_checksum CHECK (length(checksum) = 64 AND length(payload_checksum) = 64),
        CONSTRAINT ck_materialization_snapshot_certification CHECK (certification_status IN ('VALID', 'VALID_WITH_WARNINGS')),
        CONSTRAINT ck_materialization_snapshot_expiry CHECK (expires_at IS NULL OR expires_at > built_at),
        CONSTRAINT ck_materialization_snapshot_freshness CHECK (freshness IN ('FRESH','STALE_SOFT','STALE_HARD','INVALIDATED'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_materialization_snapshot_state ON materialization_snapshots (tenant_id, definition_id, freshness, built_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_materialization_snapshot_cert ON materialization_snapshots (tenant_id, certification_id);",
    """
    CREATE TABLE IF NOT EXISTS materialization_publications (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        definition_id VARCHAR(128) NOT NULL,
        definition_version INTEGER NOT NULL,
        active_snapshot_id VARCHAR(128) NOT NULL,
        previous_snapshot_id VARCHAR(128),
        published_by UUID NOT NULL,
        lock_version BIGINT NOT NULL DEFAULT 1,
        published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_materialization_publication_definition FOREIGN KEY (tenant_id, definition_id, definition_version) REFERENCES materialization_definitions(tenant_id, definition_id, version) ON DELETE RESTRICT,
        CONSTRAINT fk_materialization_publication_active FOREIGN KEY (tenant_id, definition_id, active_snapshot_id) REFERENCES materialization_snapshots(tenant_id, definition_id, snapshot_id) ON DELETE RESTRICT,
        CONSTRAINT fk_materialization_publication_previous FOREIGN KEY (tenant_id, definition_id, previous_snapshot_id) REFERENCES materialization_snapshots(tenant_id, definition_id, snapshot_id) ON DELETE RESTRICT,
        CONSTRAINT uq_materialization_active_pub UNIQUE (tenant_id, definition_id),
        CONSTRAINT ck_materialization_publication_version CHECK (definition_version >= 1),
        CONSTRAINT ck_materialization_publication_lock CHECK (lock_version >= 1)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_materialization_publication_snapshot ON materialization_publications (tenant_id, active_snapshot_id);",
    """
    CREATE TABLE IF NOT EXISTS materialization_dependencies (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        definition_id VARCHAR(128) NOT NULL,
        definition_version INTEGER NOT NULL,
        tag VARCHAR(256) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_materialization_dependency_definition FOREIGN KEY (tenant_id, definition_id, definition_version) REFERENCES materialization_definitions(tenant_id, definition_id, version) ON DELETE CASCADE,
        CONSTRAINT uq_materialization_dep_tag UNIQUE (tenant_id, definition_id, definition_version, tag)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_materialization_dependency_tag ON materialization_dependencies (tenant_id, tag, definition_id);",
    """
    CREATE TABLE IF NOT EXISTS materialization_events (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        definition_id VARCHAR(128) NOT NULL,
        event_type VARCHAR(64) NOT NULL,
        user_id UUID,
        details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT ck_materialization_event_details CHECK (jsonb_typeof(details_json) = 'object')
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_materialization_event_tenant ON materialization_events (tenant_id, definition_id, event_type, created_at DESC);",
    """
    CREATE TABLE IF NOT EXISTS smart_cache_evaluation_cases (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        case_id VARCHAR(128) NOT NULL,
        description TEXT NOT NULL,
        scenario_type VARCHAR(64) NOT NULL,
        canonical_query_fingerprint VARCHAR(64) NOT NULL,
        expected_decision VARCHAR(32) NOT NULL,
        expected_freshness VARCHAR(32) NOT NULL,
        checksum VARCHAR(64) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_smart_cache_eval_case UNIQUE (tenant_id, case_id),
        CONSTRAINT uq_smart_cache_eval_owner UNIQUE (tenant_id, case_id, checksum),
        CONSTRAINT ck_smart_cache_eval_case_checksum CHECK (length(checksum) = 64 AND length(canonical_query_fingerprint) = 64)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_eval_case_active ON smart_cache_evaluation_cases (tenant_id, is_active, scenario_type);",
    """
    CREATE TABLE IF NOT EXISTS smart_cache_evaluation_results (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        case_id VARCHAR(128) NOT NULL,
        case_checksum VARCHAR(64) NOT NULL,
        actual_decision VARCHAR(32) NOT NULL,
        actual_freshness VARCHAR(32) NOT NULL,
        passed BOOLEAN NOT NULL,
        details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_smart_cache_eval_result_case FOREIGN KEY (tenant_id, case_id, case_checksum) REFERENCES smart_cache_evaluation_cases(tenant_id, case_id, checksum) ON DELETE CASCADE,
        CONSTRAINT ck_smart_cache_eval_result_details CHECK (jsonb_typeof(details_json) = 'object')
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_smart_cache_eval_result_case ON smart_cache_evaluation_results (tenant_id, case_id, evaluated_at DESC);",
]

DOWN_STATEMENTS = [
    f"DROP TABLE IF EXISTS {table_name} CASCADE;" for table_name in reversed(TABLES)
]


async def _execute(statements: Sequence[str]) -> None:
    await guard_engine_before_write(engine)
    async with get_db_context() as session:
        for statement in statements:
            await session.execute(text(statement))


async def run_up(*, statements: Sequence[str] | None = None) -> dict[str, Any]:
    """Create v21 only on the connected disposable PostgreSQL test target."""
    selected = tuple(statements) if statements is not None else tuple(UP_STATEMENTS)
    await _execute(selected)
    return {"status": "SUCCESS", "migration": MIGRATION_NAME, "tables_affected": TABLES}


async def run_down(*, confirm_test_only: bool = False) -> dict[str, Any]:
    """Drop v21 only after an explicit test-only confirmation."""
    if not confirm_test_only:
        raise RuntimeError("v21 down is restricted to a disposable test database")
    await _execute(DOWN_STATEMENTS)
    return {"status": "SUCCESS", "migration": f"{MIGRATION_NAME}_down", "tables_dropped": TABLES}
