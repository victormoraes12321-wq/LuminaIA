"""LuminaAI V2 RC4 — Script Canônico de Bootstrap para Staging / Pré-Produção Windows.

Este script executa o provisionamento oficial de um banco de dados novo ou
existente em ambiente de pré-produção/staging:
1. Valida rigorosamente as travas de ambiente (proíbe produção, aceita apenas staging).
2. Valida o target do banco (DATABASE_URL deve apontar para lumina_preprod).
3. Cria a estrutura base do schema inicial via SQLAlchemy metadata.
4. Executa ordenadamente a cadeia de migrações canônicas (v4_1 até v26_0).
5. Registra o histórico de migrações na tabela lumina_schema_migrations.
6. Realiza a verificação final de tabelas, índices e ausência de v27.
7. Garante execução 100% idempotente.
"""
from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Adiciona o diretório backend ao sys.path e carrega .env
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("luminaai.bootstrap_preprod")


# Baseline moderno para Fresh Install:
# As 22 tabelas core iniciais representam 100% do schema acumulado até a versão 6.0
# (v1.0 Baseline + v4.1 colunas tenants + v5.0 Data Platform + v6.0 Business Knowledge Engine).
FRESH_BASELINE_VERSION: str = "6.0"

# Cadeia completa histórica de migrações (para auditoria, upgrade e compatibilidade)
HISTORICAL_MIGRATION_CHAIN: list[str] = [
    "migration_v4_1",
    "migration_v5_0",
    "migration_v6_0",
    "migration_v7_0",
    "migration_v8_0",
    "migration_v9_0",
    "migration_v10_0",
    "migration_v11_0",
    "migration_v12_0",
    "migration_v13_0",
    "migration_v14_0",
    "migration_v15_0",
    "migration_v16_0",
    "migration_v17_0",
    "migration_v18_0",
    "migration_v19_0",
    "migration_v20_0",
    "migration_v21_0",
    "migration_v22_0",
    "migration_v23_0",
    "migration_v24_0",
    "migration_v25_0",
    "migration_v26_0",
]

# Cadeia incremental para Fresh Install (v7_0 a v26_0):
# Executada imediatamente após o provisionamento da baseline 6.0 e pré-requisitos SQL.
FRESH_MIGRATION_CHAIN: list[str] = [
    "migration_v7_0",
    "migration_v8_0",
    "migration_v9_0",
    "migration_v10_0",
    "migration_v11_0",
    "migration_v12_0",
    "migration_v13_0",
    "migration_v14_0",
    "migration_v15_0",
    "migration_v16_0",
    "migration_v17_0",
    "migration_v18_0",
    "migration_v19_0",
    "migration_v20_0",
    "migration_v21_0",
    "migration_v22_0",
    "migration_v23_0",
    "migration_v24_0",
    "migration_v25_0",
    "migration_v26_0",
]

# Mapeamento canônico explícito dos entrypoints por migração
MIGRATION_ENTRYPOINT_MAP: dict[str, str] = {
    "migration_v4_1": "main",
    "migration_v5_0": "main",
    "migration_v6_0": "main",
    "migration_v7_0": "run_migration",
    "migration_v8_0": "run_migration",
    "migration_v9_0": "run_migration",
    "migration_v10_0": "run_migration",
    "migration_v11_0": "run_migration",
    "migration_v12_0": "run_up",
    "migration_v13_0": "run_up",
    "migration_v14_0": "run_up",
    "migration_v15_0": "run_up",
    "migration_v16_0": "run_up",
    "migration_v17_0": "run_up",
    "migration_v18_0": "run_up",
    "migration_v19_0": "run_up",
    "migration_v20_0": "run_up",
    "migration_v21_0": "run_up",
    "migration_v22_0": "run_up",
    "migration_v23_0": "run_up",
    "migration_v24_0": "run_up",
    "migration_v25_0": "run_up",
    "migration_v26_0": "run_up",
}


