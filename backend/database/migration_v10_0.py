"""
Migration v10.0 - Enterprise Blueprint Repository
-------------------------------------------------
Adds Enterprise governance, fingerprint, versioning, marketplace and profile
columns to blueprint_repository.

Idempotent and safe to run multiple times.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("migration_v10_0")


ALTER_BLUEPRINT_REPOSITORY = [
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS categoria VARCHAR(100) NOT NULL DEFAULT 'Geral'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS dominio_negocio VARCHAR(100) NOT NULL DEFAULT 'GERAL'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS area VARCHAR(100) NOT NULL DEFAULT 'Geral'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS autor VARCHAR(255) NOT NULL DEFAULT 'IA'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS marketplace_scope VARCHAR(50) NOT NULL DEFAULT 'TENANT'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS is_marketplace BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS fingerprint JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS fingerprint_hash VARCHAR(64) NOT NULL DEFAULT ''",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS identity JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS business_intent JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS semantic_context JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS business_context JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS kpi_strategy JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS visualization_strategy JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS component_strategy JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS filter_strategy JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS grouping_strategy JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS navigation_strategy JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS dashboard_template_reference JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS metadata_info JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS dependencies_map JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS version_info JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS performance_profile JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS quality_profile JSONB NOT NULL DEFAULT '{}'",
    "ALTER TABLE blueprint_repository ADD COLUMN IF NOT EXISTS health_profile JSONB NOT NULL DEFAULT '{}'",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_blueprint_fingerprint_hash ON blueprint_repository (fingerprint_hash)",
    "CREATE INDEX IF NOT EXISTS idx_blueprint_status ON blueprint_repository (status)",
    "CREATE INDEX IF NOT EXISTS idx_blueprint_marketplace ON blueprint_repository (marketplace_scope, is_marketplace)",
    "CREATE INDEX IF NOT EXISTS idx_blueprint_tags ON blueprint_repository USING GIN (tags)",
    "CREATE INDEX IF NOT EXISTS idx_blueprint_identity_version ON blueprint_repository (tenant_id, intent_id, version)",
]

BACKFILL = """
UPDATE blueprint_repository
SET
    categoria = COALESCE(NULLIF(categoria, ''), tipo_analise, 'Geral'),
    dominio_negocio = COALESCE(NULLIF(dominio_negocio, ''), 'GERAL'),
    area = COALESCE(NULLIF(area, ''), 'Geral'),
    tags = CASE WHEN tags = '[]'::jsonb THEN jsonb_build_array('blueprint', lower(visualization_type)) ELSE tags END,
    fingerprint = CASE
        WHEN fingerprint = '{}'::jsonb THEN jsonb_build_object(
            'objetivo', objetivo,
            'tipo_analise', tipo_analise,
            'kpis', metrics,
            'filtros', jsonb_object_keys_safe(filters),
            'agrupamentos', group_by,
            'visualizacao', visualization_type,
            'componentes', COALESCE(layout->'components', '[]'::jsonb),
            'complexidade', CASE
                WHEN jsonb_array_length(COALESCE(group_by, '[]'::jsonb)) > 1 THEN 'ALTA'
                WHEN jsonb_array_length(COALESCE(metrics, '[]'::jsonb)) > 2 THEN 'MEDIA'
                ELSE 'BAIXA'
            END
        )
        ELSE fingerprint
    END,
    identity = CASE
        WHEN identity = '{}'::jsonb THEN jsonb_build_object(
            'uuid', id,
            'nome', nome_consulta,
            'descricao', objetivo,
            'categoria', categoria,
            'dominio_negocio', dominio_negocio,
            'area', area,
            'tags', tags,
            'autor', autor,
            'status', status,
            'versao', version
        )
        ELSE identity
    END,
    business_intent = CASE
        WHEN business_intent = '{}'::jsonb THEN jsonb_build_object(
            'objetivo', objetivo,
            'indicadores', metrics,
            'filtros', filters,
            'agrupamentos', group_by,
            'tipo_analise', tipo_analise
        )
        ELSE business_intent
    END,
    kpi_strategy = CASE WHEN kpi_strategy = '{}'::jsonb THEN jsonb_build_object('kpis', metrics) ELSE kpi_strategy END,
    visualization_strategy = CASE WHEN visualization_strategy = '{}'::jsonb THEN jsonb_build_object('primary_chart_type', visualization_type, 'layout', layout) ELSE visualization_strategy END,
    filter_strategy = CASE WHEN filter_strategy = '{}'::jsonb THEN jsonb_build_object('allowed_filters', jsonb_object_keys_safe(filters)) ELSE filter_strategy END,
    grouping_strategy = CASE WHEN grouping_strategy = '{}'::jsonb THEN jsonb_build_object('group_by', group_by) ELSE grouping_strategy END,
    dependencies_map = CASE WHEN dependencies_map = '{}'::jsonb THEN jsonb_build_object('views', jsonb_build_array(view_name), 'kpis', metrics, 'dependencies', dependencias) ELSE dependencies_map END,
    version_info = CASE WHEN version_info = '{}'::jsonb THEN jsonb_build_object('version', version, 'author', autor, 'reason', 'backfill_migration_v10') ELSE version_info END,
    performance_profile = CASE
        WHEN performance_profile = '{}'::jsonb THEN jsonb_build_object(
            'avg_usage_ms', CASE WHEN quantidade_utilizacoes > 0 THEN tempo_acumulado_ms / quantidade_utilizacoes ELSE 0 END,
            'min_usage_ms', 0,
            'max_usage_ms', tempo_acumulado_ms,
            'reuse_count', quantidade_utilizacoes,
            'tokens_saved', tokens_economizados,
            'render_time_ms', 0
        )
        ELSE performance_profile
    END,
    quality_profile = CASE
        WHEN quality_profile = '{}'::jsonb THEN jsonb_build_object('integrity', 100, 'consistency', 100, 'reuse', 0, 'stability', 100, 'compatibility', 100, 'performance', 100)
        ELSE quality_profile
    END,
    health_profile = CASE
        WHEN health_profile = '{}'::jsonb THEN jsonb_build_object('health_score', 100, 'status', 'healthy', 'warnings', '[]'::jsonb)
        ELSE health_profile
    END
WHERE TRUE
"""

BACKFILL_HASH = """
UPDATE blueprint_repository
SET fingerprint_hash = md5(fingerprint::text)
WHERE fingerprint_hash = ''
"""

CREATE_JSONB_KEYS_FUNCTION = """
CREATE OR REPLACE FUNCTION jsonb_object_keys_safe(payload JSONB)
RETURNS JSONB AS $$
BEGIN
    IF payload IS NULL OR jsonb_typeof(payload) <> 'object' THEN
        RETURN '[]'::jsonb;
    END IF;
    RETURN (
        SELECT COALESCE(jsonb_agg(key), '[]'::jsonb)
        FROM jsonb_object_keys(payload) AS key
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""


async def run_migration() -> None:
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    logger.info("Connecting to database: %s", dsn.split("@")[-1])
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(CREATE_JSONB_KEYS_FUNCTION)
        for stmt in ALTER_BLUEPRINT_REPOSITORY:
            await conn.execute(stmt)
        for idx in INDEXES:
            await conn.execute(idx)
        await conn.execute(BACKFILL)
        await conn.execute(BACKFILL_HASH)
        logger.info("Migration v10.0 completed successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
