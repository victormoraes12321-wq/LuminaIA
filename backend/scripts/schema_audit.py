import asyncio
import os
import sys
import uuid
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Adiciona o diretório backend ao path para conseguir importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from services.metadata_catalog.repository import catalog_repository
from services.metadata_catalog.loader import load_corporate_catalog
from services.oracle_service import decrypt_connection_details

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("luminaai.audit.schema")

# Tenant de teste padrão (para obter as credenciais do clone Postgres)
DEFAULT_TENANT_ID = "e87f827b-23f2-498c-851f-6a7516d2673a"

async def run_audit():
    print("=" * 80)
    print("INICIANDO AUDITORIA PROFUNDA DE SCHEMAS - POSTGRESQL CLONE")
    print("=" * 80)

    # Inicializa o catálogo corporativo para o script CLI
    try:
        load_corporate_catalog()
    except Exception as e:
        print(f"[!] Erro ao carregar CKC via loader: {e}")

    # 1. Conecta ao banco corporativo principal para ler dados do tenant
    from database import get_db_context
    from models.tenant import Tenant

    clone_db_url = None
    async with get_db_context() as session:
        # Busca o primeiro tenant cadastrado se o default não existir
        tenant = None
        try:
            stmt = text("SELECT id, clone_db_conn FROM tenants LIMIT 1")
            res = await session.execute(stmt)
            row = res.fetchone()
            if row:
                tenant_id = row[0]
                clone_conn = row[1]
                pg_details = decrypt_connection_details(clone_conn)
                clone_db_name = pg_details["database"]
                base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
                clone_db_url = f"{base_url}/{clone_db_name}"
                print(f"[*] Tenant Identificado: {tenant_id}")
                print(f"[*] Banco Clone Alvo: {clone_db_name}")
        except Exception as e:
            print(f"[!] Erro ao ler banco corporativo: {e}")
            sys.exit(1)

    if not clone_db_url:
        print("[!] Nenhum banco clone configurado. Abortando auditoria.")
        sys.exit(1)

    # 2. Cria engine de conexão direta com o Postgres Clone do Tenant
    engine = create_async_engine(clone_db_url, echo=False)
    
    # 3. Inicializa o catálogo do repositório para ler as views mapeadas
    print("[*] Carregando views descritas no Corporate Knowledge Catalog (CKC)...")
    views = list(catalog_repository.catalog.views.keys())
    print(f"[*] {len(views)} views registradas no catálogo local.\n")

    print(f"{'VIEW FISICA':<30} | {'STATUS':<8} | {'VOLUMETRIA':<12} | {'PK':<10} | {'COLS':<6} | {'PREENCHIMENTO METRICA':<30}")
    print("-" * 115)

    passed_count = 0
    failed_count = 0

    for v_name in views:
        v_meta = catalog_repository.get_view(v_name)
        if not v_meta:
            continue

        exists = False
        row_count = 0
        pk_found = False
        columns_count = 0
        metric_status = "N/A"

        try:
            async with engine.connect() as conn:
                # Valida se a view de fato existe no Postgres (case-insensitive)
                stmt_exists = text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE lower(table_name) = :tname)"
                )
                res = await conn.execute(stmt_exists, {"tname": v_name.lower()})
                exists = res.scalar()

                if exists:
                    # Conta registros
                    stmt_count = text(f"SELECT COUNT(*) FROM {v_name}")
                    res_count = await conn.execute(stmt_count)
                    row_count = res_count.scalar()

                    # Valida PK
                    pk_found = bool(v_meta.primary_key)
                    
                    # Conta colunas físicas no banco
                    stmt_cols = text(
                        "SELECT column_name, data_type FROM information_schema.columns WHERE lower(table_name) = :tname"
                    )
                    res_cols = await conn.execute(stmt_cols, {"tname": v_name.lower()})
                    db_cols = {row[0].lower(): row[1] for row in res_cols.fetchall()}
                    columns_count = len(db_cols)

                    # Valida preenchimento das métricas e colunas críticas de negócio
                    metrics_for_v = catalog_repository.get_metrics_for_view(v_name)
                    if metrics_for_v:
                        metric_col = metrics_for_v[0].physical_column.lower()
                        if metric_col in db_cols:
                            # Verifica se possui valores dummy
                            stmt_metric_check = text(
                                f"SELECT COUNT(*), COUNT(CASE WHEN {metric_col} IS NULL THEN 1 END), "
                                f"COUNT(CASE WHEN {metric_col} = 1 THEN 1 END) FROM {v_name}"
                            )
                            res_m = await conn.execute(stmt_metric_check)
                            m_row = res_m.fetchone()
                            
                            total = m_row[0]
                            nulls = m_row[1]
                            ones = m_row[2]

                            if total == 0:
                                metric_status = f"{metric_col}: View Vazia"
                            elif nulls == total:
                                metric_status = f"{metric_col}: 100% NULA (ERRO)"
                            elif ones == total and total > 5:
                                metric_status = f"{metric_col}: 100% DUMMY '1' (ERRO)"
                            else:
                                fill_pct = ((total - nulls) / total) * 100 if total > 0 else 0
                                metric_status = f"{metric_col}: {fill_pct:.1f}% OK"
                        else:
                            metric_status = f"Coluna {metric_col} ausente no banco!"
                    else:
                        metric_status = "Sem metricas associadas"

        except Exception as e:
            exists = False
            metric_status = f"Erro na conexao: {e}"

        status_str = "OK" if exists and row_count > 0 else "FALHA"
        if status_str == "OK":
            passed_count += 1
        else:
            failed_count += 1

        print(f"{v_name:<30} | {status_str:<8} | {row_count:<12} | {('SIM' if pk_found else 'NAO'):<10} | {columns_count:<6} | {metric_status:<30}")

    print("-" * 115)
    print(f"RESULTADO: {passed_count} views OK | {failed_count} views com FALHAS.")
    print("=" * 80)

    await engine.dispose()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_audit())