def _enforce_staging_guard():
    """Valida que o ambiente é estritamente staging e nunca produção."""
    from config import settings

    env = (settings.ENVIRONMENT or "").strip().lower()
    if env == "production":
        raise RuntimeError("FATAL: O bootstrap automático é estritamente proibido em ENVIRONMENT=production!")
    if env != "staging":
        raise RuntimeError(f"FATAL: O bootstrap de pré-produção exige ENVIRONMENT=staging (atual: '{env}')")

    db_url = settings.DATABASE_URL
    if not db_url:
        raise RuntimeError("FATAL: DATABASE_URL não configurada no backend/.env")

    # Garante sinalização de bootstrap para o database_guard
    os.environ["LUMINA_STAGING_BOOTSTRAP"] = "true"
    os.environ["LUMINA_MIGRATION_MODE"] = "staging_bootstrap"

    logger.info("🔒 Guard de Staging aprovado (Ambiente: %s | Target: %s)", env.upper(), settings.DATABASE_URL.split("@")[-1])


def _load_migration_module(migration_name: str) -> Any:
    """Carrega dinamicamente o módulo de migração."""
    file_path = BACKEND_DIR / "database" / f"{migration_name}.py"
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo de migração não encontrado: {file_path}")

    spec = importlib.util.spec_from_file_location(f"lumina_migration_{migration_name}", file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Falha ao carregar spec para {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_migration_entrypoint(mod: Any, migration_name: str) -> tuple[Any, str]:
    """Resolve determinística e rigidamente o entrypoint canônico de cada migração (fail-closed)."""
    expected = MIGRATION_ENTRYPOINT_MAP.get(migration_name)
    if expected and hasattr(mod, expected):
        func = getattr(mod, expected)
        if callable(func):
            return func, expected

    # Fallback estrito para entrypoints canônicos conhecidos
    for candidate in ("run_up", "run_migration", "main", "execute_migration"):
        if hasattr(mod, candidate):
            func = getattr(mod, candidate)
            if callable(func):
                return func, candidate

    raise AttributeError(
        f"Módulo {migration_name} não possui entrypoint de migração reconhecido "
        f"(esperado um de: run_up, run_migration, main, execute_migration)"
    )


# ==============================================================================
# Pré-requisito SQL canônico: extraído textualmente de backend/database/init.sql (linhas 38-44)
# ==============================================================================
CANONICAL_FN_UPDATE_ATUALIZADO_EM = """
CREATE OR REPLACE FUNCTION fn_update_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


async def _ensure_sql_prerequisites(engine: Any) -> None:
    """Aplica pré-requisitos SQL nativos canônicos (funções e extensões) antes das migrações."""
    from sqlalchemy import text

    logger.info("🔧 Aplicando pré-requisitos SQL canônicos (funções e extensões)...")
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto";'))
        await conn.execute(text(CANONICAL_FN_UPDATE_ATUALIZADO_EM))
    logger.info("✅ Pré-requisitos SQL aplicados com sucesso (fn_update_atualizado_em presente).")


# ==============================================================================
# Tabelas canônicas do Schema Inicial Core (Baseline pré-v7)
# As demais 102 tabelas pertencem estritamente às migrações v7_0 a v26_0.
# ==============================================================================
CORE_INITIAL_SCHEMA_TABLES: frozenset[str] = frozenset({
    "analytical_packages",
    "blueprint_repository",
    "business_concepts",
    "business_formulas",
    "business_governance_logs",
    "business_kpis",
    "business_relationships",
    "dashboard_preferences",
    "data_platform_history",
    "datasets",
    "favorites",
    "metadata_catalog",
    "package_dashboard_instances",
    "search_history",
    "semantic_memory",
    "svr_audit_logs",
    "svr_compatibility_matrix",
    "svr_concepts",
    "svr_versions",
    "tenants",
    "users",
    "view_catalog",
})


async def _run_initial_schema(engine: Any) -> None:
    """Aplica o schema inicial SQLAlchemy restrito às 22 tabelas core da baseline (pré-v7)."""
    from database import Base
    import models  # Registra todos os modelos

    logger.info("📦 Criando tabelas base do schema inicial (Core Baseline pré-v7)...")
    startup_tables = [
        table for table in Base.metadata.tables.values()
        if table.name in CORE_INITIAL_SCHEMA_TABLES
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=startup_tables))
    logger.info("✅ Tabelas base inicializadas com sucesso (%d tabelas core).", len(startup_tables))


# ==============================================================================
# Migrações Operacionais Governamentais v21_0 a v26_0
# Executadas via Operational Staging Executor para isolar do wrapper test-only.
# ==============================================================================
OPERATIONAL_STAGING_MIGRATIONS: frozenset[str] = frozenset({
    "migration_v21_0",
    "migration_v22_0",
    "migration_v23_0",
    "migration_v24_0",
    "migration_v25_0",
    "migration_v26_0",
})


async def _enforce_operational_staging_guard(engine: Any) -> None:
    """Valida estritamente a conexão e o ambiente operacional de staging antes de qualquer escrita."""
    from config import settings
    from sqlalchemy import text
    import ipaddress

    env = (settings.ENVIRONMENT or "").strip().lower()
    if env != "staging":
        raise RuntimeError(f"STAGING_OPERATIONAL_GUARD_FAILED: ENVIRONMENT deve ser 'staging' (atual: '{env}')")

    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT
                    current_database() AS db_name,
                    current_user AS db_user,
                    COALESCE(host(inet_server_addr()), '127.0.0.1') AS srv_addr,
                    inet_server_port() AS srv_port
            """)
        )
        row = result.mappings().one()
        db_name = str(row["db_name"]).strip().lower()
        db_user = str(row["db_user"]).strip().lower()
        srv_addr = str(row["srv_addr"]).strip().lower()
        srv_port = int(row["srv_port"] or 5432)

        forbidden_dbs = {"postgres", "template0", "template1", "luminaai", "lumina", "agrodesk_ti", "luminaai_db"}
        if db_name in forbidden_dbs:
            raise RuntimeError(f"STAGING_OPERATIONAL_GUARD_FAILED: Database '{db_name}' é protegido/proibido!")

        if db_name != "lumina_preprod":
            raise RuntimeError(f"STAGING_OPERATIONAL_GUARD_FAILED: Database deve ser 'lumina_preprod' (conectado: '{db_name}')")

        if db_user != "lumina_preprod_user":
            raise RuntimeError(f"STAGING_OPERATIONAL_GUARD_FAILED: Usuário deve ser 'lumina_preprod_user' (conectado: '{db_user}')")

        try:
            addr = ipaddress.ip_address(srv_addr.split("%", 1)[0])
            if not (addr.is_loopback or addr.is_private):
                raise RuntimeError(f"STAGING_OPERATIONAL_GUARD_FAILED: Servidor PostgreSQL ({srv_addr}) não é local/privado!")
        except ValueError as exc:
            raise RuntimeError(f"STAGING_OPERATIONAL_GUARD_FAILED: Endereço inválido: {srv_addr}") from exc


