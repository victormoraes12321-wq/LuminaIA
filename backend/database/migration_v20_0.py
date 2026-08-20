from __future__ import annotations

import logging
from typing import Any, Dict
from sqlalchemy import text

from database import get_db_context

logger = logging.getLogger("luminaai.database.migration_v20_0")

TABLES = [
    "validation_policies",
    "validation_runs",
    "analytical_facts",
    "analytical_claims",
    "analytical_claim_bindings",
    "provenance_manifests",
    "result_certifications",
    "response_certifications",
    "validation_events",
]


async def run_up() -> Dict[str, Any]:
    """
    Migration v20_0 — Governed Validation & Provenance Layer.
    Idempotent creation of validation policies, runs, facts, claims, bindings,
    provenance manifests, result/response certifications, and audit events.
    """
    logger.info("Executing migration v20_0 UP...")

    statements = [
        """
        CREATE TABLE IF NOT EXISTS validation_policies (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            policy_name VARCHAR(255) NOT NULL,
            version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
            required_stages JSONB NOT NULL DEFAULT '[]'::jsonb,
            validators_config JSONB NOT NULL DEFAULT '[]'::jsonb,
            fail_fast BOOLEAN NOT NULL DEFAULT TRUE,
            allow_partial BOOLEAN NOT NULL DEFAULT FALSE,
            require_fact_bindings BOOLEAN NOT NULL DEFAULT TRUE,
            strict_decimal BOOLEAN NOT NULL DEFAULT TRUE,
            freshness_tolerance_seconds INTEGER NOT NULL DEFAULT 86400,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            lock_version BIGINT NOT NULL DEFAULT 1,
            checksum VARCHAR(64) NOT NULL,
            created_at VARCHAR(64) NOT NULL,
            CONSTRAINT uq_validation_policy_tenant_name_ver UNIQUE (tenant_id, policy_name, version),
            CONSTRAINT ck_validation_policy_lock_ver CHECK (lock_version >= 1)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_val_policy_tenant ON validation_policies(tenant_id, is_active);
        """,
        """
        CREATE TABLE IF NOT EXISTS validation_runs (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            request_id VARCHAR(128) NOT NULL,
            orchestration_run_id VARCHAR(128),
            overall_status VARCHAR(32) NOT NULL,
            total_execution_time_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            lock_version BIGINT NOT NULL DEFAULT 1,
            checksum VARCHAR(64) NOT NULL,
            created_at VARCHAR(64) NOT NULL,
            CONSTRAINT ck_validation_run_lock_ver CHECK (lock_version >= 1)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_val_run_tenant_status ON validation_runs(tenant_id, overall_status);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_val_run_req ON validation_runs(tenant_id, request_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS analytical_facts (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            fact_id VARCHAR(128) NOT NULL,
            fact_type VARCHAR(64) NOT NULL,
            canonical_metric_id VARCHAR(128),
            period_start VARCHAR(64),
            period_end VARCHAR(64),
            decimal_value VARCHAR(128),
            int_value BIGINT,
            string_value TEXT,
            unit VARCHAR(64),
            currency VARCHAR(16),
            completeness VARCHAR(64) NOT NULL DEFAULT 'COMPLETE',
            source_result_ref VARCHAR(128) NOT NULL,
            metric_fingerprint VARCHAR(64),
            tenant_proof_checksum VARCHAR(64) NOT NULL,
            validation_status VARCHAR(32) NOT NULL DEFAULT 'VALID',
            checksum VARCHAR(64) NOT NULL,
            created_at VARCHAR(64) NOT NULL,
            CONSTRAINT uq_analytical_fact_tenant_fact_ck UNIQUE (tenant_id, fact_id, checksum)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fact_tenant_type ON analytical_facts(tenant_id, fact_type);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fact_metric ON analytical_facts(tenant_id, canonical_metric_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS analytical_claims (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            claim_id VARCHAR(128) NOT NULL,
            claim_type VARCHAR(64) NOT NULL,
            text TEXT NOT NULL,
            origin VARCHAR(64) NOT NULL DEFAULT 'MODEL_PROPOSED',
            checksum VARCHAR(64) NOT NULL,
            created_at VARCHAR(64) NOT NULL,
            CONSTRAINT uq_analytical_claim_tenant_claim_ck UNIQUE (tenant_id, claim_id, checksum)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_claim_tenant_type ON analytical_claims(tenant_id, claim_type);
        """,
        """
        CREATE TABLE IF NOT EXISTS analytical_claim_bindings (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            claim_id VARCHAR(128) NOT NULL,
            fact_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            validation_status VARCHAR(32) NOT NULL,
            public_display_value TEXT,
            canonical_value_checksum VARCHAR(64) NOT NULL,
            mismatch_reason TEXT,
            created_at VARCHAR(64) NOT NULL
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_claim_bind_tenant_claim ON analytical_claim_bindings(tenant_id, claim_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS provenance_manifests (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            request_id VARCHAR(128) NOT NULL,
            graph_data JSONB NOT NULL,
            graph_checksum VARCHAR(64) NOT NULL,
            fact_count INTEGER NOT NULL DEFAULT 0,
            claim_count INTEGER NOT NULL DEFAULT 0,
            manifest_checksum VARCHAR(64) NOT NULL,
            created_at VARCHAR(64) NOT NULL
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_prov_manifest_tenant_req ON provenance_manifests(tenant_id, request_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS result_certifications (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            request_id VARCHAR(128) NOT NULL,
            result_checksum VARCHAR(64) NOT NULL,
            query_fingerprint VARCHAR(64),
            tenant_proof_checksum VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            certified_at VARCHAR(64) NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            CONSTRAINT uq_result_cert_tenant_req_res UNIQUE (tenant_id, request_id, result_checksum)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_res_cert_tenant_req ON result_certifications(tenant_id, request_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS response_certifications (
            id UUID PRIMARY KEY,
            result_certification_id UUID NOT NULL REFERENCES result_certifications(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            request_id VARCHAR(128) NOT NULL,
            response_draft_checksum VARCHAR(64) NOT NULL,
            claim_validation_data JSONB NOT NULL,
            status VARCHAR(32) NOT NULL,
            superseded_by_id UUID,
            lock_version BIGINT NOT NULL DEFAULT 1,
            certified_at VARCHAR(64) NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            CONSTRAINT ck_resp_cert_lock_ver CHECK (lock_version >= 1)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_resp_cert_tenant_req ON response_certifications(tenant_id, request_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS validation_events (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            event_type VARCHAR(64) NOT NULL,
            certification_id UUID,
            severity VARCHAR(32) NOT NULL DEFAULT 'INFO',
            message TEXT NOT NULL,
            details JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at VARCHAR(64) NOT NULL
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_val_event_tenant_type ON validation_events(tenant_id, event_type);
        """,
    ]

    async with get_db_context() as session:
        for stmt in statements:
            await session.execute(text(stmt))
        await session.commit()

    logger.info("Migration v20_0 UP executed successfully.")
    return {"status": "SUCCESS", "migration": "v20_0", "tables_affected": TABLES}


async def run_down() -> Dict[str, Any]:
    """
    Migration v20_0 DOWN — Test-only rollback of validation & provenance tables.
    """
    logger.info("Executing migration v20_0 DOWN...")
    async with get_db_context() as session:
        for table in reversed(TABLES):
            await session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
        await session.commit()

    logger.info("Migration v20_0 DOWN executed successfully.")
    return {"status": "SUCCESS", "migration": "v20_0_down", "tables_dropped": TABLES}
