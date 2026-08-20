"""
Migration v8.0 — Metadata Catalog Corporativo
----------------------------------------------
Evolui o metadata_catalog para centro de governança da Data Platform.
Adiciona ~20 novas colunas e cria a tabela metadata_catalog_versions.

Execução idempotente — seguro para rodar múltiplas vezes.
"""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("migration_v8_0")

# ── Novos campos da tabela metadata_catalog ────────────────────────────────

ALTER_METADATA_CATALOG = [
    # Classificação e governança
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS tipo_estrutura VARCHAR(50) NOT NULL DEFAULT 'VIEW'",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS owner VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS categoria VARCHAR(100) NOT NULL DEFAULT 'Geral'",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS estrutura_id VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS blueprint_associado VARCHAR(255)",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS dashboard_associado VARCHAR(255)",
    # Health Monitor scores
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS health_score NUMERIC(5,2) NOT NULL DEFAULT 100.0",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS integrity_score NUMERIC(5,2) NOT NULL DEFAULT 100.0",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS performance_score NUMERIC(5,2) NOT NULL DEFAULT 100.0",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS freshness_score NUMERIC(5,2) NOT NULL DEFAULT 100.0",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS usage_score NUMERIC(5,2) NOT NULL DEFAULT 0.0",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS alertas JSONB NOT NULL DEFAULT '[]'",
    # Cache metadata
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS cache_ativo BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS cache_atualizado_em TIMESTAMPTZ",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS cache_ttl_segundos INTEGER NOT NULL DEFAULT 3600",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS cache_hit_rate NUMERIC(5,2) NOT NULL DEFAULT 0.0",
    # Data Lineage e Dependency Graph
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS lineage JSONB NOT NULL DEFAULT '[]'",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS dependencias_grafo JSONB NOT NULL DEFAULT '{}'",
    # Métricas de uso
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS quantidade_usuarios INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS ultima_utilizacao TIMESTAMPTZ",
    # Dados de sincronização extendidos
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS duracao_ultima_sync_ms NUMERIC(10,2) NOT NULL DEFAULT 0.0",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS registros_ultima_sync INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE metadata_catalog ADD COLUMN IF NOT EXISTS erros_sync JSONB NOT NULL DEFAULT '[]'",
]

# ── Índices novos ─────────────────────────────────────────────────────────

NEW_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_metadata_tipo_estrutura ON metadata_catalog (tipo_estrutura)",
    "CREATE INDEX IF NOT EXISTS idx_metadata_estrutura_id ON metadata_catalog (estrutura_id)",
    "CREATE INDEX IF NOT EXISTS idx_metadata_tags ON metadata_catalog USING GIN (tags)",
    "CREATE INDEX IF NOT EXISTS idx_metadata_lineage ON metadata_catalog USING GIN (lineage)",
    "CREATE INDEX IF NOT EXISTS idx_metadata_health_score ON metadata_catalog (health_score)",
]

# ── Nova tabela: metadata_catalog_versions ─────────────────────────────────

CREATE_VERSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS metadata_catalog_versions (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id       UUID            NOT NULL,
    metadata_id     UUID            NOT NULL,
    versao          INTEGER         NOT NULL,
    snapshot        JSONB           NOT NULL DEFAULT '{}',
    autor           VARCHAR(255),
    motivo          TEXT,
    criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_metadata_catalog_versions     PRIMARY KEY (id),
    CONSTRAINT fk_mcv_tenant                    FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_mcv_metadata                  FOREIGN KEY (metadata_id) REFERENCES metadata_catalog (id) ON DELETE CASCADE
)
"""

CREATE_VERSIONS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_mcv_tenant_id ON metadata_catalog_versions (tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mcv_metadata_id ON metadata_catalog_versions (metadata_id)",
    "CREATE INDEX IF NOT EXISTS idx_mcv_versao ON metadata_catalog_versions (metadata_id, versao)",
]

# ── Trigger para versões (imutável — sem UPDATE trigger) ──────────────────

BACKFILL_ESTRUTURA_ID = """
UPDATE metadata_catalog
SET estrutura_id = nome_view
WHERE estrutura_id = ''
"""


async def run_migration():
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    logger.info("Conectando ao banco: %s", dsn.split("@")[-1])
    conn = await asyncpg.connect(dsn)

    try:
        logger.info("── ALTER TABLE metadata_catalog ──────────────────────────")
        for stmt in ALTER_METADATA_CATALOG:
            col = stmt.split("ADD COLUMN IF NOT EXISTS")[1].split()[0]
            logger.info("  Adicionando coluna: %s", col)
            await conn.execute(stmt)

        logger.info("── Criando índices novos ─────────────────────────────────")
        for idx in NEW_INDEXES:
            await conn.execute(idx)

        logger.info("── Criando tabela metadata_catalog_versions ──────────────")
        await conn.execute(CREATE_VERSIONS_TABLE)
        for idx in CREATE_VERSIONS_INDEXES:
            await conn.execute(idx)

        logger.info("── Backfill: estrutura_id = nome_view ────────────────────")
        result = await conn.execute(BACKFILL_ESTRUTURA_ID)
        logger.info("  Linhas atualizadas: %s", result.split()[-1] if result else 0)

        logger.info("✅ Migration v8.0 executada com sucesso!")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
