"""
Migration v9.0 — Sync Queue Table
----------------------------------
Cria a tabela sync_queue para gerenciar a fila e histórico de sincronizações do Sync Engine.

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
logger = logging.getLogger("migration_v9_0")

CREATE_SYNC_QUEUE_TABLE = """
CREATE TABLE IF NOT EXISTS sync_queue (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id           UUID            NOT NULL,
    data_execucao       DATE            NOT NULL DEFAULT CURRENT_DATE,
    hora_execucao       TIME            NOT NULL DEFAULT CURRENT_TIME,
    status              VARCHAR(100)    NOT NULL DEFAULT 'PENDING',
    tempo_duracao_ms    NUMERIC(10, 2)  NOT NULL DEFAULT 0.0,
    quantidade_views    INTEGER         NOT NULL DEFAULT 0,
    quantidade_registros INTEGER        NOT NULL DEFAULT 0,
    resultado           TEXT,
    erros               JSONB           NOT NULL DEFAULT '[]',
    avisos              JSONB           NOT NULL DEFAULT '[]',
    criado_em           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_sync_queue PRIMARY KEY (id),
    CONSTRAINT fk_sync_queue_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sync_queue_tenant_id ON sync_queue (tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue (status)",
    "CREATE INDEX IF NOT EXISTS idx_sync_queue_criado_em ON sync_queue (criado_em DESC)"
]

async def run_migration():
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    logger.info("Conectando ao banco: %s", dsn.split("@")[-1])
    conn = await asyncpg.connect(dsn)

    try:
        logger.info("── Criando tabela sync_queue ─────────────────────────────────")
        await conn.execute(CREATE_SYNC_QUEUE_TABLE)
        
        logger.info("── Criando índices ──────────────────────────────────────────")
        for idx in CREATE_INDEXES:
            await conn.execute(idx)

        logger.info("✅ Migration v9.0 executada com sucesso!")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
