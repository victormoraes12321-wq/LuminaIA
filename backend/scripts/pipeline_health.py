import asyncio
import os
import sys
import uuid
import time
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Adiciona o diretório backend ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from services.metadata_catalog.repository import catalog_repository
from services.metadata_catalog.loader import load_corporate_catalog
from services.oracle_service import decrypt_connection_details

async def run_health_check():
    print("=" * 80)
    print("INICIANDO HEALTH CHECK DO PIPELINE ANALITICO")
    print("=" * 80)

    # Inicializa o catálogo corporativo para o script CLI
    try:
        load_corporate_catalog()
    except Exception as e:
        print(f"[!] Erro ao carregar CKC via loader: {e}")

    # 1. Check OpenAI
    print("[*] CHECK 1: OpenAI Connectivity...")
    try:
        from database import get_db_context
        from services.ai_credential_manager import ai_credential_manager
        
        async with get_db_context() as session:
            stmt = text("SELECT id FROM tenants LIMIT 1")
            res = await session.execute(stmt)
            row = res.fetchone()
            if row:
                tenant_id = row[0]
                lease = await ai_credential_manager.resolve_client(tenant_id=tenant_id)
                test_comp = await lease.client.chat.completions.create(
                    model=lease.model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=2
                )
                print("    [OK] OpenAI CONNECTED successfully")
            else:
                print("    [FAILED] OpenAI: Nenhum tenant localizado para teste")
    except Exception as e:
        print(f"    [FAILED] OpenAI FAILED: {e}")

    # 2. Check Oracle Connection
    print("\n[*] CHECK 2: Oracle Connection...")
    try:
        from database import get_db_context
        from models.tenant import Tenant
        from services.oracle_service import get_oracle_connection
        
        async with get_db_context() as session:
            stmt = text("SELECT id, oracle_conn FROM tenants LIMIT 1")
            res = await session.execute(stmt)
            row = res.fetchone()
            if row:
                tenant_id = row[0]
                crypt_conn = row[1]
                oracle_details = decrypt_connection_details(crypt_conn)
                
                # Executa conexão assíncrona
                conn = await get_oracle_connection(details=oracle_details, tenant_id=tenant_id)
                if conn:
                    cursor = conn.cursor()
                    await cursor.execute("SELECT 1 FROM DUAL")
                    row_val = await cursor.fetchone()
                    val = row_val[0] if row_val else None
                    print(f"    [OK] Oracle CONNECTED successfully (DUAL returns {val})")
                    await cursor.close()
                    await conn.close()
                else:
                    print("    [FAILED] Oracle FAILED: Conexao assincrona nula")
            else:
                print("    [FAILED] Oracle FAILED: Nenhum tenant localizado no banco corporativo")
    except Exception as e:
        print(f"    [FAILED] Oracle FAILED: {e}")

    # 3. Check PostgreSQL Clone Connection
    print("\n[*] CHECK 3: PostgreSQL Clone Connection...")
    clone_db_name = None
    try:
        from database import get_db_context
        from models.tenant import Tenant
        
        async with get_db_context() as session:
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
                
                engine = create_async_engine(clone_db_url, echo=False)
                async with engine.connect() as conn:
                    res_val = await conn.execute(text("SELECT 1"))
                    val = res_val.scalar()
                    print(f"    [OK] PostgreSQL Clone '{clone_db_name}' CONNECTED successfully (returns {val})")
                await engine.dispose()
            else:
                print("    [FAILED] PostgreSQL Clone FAILED: Nenhum tenant localizado")
    except Exception as e:
        print(f"    [FAILED] PostgreSQL Clone FAILED: {e}")

    # 4. Check Corporate Knowledge Catalog (CKC) Consistency
    print("\n[*] CHECK 4: Corporate Knowledge Catalog (CKC) Consistency...")
    try:
        views = list(catalog_repository.catalog.views.keys())
        entities = list(catalog_repository.catalog.entities.keys())
        aliases = list(catalog_repository.catalog.aliases.keys())
        metrics = list(catalog_repository.catalog.metrics.keys())
        dimensions = list(catalog_repository.catalog.dimensions.keys())
        
        pk_count = 0
        fk_count = 0
        desc_count = 0
        alias_count = 0
        metrics_count = 0
        rel_count = 0

        for v_name in views:
            v_meta = catalog_repository.get_view(v_name)
            if not v_meta:
                continue
            
            if v_meta.primary_key:
                pk_count += 1
            if v_meta.foreign_keys:
                fk_count += 1
            if v_meta.functional_description or v_meta.business_description:
                desc_count += 1
            if v_meta.relationships:
                rel_count += 1
                
            has_alias = False
            for a_meta in catalog_repository.catalog.aliases.values():
                if a_meta.canonical_name.startswith(f"{v_name}."):
                    has_alias = True
                    break
            if has_alias:
                alias_count += 1
                
            has_metric = len(catalog_repository.get_metrics_for_view(v_name)) > 0
            if has_metric:
                metrics_count += 1

        print(f"    - Catalog Views: {len(views)}")
        print(f"      -> {pk_count} possuem PK")
        print(f"      -> {fk_count} possuem FK")
        print(f"      -> {desc_count} possuem descricao")
        print(f"      -> {alias_count} possuem aliases semanticos")
        print(f"      -> {metrics_count} possuem metricas")
        print(f"      -> {rel_count} possuem relacionamentos de JOIN")

    except Exception as e:
        print(f"    [FAILED] CKC Consistency Check FAILED: {e}")

    print("=" * 80)
    print("HEALTH CHECK CONCLUIDO")
    print("=" * 80)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_health_check())
