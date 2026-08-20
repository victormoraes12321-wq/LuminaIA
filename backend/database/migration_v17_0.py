from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy import text
from database import get_db_context

logger = logging.getLogger("luminaai.database.migration_v17_0")

TABLES = [
    "ai_tool_identities",
    "ai_tool_versions",
    "ai_tool_reviews",
    "ai_tool_publications",
    "ai_tool_registry_snapshots",
    "ai_tool_registry_members",
    "ai_tool_dependencies",
    "ai_tool_events",
    "ai_tool_invocation_records",
    "ai_tool_circuit_states",
    "ai_tool_evaluation_cases",
    "ai_tool_evaluation_results",
]


async def run_up() -> Dict[str, Any]:
    """
    Migration v17_0 — Governed AI Tool Registry Schema.
    Idempotent creation of tables, constraints, and indexes.
    """
    logger.info("Executing migration v17_0 UP...")

    statements = [
        """
        CREATE TABLE IF NOT EXISTS ai_tool_identities (
            id UUID PRIMARY KEY,
            tool_id VARCHAR(128) NOT NULL,
            canonical_name VARCHAR(128) NOT NULL,
            display_name VARCHAR(128) NOT NULL,
            description TEXT NOT NULL,
            domain VARCHAR(64) NOT NULL DEFAULT 'business_intelligence',
            tool_type VARCHAR(64) NOT NULL DEFAULT 'DOMAIN_READ',
            capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
            risk_class VARCHAR(32) NOT NULL DEFAULT 'LOW',
            side_effect VARCHAR(32) NOT NULL DEFAULT 'READ_ONLY',
            network_class VARCHAR(32) NOT NULL DEFAULT 'INTERNAL_SERVICE_ONLY',
            data_class VARCHAR(32) NOT NULL DEFAULT 'TENANT_BUSINESS_DATA',
            owner_id VARCHAR(128) NOT NULL DEFAULT 'system',
            tenant_id VARCHAR(128) NOT NULL DEFAULT 'system',
            scope VARCHAR(32) NOT NULL DEFAULT 'SYSTEM',
            checksum VARCHAR(64) NOT NULL,
            contract_version VARCHAR(64) NOT NULL DEFAULT 'lumina.ai-tool-registry/1.0',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_tool_identity_tenant UNIQUE (id, tenant_id),
            CONSTRAINT uq_ai_tool_canonical_name UNIQUE (tenant_id, canonical_name),
            CONSTRAINT ck_ai_tool_risk CHECK (risk_class IN ('LOW','MODERATE','HIGH','CRITICAL','FORBIDDEN')),
            CONSTRAINT ck_ai_tool_side_effect CHECK (side_effect IN ('NONE','READ_ONLY','CACHE_ONLY','STATEFUL_IDEMPOTENT','STATEFUL_NON_IDEMPOTENT','ADMINISTRATIVE','DESTRUCTIVE','FORBIDDEN')),
            CONSTRAINT ck_ai_tool_network CHECK (network_class IN ('NO_NETWORK','INTERNAL_SERVICE_ONLY','ALLOWLISTED_EXTERNAL','ARBITRARY_EXTERNAL','FORBIDDEN')),
            CONSTRAINT ck_ai_tool_data_class CHECK (data_class IN ('PUBLIC_METADATA','TENANT_METADATA','TENANT_BUSINESS_DATA','RESTRICTED_BUSINESS_DATA','PERSONAL_DATA','SENSITIVE_PERSONAL_DATA','SECRET','FORBIDDEN'))
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_canonical_name ON ai_tool_identities(tenant_id, canonical_name);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_risk_side_effect ON ai_tool_identities(risk_class, side_effect);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_versions (
            id UUID PRIMARY KEY,
            tool_identity_id UUID NOT NULL,
            tool_id VARCHAR(128) NOT NULL,
            version VARCHAR(32) NOT NULL,
            adapter_id VARCHAR(128) NOT NULL,
            input_contract JSONB NOT NULL,
            output_contract JSONB NOT NULL,
            execution_policy JSONB NOT NULL,
            dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
            lifecycle VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
            author_id VARCHAR(128) NOT NULL,
            reviewer_id VARCHAR(128),
            published_by VARCHAR(128),
            tenant_id VARCHAR(128) NOT NULL DEFAULT 'system',
            effective_from TIMESTAMP WITH TIME ZONE,
            effective_to TIMESTAMP WITH TIME ZONE,
            lock_version INTEGER NOT NULL DEFAULT 1,
            checksum VARCHAR(64) NOT NULL,
            contract_version VARCHAR(64) NOT NULL DEFAULT 'lumina.ai-tool-registry/1.0',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_tool_version_tenant UNIQUE (id, tenant_id),
            CONSTRAINT uq_ai_tool_version_identity UNIQUE (tool_identity_id, version),
            CONSTRAINT fk_ai_tool_version_identity FOREIGN KEY (tool_identity_id, tenant_id) REFERENCES ai_tool_identities(id, tenant_id) ON DELETE CASCADE,
            CONSTRAINT ck_ai_tool_lifecycle CHECK (lifecycle IN ('DRAFT','IN_REVIEW','APPROVED','ACTIVE','DEPRECATED','DISABLED','RETIRED','REJECTED')),
            CONSTRAINT ck_ai_tool_version_lock CHECK (lock_version >= 1)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_version_lifecycle ON ai_tool_versions(tool_id, lifecycle);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_version_adapter ON ai_tool_versions(adapter_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_reviews (
            id UUID PRIMARY KEY,
            tool_version_id UUID NOT NULL,
            reviewer_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL DEFAULT 'system',
            approved BOOLEAN NOT NULL,
            review_notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_ai_tool_review_version FOREIGN KEY (tool_version_id, tenant_id) REFERENCES ai_tool_versions(id, tenant_id) ON DELETE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_review_version ON ai_tool_reviews(tool_version_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_publications (
            id UUID PRIMARY KEY,
            tool_version_id UUID NOT NULL,
            published_by VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL DEFAULT 'system',
            publication_notes TEXT NOT NULL DEFAULT '',
            checksum VARCHAR(64) NOT NULL,
            published_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_ai_tool_pub_version FOREIGN KEY (tool_version_id, tenant_id) REFERENCES ai_tool_versions(id, tenant_id) ON DELETE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_pub_version ON ai_tool_publications(tool_version_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_registry_snapshots (
            id UUID PRIMARY KEY,
            snapshot_id VARCHAR(128) NOT NULL,
            version VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'READY',
            active_tool_versions JSONB NOT NULL,
            disabled_tool_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            dependency_graph_checksum VARCHAR(64) NOT NULL,
            created_by VARCHAR(128) NOT NULL,
            published_by VARCHAR(128),
            previous_snapshot_id VARCHAR(128),
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT uq_ai_tool_snapshot_id UNIQUE (snapshot_id),
            CONSTRAINT ck_ai_tool_snapshot_status CHECK (status IN ('DRAFT','VALIDATING','READY','PUBLISHED','REJECTED','DEPRECATED','ARCHIVED'))
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_snapshot_status ON ai_tool_registry_snapshots(status);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_registry_members (
            id UUID PRIMARY KEY,
            snapshot_id UUID NOT NULL,
            tool_version_id UUID NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            checksum VARCHAR(64) NOT NULL,
            CONSTRAINT fk_ai_tool_member_snapshot FOREIGN KEY (snapshot_id) REFERENCES ai_tool_registry_snapshots(id) ON DELETE CASCADE,
            CONSTRAINT fk_ai_tool_member_version FOREIGN KEY (tool_version_id) REFERENCES ai_tool_versions(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_member_snapshot ON ai_tool_registry_members(snapshot_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_dependencies (
            id UUID PRIMARY KEY,
            tool_version_id UUID NOT NULL,
            target_tool_id VARCHAR(128) NOT NULL,
            min_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
            max_version VARCHAR(32),
            dependency_type VARCHAR(32) NOT NULL DEFAULT 'REQUIRED',
            checksum VARCHAR(64) NOT NULL,
            CONSTRAINT fk_ai_tool_dep_version FOREIGN KEY (tool_version_id) REFERENCES ai_tool_versions(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_dep_version ON ai_tool_dependencies(tool_version_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_events (
            id UUID PRIMARY KEY,
            tenant_id VARCHAR(128) NOT NULL,
            user_id VARCHAR(128) NOT NULL,
            event_type VARCHAR(64) NOT NULL,
            tool_id VARCHAR(128) NOT NULL,
            version VARCHAR(32),
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_event_tenant_type ON ai_tool_events(tenant_id, event_type);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_event_created ON ai_tool_events(created_at);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_invocation_records (
            id UUID PRIMARY KEY,
            request_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL,
            user_id VARCHAR(128) NOT NULL,
            tool_id VARCHAR(128) NOT NULL,
            version VARCHAR(32) NOT NULL,
            snapshot_id VARCHAR(128) NOT NULL,
            duration_ms DOUBLE PRECISION NOT NULL,
            status VARCHAR(32) NOT NULL,
            error_code VARCHAR(64),
            input_checksum VARCHAR(64) NOT NULL,
            output_checksum VARCHAR(64) NOT NULL,
            cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
            circuit_state VARCHAR(32) NOT NULL DEFAULT 'CLOSED',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_inv_tenant_tool ON ai_tool_invocation_records(tenant_id, tool_id, created_at);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_inv_status ON ai_tool_invocation_records(status);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_circuit_states (
            id UUID PRIMARY KEY,
            tool_id VARCHAR(128) NOT NULL,
            version VARCHAR(32) NOT NULL,
            adapter_id VARCHAR(128) NOT NULL,
            state VARCHAR(32) NOT NULL DEFAULT 'CLOSED',
            failure_count INTEGER NOT NULL DEFAULT 0,
            success_count INTEGER NOT NULL DEFAULT 0,
            last_failure_at TIMESTAMP WITH TIME ZONE,
            last_state_change TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_tool_circuit_state UNIQUE (tool_id, version, adapter_id),
            CONSTRAINT ck_ai_tool_circuit_state CHECK (state IN ('CLOSED','OPEN','HALF_OPEN'))
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_evaluation_cases (
            id UUID PRIMARY KEY,
            case_id VARCHAR(128) NOT NULL,
            tool_id VARCHAR(128) NOT NULL,
            name VARCHAR(128) NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            input_fixture JSONB NOT NULL,
            expected_output_fixture JSONB,
            expected_error_code VARCHAR(64),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_tool_eval_case_id UNIQUE (case_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_tool_evaluation_results (
            id UUID PRIMARY KEY,
            evaluation_id VARCHAR(128) NOT NULL,
            case_id VARCHAR(128) NOT NULL,
            tool_id VARCHAR(128) NOT NULL,
            version VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL,
            passed BOOLEAN NOT NULL,
            execution_time_ms DOUBLE PRECISION NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_tool_eval_result_case ON ai_tool_evaluation_results(case_id);
        """,
    ]

    async with get_db_context() as session:
        for stmt in statements:
            await session.execute(text(stmt))
        await session.commit()

    return {
        "status": "success",
        "tables": sorted(TABLES),
        "constraints": [
            "uq_ai_tool_identity_tenant",
            "uq_ai_tool_canonical_name",
            "uq_ai_tool_version_tenant",
            "uq_ai_tool_version_identity",
            "uq_ai_tool_snapshot_id",
            "uq_ai_tool_circuit_state",
            "uq_ai_tool_eval_case_id",
        ],
        "indexes": [
            "idx_ai_tool_canonical_name",
            "idx_ai_tool_risk_side_effect",
            "idx_ai_tool_version_lifecycle",
            "idx_ai_tool_version_adapter",
            "idx_ai_tool_review_version",
            "idx_ai_tool_pub_version",
            "idx_ai_tool_snapshot_status",
            "idx_ai_tool_member_snapshot",
            "idx_ai_tool_dep_version",
            "idx_ai_tool_event_tenant_type",
            "idx_ai_tool_event_created",
            "idx_ai_tool_inv_tenant_tool",
            "idx_ai_tool_inv_status",
            "idx_ai_tool_eval_result_case",
        ],
    }


async def run_down(confirm_test_only: bool = False) -> Dict[str, Any]:
    """
    Migration v17_0 DOWN.
    ONLY for disposable test environment.
    """
    if not confirm_test_only:
        raise RuntimeError("run_down is strictly restricted to disposable test environment.")

    logger.warning("Executing migration v17_0 DOWN (Test Environment)...")

    drop_statements = [
        "DROP TABLE IF EXISTS ai_tool_evaluation_results CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_evaluation_cases CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_circuit_states CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_invocation_records CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_events CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_dependencies CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_registry_members CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_registry_snapshots CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_publications CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_reviews CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_versions CASCADE;",
        "DROP TABLE IF EXISTS ai_tool_identities CASCADE;",
    ]

    async with get_db_context() as session:
        for stmt in drop_statements:
            await session.execute(text(stmt))
        await session.commit()

    return {"status": "success", "dropped_tables": TABLES}