async def _execute_operational_staging_migration(engine: Any, migration_name: str) -> dict[str, Any]:
    """Executa de forma segura e determinística o payload DDL canônico das migrações v21 a v26 em staging."""
    from sqlalchemy import text

    await _enforce_operational_staging_guard(engine)

    mod = _load_migration_module(migration_name)
    mig_id = getattr(mod, "MIGRATION_NAME", migration_name)
    tables = getattr(mod, "TABLES", [])

    if migration_name == "migration_v21_0":
        up_statements = getattr(mod, "UP_STATEMENTS", None)
        if not up_statements:
            raise RuntimeError("migration_v21_0 não possui UP_STATEMENTS")
        async with engine.begin() as conn:
            for statement in up_statements:
                await conn.execute(text(statement))

    elif migration_name in {
        "migration_v22_0", "migration_v23_0", "migration_v24_0",
        "migration_v25_0", "migration_v26_0"
    }:
        model_tables = getattr(mod, "MODEL_TABLES", None)
        immutability_statements = getattr(mod, "IMMUTABILITY_STATEMENTS", None)

        if not model_tables:
            raise RuntimeError(f"{migration_name} não possui MODEL_TABLES")

        async with engine.begin() as conn:
            for table in model_tables:
                await conn.run_sync(lambda sync_conn, target=table: target.create(sync_conn, checkfirst=True))
            if immutability_statements:
                for statement in immutability_statements:
                    await conn.execute(text(statement))
    else:
        raise ValueError(f"Migração {migration_name} não é uma migração operacional v21-v26 reconhecida")

    return {
        "status": "SUCCESS",
        "migration": mig_id,
        "tables_affected": tables,
    }


