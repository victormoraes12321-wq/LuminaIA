from __future__ import annotations

import logging
from typing import Any, Dict
from sqlalchemy import text

from database import get_db_context

logger = logging.getLogger("luminaai.database.migration_v19_0")

TABLES = [
    "ai_orchestration_policies",
    "ai_model_definitions",
    "ai_provider_definitions",
    "ai_prompt_template_versions",
    "ai_orchestration_runs",
    "ai_orchestration_steps",
    "ai_model_invocations",
    "ai_orchestration_tool_calls",
    "ai_orchestration_usage_records",
    "ai_orchestration_evaluation_cases",
    "ai_orchestration_evaluation_results",
]


async def run_up() -> Dict[str, Any]:
    """
    Migration v19_0 — AI Orchestration and Token Control Layer.
    Idempotent creation of orchestration tables, constraints, and indexes.
    """
    logger.info("Executing migration v19_0 UP...")

    statements = [
        """
        CREATE TABLE IF NOT EXISTS ai_orchestration_policies (
            id UUID PRIMARY KEY,
            policy_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL DEFAULT 'system',
            policy_data JSONB NOT NULL,
            version VARCHAR(32) NOT NULL DEFAULT 'lumina.ai-orchestration/1.0',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_orchestration_policy UNIQUE (tenant_id, policy_id)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_orch_policy_tenant ON ai_orchestration_policies(tenant_id, is_active);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_model_definitions (
            id UUID PRIMARY KEY,
            canonical_model_id VARCHAR(128) NOT NULL,
            provider_id VARCHAR(64) NOT NULL,
            internal_provider_model_name VARCHAR(128) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            definition_data JSONB NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_model_def_canonical UNIQUE (canonical_model_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_provider_definitions (
            id UUID PRIMARY KEY,
            provider_id VARCHAR(64) NOT NULL,
            display_name VARCHAR(128) NOT NULL,
            adapter_class VARCHAR(256) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            definition_data JSONB NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_provider_def_id UNIQUE (provider_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_prompt_template_versions (
            id UUID PRIMARY KEY,
            template_id VARCHAR(128) NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            purpose VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
            system_policy_text TEXT NOT NULL,
            template_data JSONB NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_prompt_template_ver UNIQUE (template_id, version)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_orchestration_runs (
            id UUID PRIMARY KEY,
            run_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL,
            user_id VARCHAR(128) NOT NULL,
            session_id VARCHAR(128) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
            strategy VARCHAR(32) NOT NULL DEFAULT 'SINGLE_MODEL_CALL',
            model_id VARCHAR(128),
            provider_id VARCHAR(64),
            idempotency_key VARCHAR(128),
            run_data JSONB NOT NULL,
            lock_version BIGINT NOT NULL DEFAULT 0,
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_orch_run_id UNIQUE (tenant_id, run_id),
            CONSTRAINT uq_ai_orch_idempotency UNIQUE (tenant_id, user_id, idempotency_key)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_orch_run_tenant_status ON ai_orchestration_runs(tenant_id, status);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_orch_run_user ON ai_orchestration_runs(tenant_id, user_id, created_at);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_orchestration_steps (
            id UUID PRIMARY KEY,
            run_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL,
            step_sequence INTEGER NOT NULL,
            state_from VARCHAR(32) NOT NULL,
            state_to VARCHAR(32) NOT NULL,
            transition_reason TEXT NOT NULL,
            duration_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_orch_step_seq UNIQUE (tenant_id, run_id, step_sequence)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_model_invocations (
            id UUID PRIMARY KEY,
            invocation_id VARCHAR(128) NOT NULL,
            run_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL,
            model_id VARCHAR(128) NOT NULL,
            provider_id VARCHAR(64) NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            duration_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_model_inv_id UNIQUE (tenant_id, invocation_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_orchestration_tool_calls (
            id UUID PRIMARY KEY,
            tool_call_id VARCHAR(128) NOT NULL,
            run_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL,
            sequence INTEGER NOT NULL,
            tool_id VARCHAR(128) NOT NULL,
            tool_version VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
            args_checksum VARCHAR(64) NOT NULL,
            result_checksum VARCHAR(64) NOT NULL,
            duration_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_orch_tool_seq UNIQUE (tenant_id, run_id, sequence)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_orchestration_usage_records (
            id UUID PRIMARY KEY,
            record_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL,
            user_id VARCHAR(128) NOT NULL,
            run_id VARCHAR(128) NOT NULL,
            model_id VARCHAR(128) NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            cost_estimate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_orch_usage_id UNIQUE (tenant_id, record_id)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_orch_usage_tenant ON ai_orchestration_usage_records(tenant_id, created_at);
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_orchestration_evaluation_cases (
            id UUID PRIMARY KEY,
            case_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL DEFAULT 'system',
            title VARCHAR(256) NOT NULL,
            user_query TEXT NOT NULL,
            case_data JSONB NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_orch_eval_case UNIQUE (tenant_id, case_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_orchestration_evaluation_results (
            id UUID PRIMARY KEY,
            evaluation_id VARCHAR(128) NOT NULL,
            case_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL,
            passed BOOLEAN NOT NULL DEFAULT FALSE,
            result_data JSONB NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_orch_eval_res UNIQUE (tenant_id, evaluation_id)
        );
        """,
    ]

    async with get_db_context() as session:
        for stmt in statements:
            await session.execute(text(stmt))
        await session.commit()

    logger.info("Migration v19_0 UP executed successfully.")
    return {"status": "SUCCESS", "migration": "v19_0", "tables_affected": TABLES}


async def run_down() -> Dict[str, Any]:
    """
    Migration v19_0 DOWN — Test-only rollback of AI orchestration tables.
    """
    logger.info("Executing migration v19_0 DOWN...")
    async with get_db_context() as session:
        for table in reversed(TABLES):
            await session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
        await session.commit()

    logger.info("Migration v19_0 DOWN executed successfully.")
    return {"status": "SUCCESS", "migration": "v19_0_down", "tables_dropped": TABLES}
