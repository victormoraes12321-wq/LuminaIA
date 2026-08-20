from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy import text
from database import get_db_context

logger = logging.getLogger("luminaai.database.migration_v18_0")

TABLES = [
    "analytical_catalog_definitions",
    "analytical_catalog_snapshots",
    "analytical_dataset_definitions",
    "analytical_execution_records",
]


async def run_up() -> Dict[str, Any]:
    """
    Migration v18_0 — Safe Analytical PostgreSQL Access Layer.
    Idempotent creation of analytical catalog tables, constraints, and indexes.
    """
    logger.info("Executing migration v18_0 UP...")

    statements = [
        """
        CREATE TABLE IF NOT EXISTS analytical_catalog_definitions (
            id UUID PRIMARY KEY,
            catalog_id VARCHAR(128) NOT NULL,
            description TEXT NOT NULL DEFAULT 'Governed Analytical Catalog',
            tenant_id VARCHAR(128) NOT NULL DEFAULT 'system',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_analytical_catalog_def_tenant UNIQUE (id, tenant_id),
            CONSTRAINT uq_analytical_catalog_id UNIQUE (tenant_id, catalog_id)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_analytical_catalog_tenant ON analytical_catalog_definitions(tenant_id, is_active);
        """,
        """
        CREATE TABLE IF NOT EXISTS analytical_catalog_snapshots (
            id UUID PRIMARY KEY,
            snapshot_id VARCHAR(128) NOT NULL,
            catalog_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
            lifecycle VARCHAR(32) NOT NULL DEFAULT 'PUBLISHED',
            snapshot_data JSONB NOT NULL,
            tenant_id VARCHAR(128) NOT NULL DEFAULT 'system',
            published_by VARCHAR(128) NOT NULL DEFAULT 'system',
            checksum VARCHAR(64) NOT NULL,
            published_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_analytical_catalog_snap_tenant UNIQUE (id, tenant_id),
            CONSTRAINT uq_analytical_catalog_snap_id UNIQUE (tenant_id, snapshot_id),
            CONSTRAINT ck_analytical_catalog_lifecycle CHECK (lifecycle IN ('DRAFT','VALIDATING','READY','PUBLISHED','DEPRECATED','DISABLED','ARCHIVED'))
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_analytical_catalog_snap_lifecycle ON analytical_catalog_snapshots(tenant_id, lifecycle);
        """,
        """
        CREATE TABLE IF NOT EXISTS analytical_dataset_definitions (
            id UUID PRIMARY KEY,
            canonical_dataset_id VARCHAR(128) NOT NULL,
            domain VARCHAR(64) NOT NULL DEFAULT 'sales',
            tenant_strategy VARCHAR(32) NOT NULL DEFAULT 'TENANT_COLUMN_REQUIRED',
            tenant_id VARCHAR(128) NOT NULL DEFAULT 'system',
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_analytical_dataset_tenant UNIQUE (id, tenant_id),
            CONSTRAINT uq_analytical_dataset_canonical UNIQUE (tenant_id, canonical_dataset_id),
            CONSTRAINT ck_analytical_dataset_tenant_strat CHECK (tenant_strategy IN ('TENANT_COLUMN_REQUIRED','DEDICATED_TENANT_DATABASE','CERTIFIED_ROW_LEVEL_SECURITY','CERTIFIED_TENANT_VIEW','SYSTEM_GLOBAL_METADATA','BLOCKED'))
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS analytical_execution_records (
            id UUID PRIMARY KEY,
            execution_id VARCHAR(128) NOT NULL,
            query_fingerprint VARCHAR(64) NOT NULL,
            dataset_id VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(128) NOT NULL,
            user_id VARCHAR(128) NOT NULL,
            row_count INTEGER NOT NULL DEFAULT 0,
            truncated BOOLEAN NOT NULL DEFAULT FALSE,
            execution_time_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_analytical_exec_tenant_time ON analytical_execution_records(tenant_id, created_at);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_analytical_exec_fingerprint ON analytical_execution_records(query_fingerprint);
        """,
    ]

    async with get_db_context() as session:
        for stmt in statements:
            await session.execute(text(stmt))
        await session.commit()

    logger.info("Migration v18_0 UP executed successfully.")
    return {"status": "SUCCESS", "migration": "v18_0", "tables_affected": TABLES}


async def run_down() -> Dict[str, Any]:
    """
    Migration v18_0 DOWN — Test-only rollback of safe analytical PostgreSQL tables.
    """
    logger.info("Executing migration v18_0 DOWN...")
    async with get_db_context() as session:
        for table in reversed(TABLES):
            await session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
        await session.commit()

    logger.info("Migration v18_0 DOWN executed successfully.")
    return {"status": "SUCCESS", "migration": "v18_0_down", "tables_dropped": TABLES}