async def _run_migration_chain(engine: Any, migration_chain: list[str] | None = None) -> list[str]:
    """Executa a cadeia sequencial incremental de migrações (v7_0 a v26_0) de forma determinística."""
    chain = migration_chain if migration_chain is not None else FRESH_MIGRATION_CHAIN
    applied = []
    for migration_name in chain:
        logger.info("⚡ Executando migração: %s...", migration_name)

        if migration_name in OPERATIONAL_STAGING_MIGRATIONS:
            res = await _execute_operational_staging_migration(engine, migration_name)
            entrypoint_name = "OPERATIONAL_STAGING_EXECUTOR"
        else:
            mod = _load_migration_module(migration_name)
            entrypoint_fn, entrypoint_name = resolve_migration_entrypoint(mod, migration_name)
            res = await entrypoint_fn()

        status = res.get("status", "SUCCESS") if isinstance(res, dict) else "SUCCESS"
        logger.info("   -> %s concluída via %s() [status=%s]", migration_name, entrypoint_name, status)

        applied.append(migration_name)

    return applied


async def _verify_final_schema(engine: Any) -> dict[str, Any]:
    """Verifica tabelas chave, funções, triggers e ausência de v27."""
    from sqlalchemy import text

    critical_tables = [
        "users",
        "tenants",
        "blueprint_repository",
        "conversation_sessions",
        "conversation_nodes",
        "enterprise_knowledge_assets",
        "user_analytical_profiles",
        "governed_feedback_records",
        "semantic_index_definitions",
        "smart_cache_policies",
        "materialization_definitions",
        "dashboards_v2",
        "dashboard_revisions_v2",
        "dashboard_ai_proposals_v2",
        "post_sync_insights_v2",
        "observability_slo_definitions_v2",
        "governed_work_queue_jobs_v2",
        "lumina_schema_migrations",
    ]

    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        ))
        existing_tables = {row[0] for row in result.fetchall()}

        missing = [t for t in critical_tables if t not in existing_tables]
        if missing:
            raise RuntimeError(f"Verificação de schema falhou! Tabelas ausentes: {missing}")

        # Verifica que v27 não existe
        v27_tables = [t for t in existing_tables if "v27" in t]
        if v27_tables:
            raise RuntimeError(f"Tabelas de versão v27 encontradas indevidamente: {v27_tables}")

        # Verifica pré-requisito fn_update_atualizado_em
        fn_res = await conn.execute(text("SELECT 1 FROM pg_proc WHERE proname = 'fn_update_atualizado_em'"))
        if not fn_res.scalar():
            raise RuntimeError("Função SQL canônica fn_update_atualizado_em() não encontrada no pg_proc!")

        # Verifica trigger trg_semantic_atualizado_em
        trg_res = await conn.execute(text("SELECT 1 FROM pg_trigger WHERE tgname = 'trg_semantic_atualizado_em'"))
        if not trg_res.scalar():
            raise RuntimeError("Trigger trg_semantic_atualizado_em não encontrada no pg_trigger!")

    return {
        "status": "VERIFIED",
        "total_tables": len(existing_tables),
        "critical_tables_verified": len(critical_tables),
        "v26_tables_verified": True,
        "v27_absent": True,
        "fn_update_atualizado_em": True,
        "trg_semantic_atualizado_em": True,
    }


# ==============================================================================
# Tenant e Admin Canônicos (init.sql baseline)
# ==============================================================================
CANONICAL_TENANT_ID: str = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
CANONICAL_TENANT_NOME: str = "Empresa Demonstração"


async def _ensure_canonical_tenant(engine: Any) -> None:
    """Garante a existência do tenant canônico (a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11) de forma estrita e idempotente."""
    from sqlalchemy import text

    logger.info("🏢 Garantindo tenant canônico (%s)...", CANONICAL_TENANT_ID)
    async with engine.begin() as conn:
        await conn.execute(
            text("""
                INSERT INTO tenants (
                    id, nome, logo_url, tema_config, ia_config,
                    oracle_conn, clone_db_conn, sync_config, ativo,
                    criado_em, atualizado_em
                ) VALUES (
                    :tenant_id, :nome, NULL,
                    '{"theme": "dark", "primary_color": "#6366f1"}'::jsonb,
                    '{"model": "gpt-4o-mini", "temperature": 0.2}'::jsonb,
                    '{}'::jsonb, '{}'::jsonb,
                    '{"enabled": false, "times": []}'::jsonb,
                    TRUE, NOW(), NOW()
                ) ON CONFLICT (id) DO UPDATE SET
                    nome = EXCLUDED.nome,
                    ativo = TRUE,
                    atualizado_em = NOW();
            """),
            {
                "tenant_id": CANONICAL_TENANT_ID,
                "nome": CANONICAL_TENANT_NOME,
            },
        )
    logger.info("✅ Tenant canônico '%s' (%s) verificado/garantido com sucesso.", CANONICAL_TENANT_NOME, CANONICAL_TENANT_ID)


