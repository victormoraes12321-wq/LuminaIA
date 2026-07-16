"""
Migration v11.0 - Enterprise Dashboard Studio
---------------------------------------------
Creates visual-only Dashboard Template, Dashboard Instance and version history
tables. This keeps dashboard customization separate from analytical logic.
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
logger = logging.getLogger("migration_v11_0")


BOOTSTRAP_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION fn_update_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


CREATE_DASHBOARD_TEMPLATES = """
CREATE TABLE IF NOT EXISTS dashboard_templates (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    blueprint_id            UUID,
    analytical_package_id   UUID,
    name                    VARCHAR(255)    NOT NULL,
    description             TEXT,
    category                VARCHAR(100)    NOT NULL DEFAULT 'CUSTOM',
    status                  VARCHAR(50)     NOT NULL DEFAULT 'ACTIVE',
    version                 INTEGER         NOT NULL DEFAULT 1,
    layout                  JSONB           NOT NULL DEFAULT '{}',
    grid                    JSONB           NOT NULL DEFAULT '{}',
    components              JSONB           NOT NULL DEFAULT '[]',
    component_order         JSONB           NOT NULL DEFAULT '[]',
    groups                  JSONB           NOT NULL DEFAULT '[]',
    tabs                    JSONB           NOT NULL DEFAULT '[]',
    sections                JSONB           NOT NULL DEFAULT '[]',
    responsive              JSONB           NOT NULL DEFAULT '{}',
    theme                   JSONB           NOT NULL DEFAULT '{}',
    visual_config           JSONB           NOT NULL DEFAULT '{}',
    default_state           JSONB           NOT NULL DEFAULT '{}',
    available_components    JSONB           NOT NULL DEFAULT '[]',
    permissions             JSONB           NOT NULL DEFAULT '{}',
    created_by              UUID,
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_dashboard_templates PRIMARY KEY (id),
    CONSTRAINT fk_dashboard_templates_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_dashboard_templates_created_by FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
);
"""


CREATE_DASHBOARD_INSTANCES = """
CREATE TABLE IF NOT EXISTS dashboard_instances (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    template_id             UUID            NOT NULL,
    user_id                 UUID            NOT NULL,
    name                    VARCHAR(255)    NOT NULL,
    status                  VARCHAR(50)     NOT NULL DEFAULT 'ACTIVE',
    is_favorite             BOOLEAN         NOT NULL DEFAULT FALSE,
    version                 INTEGER         NOT NULL DEFAULT 1,
    current_filters         JSONB           NOT NULL DEFAULT '{}',
    expanded_components     JSONB           NOT NULL DEFAULT '[]',
    panel_positions         JSONB           NOT NULL DEFAULT '{}',
    favorites               JSONB           NOT NULL DEFAULT '[]',
    visible_columns         JSONB           NOT NULL DEFAULT '{}',
    sort_orders             JSONB           NOT NULL DEFAULT '{}',
    preferences             JSONB           NOT NULL DEFAULT '{}',
    current_state           JSONB           NOT NULL DEFAULT '{}',
    layout_override         JSONB           NOT NULL DEFAULT '{}',
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_dashboard_instances PRIMARY KEY (id),
    CONSTRAINT fk_dashboard_instances_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_dashboard_instances_template FOREIGN KEY (template_id) REFERENCES dashboard_templates (id) ON DELETE CASCADE,
    CONSTRAINT fk_dashboard_instances_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
"""


CREATE_DASHBOARD_STUDIO_VERSIONS = """
CREATE TABLE IF NOT EXISTS dashboard_studio_versions (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    template_id             UUID,
    instance_id             UUID,
    target_type             VARCHAR(30)     NOT NULL,
    version                 INTEGER         NOT NULL,
    snapshot                JSONB           NOT NULL DEFAULT '{}',
    author_id               UUID,
    description             TEXT,
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_dashboard_studio_versions PRIMARY KEY (id),
    CONSTRAINT fk_dsv_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_dsv_template FOREIGN KEY (template_id) REFERENCES dashboard_templates (id) ON DELETE CASCADE,
    CONSTRAINT fk_dsv_instance FOREIGN KEY (instance_id) REFERENCES dashboard_instances (id) ON DELETE CASCADE,
    CONSTRAINT fk_dsv_author FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT ck_dashboard_studio_version_single_target CHECK (
        (template_id IS NOT NULL AND instance_id IS NULL)
        OR (template_id IS NULL AND instance_id IS NOT NULL)
    )
);
"""


INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_dashboard_templates_tenant ON dashboard_templates (tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_templates_status ON dashboard_templates (status)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_templates_blueprint ON dashboard_templates (blueprint_id)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_templates_package ON dashboard_templates (analytical_package_id)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_templates_grid_gin ON dashboard_templates USING GIN (grid)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_instances_tenant_user ON dashboard_instances (tenant_id, user_id)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_instances_template ON dashboard_instances (template_id)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_instances_favorite ON dashboard_instances (tenant_id, user_id, is_favorite)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_instances_status ON dashboard_instances (status)",
    "CREATE INDEX IF NOT EXISTS idx_dsv_tenant ON dashboard_studio_versions (tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_dsv_template ON dashboard_studio_versions (template_id)",
    "CREATE INDEX IF NOT EXISTS idx_dsv_instance ON dashboard_studio_versions (instance_id)",
    "CREATE INDEX IF NOT EXISTS idx_dsv_author ON dashboard_studio_versions (author_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_dsv_template_version ON dashboard_studio_versions (template_id, version) WHERE template_id IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_dsv_instance_version ON dashboard_studio_versions (instance_id, version) WHERE instance_id IS NOT NULL",
]


TRIGGERS = [
    "DROP TRIGGER IF EXISTS trg_dashboard_templates_atualizado_em ON dashboard_templates",
    """
    CREATE TRIGGER trg_dashboard_templates_atualizado_em
        BEFORE UPDATE ON dashboard_templates
        FOR EACH ROW
        EXECUTE FUNCTION fn_update_atualizado_em()
    """,
    "DROP TRIGGER IF EXISTS trg_dashboard_instances_atualizado_em ON dashboard_instances",
    """
    CREATE TRIGGER trg_dashboard_instances_atualizado_em
        BEFORE UPDATE ON dashboard_instances
        FOR EACH ROW
        EXECUTE FUNCTION fn_update_atualizado_em()
    """,
]


async def run_migration() -> None:
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    logger.info("Connecting to database: %s", dsn.split("@")[-1])
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(BOOTSTRAP_SQL)
        await conn.execute(CREATE_DASHBOARD_TEMPLATES)
        await conn.execute(CREATE_DASHBOARD_INSTANCES)
        await conn.execute(CREATE_DASHBOARD_STUDIO_VERSIONS)
        for stmt in INDEXES:
            await conn.execute(stmt)
        for stmt in TRIGGERS:
            await conn.execute(stmt)
        logger.info("Migration v11.0 completed successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