async def _seed_initial_admin_if_configured(engine: Any) -> None:
    """Cria o usuário administrador inicial de forma segura se configurado via .env."""
    from sqlalchemy import text
    import uuid
    from services.auth_service import get_password_hash

    admin_email = os.environ.get("INITIAL_ADMIN_EMAIL") or os.environ.get("LUMINA_ADMIN_EMAIL") or "admin@lumina.ai"
    admin_password = os.environ.get("INITIAL_ADMIN_PASSWORD") or os.environ.get("LUMINA_ADMIN_PASSWORD")

    if not admin_password:
        logger.info("ℹ️ Nenhum INITIAL_ADMIN_PASSWORD configurado no .env. Criação de usuário admin omitida.")
        return

    hashed_pwd = get_password_hash(admin_password)

    async with engine.begin() as conn:
        # Verifica se admin já existe
        user_res = await conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": admin_email},
        )
        if user_res.fetchone():
            logger.info("ℹ️ Usuário admin '%s' já existe. Mantendo existente.", admin_email)
        else:
            user_id = str(uuid.uuid4())
            await conn.execute(
                text("""
                    INSERT INTO users (
                        id, tenant_id, nome, email, password_hash, role, ativo, must_change_password, criado_em, atualizado_em
                    ) VALUES (
                        :id, :tenant_id, 'Administrador do Sistema', :email, :password, 'ADMIN', true, false, NOW(), NOW()
                    )
                """),
                {
                    "id": user_id,
                    "tenant_id": CANONICAL_TENANT_ID,
                    "email": admin_email,
                    "password": hashed_pwd,
                },
            )
            logger.info("👤 Usuário administrador '%s' criado com sucesso com privilégio ADMIN.", admin_email)


async def bootstrap_staging() -> dict[str, Any]:
    """Orquestrador principal de fresh bootstrap."""
    logger.info("=" * 70)
    logger.info("🚀 LUMINA AI V2 RC4 — BOOTSTRAP DE BANCO DE DADOS (STAGING)")
    logger.info("=" * 70)

    _enforce_staging_guard()

    from database import engine

    # 1. Schema inicial baseline 6.0 (22 tabelas core)
    await _run_initial_schema(engine)

    # 2. Pré-requisitos SQL canônicos (pgcrypto, fn_update_atualizado_em)
    await _ensure_sql_prerequisites(engine)

    # 3. Provisionamento do Tenant Canônico (necessário para v7_0+)
    await _ensure_canonical_tenant(engine)

    # 4. Cadeia incremental de migrações (v7_0 a v26_0)
    applied_migrations = await _run_migration_chain(engine)

    # 5. Seed opcional de admin inicial se configurado
    await _seed_initial_admin_if_configured(engine)

    # 6. Verificação final estrita de schema
    verification = await _verify_final_schema(engine)

    logger.info("=" * 70)
    logger.info("✅ BOOTSTRAP DE STAGING CONCLUÍDO COM 100%% DE SUCESSO!")
    logger.info("   Baseline versão           : %s", FRESH_BASELINE_VERSION)
    logger.info("   Total de tabelas no banco : %d", verification["total_tables"])
    logger.info("   Migrações aplicadas       : %d (%s -> %s)", len(applied_migrations), applied_migrations[0], applied_migrations[-1])
    logger.info("   v26 verificado            : %s", verification["v26_tables_verified"])
    logger.info("   v27 ausente               : %s", verification["v27_absent"])
    logger.info("=" * 70)

    await engine.dispose()
    return {
        "status": "SUCCESS",
        "applied_migrations": applied_migrations,
        "verification": verification,
    }


def main():
    try:
        asyncio.run(bootstrap_staging())
    except Exception as exc:
        logger.critical("❌ FALHA NO BOOTSTRAP DE STAGING: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
