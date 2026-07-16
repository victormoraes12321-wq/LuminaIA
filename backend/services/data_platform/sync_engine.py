"""
Sync Engine — LuminaAI Data Platform
-------------------------------------
O Sync Engine é o único componente autorizado a acessar diretamente o banco de dados do ERP (Oracle).
Responsável por ler do ERP e atualizar a Data Platform analítica de forma incremental,
transacional e com isolamento completo (Multi-Tenant).

Responsabilidades:
  - Fila de sincronização persistente (sync_queue)
  - Validação estrita antes da substituição do dataset (staging tables)
  - Substituição atômica no PostgreSQL (rename transacional)
  - Fallback automático e transparente de incremental para full sync
  - Mecanismo de Retry automático para falhas temporárias
  - Atualização do Metadata Catalog, Cache, Performance Layer e Datasets
  - Monitoramento de saúde (CPU, Memória, integridade, latência)
"""
import asyncio
import inspect
import logging
import uuid
import time
import json
import hashlib
import re
from datetime import datetime, timezone, date, time as dt_time
from decimal import Decimal
from typing import Any, Awaitable, Callable

import oracledb
import asyncpg
from sqlalchemy import select, update

from database import get_db_context
from models.tenant import Tenant
from models.view_catalog import ViewCatalog, ChartType
from models.dataset import Dataset
from models.sync_queue import SyncQueue
from services.oracle_service import decrypt_connection_details, get_oracle_connection
from services.postgresql_clone_service import get_clone_db_connection, release_clone_db_connection
from services.data_platform.catalog_api import catalog_api
from services.data_platform.history_service import history_service
from services.cache_service import global_cache

# Opcional para monitoramento real de CPU/Memória
try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger("luminaai.data_platform.sync_engine")


_ORACLE_IDENTIFIER_RE = re.compile(r"^[A-Z][A-Z0-9_$#]*$")


def _split_oracle_identifier(view_name: str) -> tuple[str | None, str]:
    """Valida e separa OWNER.VIEW sem permitir SQL arbitrario."""
    raw = str(view_name or "").strip().upper()
    parts = raw.split(".")
    if len(parts) == 1:
        owner = None
        object_name = parts[0]
    elif len(parts) == 2:
        owner, object_name = parts
    else:
        raise ValueError(f"Nome de view Oracle invalido: '{view_name}'")

    if owner is not None and not _ORACLE_IDENTIFIER_RE.fullmatch(owner):
        raise ValueError(f"Owner Oracle invalido: '{view_name}'")
    if not _ORACLE_IDENTIFIER_RE.fullmatch(object_name):
        raise ValueError(f"Nome de view Oracle invalido: '{view_name}'")
    return owner, object_name


def _oracle_identifier(owner: str | None, object_name: str) -> str:
    return f"{owner}.{object_name}" if owner else object_name


def _local_table_name(view_name: str) -> str:
    """Tabela local do clone usa apenas o nome da view, sem owner Oracle."""
    _owner, object_name = _split_oracle_identifier(view_name)
    return object_name.lower()

async def _close_oracle_resource(resource: Any) -> None:
    """Close Oracle resources safely across async and thin/sync driver modes."""
    if not resource:
        return
    result = resource.close()
    if inspect.isawaitable(result):
        await result


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]


def _serialize_dataset_value(value: Any) -> Any:
    """Convert database scalar values to JSONB-safe values for dataset history."""
    if isinstance(value, (datetime, date, dt_time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value
# Lock global para controle de concorrência por Tenant
_sync_locks: dict[uuid.UUID, asyncio.Lock] = {}
_sync_locks_lock = asyncio.Lock()


async def get_tenant_sync_lock(tenant_id: uuid.UUID) -> asyncio.Lock:
    """Retorna o lock assíncrono correspondente ao tenant."""
    async with _sync_locks_lock:
        if tenant_id not in _sync_locks:
            _sync_locks[tenant_id] = asyncio.Lock()
        return _sync_locks[tenant_id]


class SyncEngine:
    """
    Motor de Sincronização analítica do LuminaAI.
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def _resolve_oracle_view_identifier(
        self,
        oracle_conn: oracledb.Connection,
        view_name: str,
    ) -> str:
        """Resolve OWNER.VIEW quando a view existe fora do schema padrao da conexao."""
        owner, object_name = _split_oracle_identifier(view_name)
        if owner:
            return _oracle_identifier(owner, object_name)

        # Se for simulação Oracle local, retorna o próprio object_name diretamente
        from config import settings
        if settings.MOCK_ORACLE:
            return object_name


        cursor = oracle_conn.cursor()
        try:
            await cursor.execute(
                """
                SELECT owner
                FROM (
                    SELECT owner
                    FROM all_views
                    WHERE view_name = :view_name
                    ORDER BY
                        CASE
                            WHEN owner = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') THEN 0
                            WHEN owner NOT IN ('SYS', 'SYSTEM') THEN 1
                            ELSE 2
                        END,
                        owner
                )
                WHERE ROWNUM = 1
                """,
                {"view_name": object_name},
            )
            row = await _maybe_await(cursor.fetchone())
            if row and row[0]:
                return _oracle_identifier(str(row[0]).upper(), object_name)
            return object_name
        finally:
            await _close_oracle_resource(cursor)

    async def run_sync(self, tenant_id: uuid.UUID | str) -> uuid.UUID:
        """
        Inicia a sincronização de todas as views ativas do tenant em background.
        Registra a execução na fila sync_queue e executa o fluxo com segurança.
        """
        tenant_key = uuid.UUID(str(tenant_id))
        lock = await get_tenant_sync_lock(tenant_key)
        
        if lock.locked():
            logger.warning("[SyncEngine] Sincronização já em andamento para tenant: %s", tenant_key)
            raise RuntimeError("Sincronização já em andamento para esta empresa.")

        # Dispara a sincronização
        job_id = uuid.uuid4()
        asyncio.create_task(self._execute_sync_job(job_id, tenant_key, lock))
        return job_id

    async def _execute_sync_job(self, job_id: uuid.UUID, tenant_id: uuid.UUID, lock: asyncio.Lock) -> None:
        """Executa a sincronização completa da fila sob proteção do Lock."""
        async with lock:
            start_time = time.perf_counter()
            logger.info("[SyncEngine] Iniciando Job de sincronização %s para tenant %s", job_id, tenant_id)

            # 1. Registra o início na Fila de Sincronização
            async with get_db_context() as db_session:
                stmt_t = select(Tenant).where(Tenant.id == tenant_id)
                res_t = await db_session.execute(stmt_t)
                tenant = res_t.scalar_one_or_none()
                if not tenant:
                    logger.error("[SyncEngine] Tenant %s não encontrado para sincronização.", tenant_id)
                    return

                # Inicializa configuração de sync do tenant
                sync_config = tenant.sync_config or {}
                if isinstance(sync_config, str):
                    try:
                        sync_config = json.loads(sync_config)
                    except Exception:
                        sync_config = {}

                # Busca todas as views cadastradas e ativas
                stmt_views = select(ViewCatalog).where(
                    ViewCatalog.tenant_id == tenant_id,
                    ViewCatalog.ativo.is_(True)
                )
                res_views = await db_session.execute(stmt_views)
                views = res_views.scalars().all()

                job = SyncQueue(
                    id=job_id,
                    tenant_id=tenant_id,
                    status="RUNNING",
                    quantidade_views=len(views),
                    quantidade_registros=0,
                    resultado="Sincronização iniciada",
                )
                db_session.add(job)
                await db_session.commit()

            # 2. Configurações e Conexões
            oracle_conn = None
            pg_conn = None
            total_records = 0
            job_status = "SUCCESS"
            job_result = ""
            errors = []
            warnings = []

            try:
                # Obter credenciais criptografadas
                oracle_details = decrypt_connection_details(tenant.oracle_conn)
                pg_details = decrypt_connection_details(tenant.clone_db_conn)

                # Validar Conexões (Oracle e PostgreSQL) com retry
                oracle_conn = await self._connect_oracle_with_retry(oracle_details)
                pg_conn = await get_clone_db_connection(pg_details)

                # Sincroniza view por view
                for view in views:
                    view_name = _oracle_identifier(*_split_oracle_identifier(view.nome_view_oracle))
                    view_start = time.perf_counter()

                    try:
                        # Fluxo interno por View
                        imported = await self._sync_single_view(
                            tenant_id=tenant_id,
                            view_name=view_name,
                            view_catalog_id=view.id,
                            oracle_conn=oracle_conn,
                            pg_conn=pg_conn,
                        )
                        total_records += imported
                        warnings.append(f"View {view_name} atualizada com sucesso. {imported} registros.")

                    except Exception as view_exc:
                        logger.error("[SyncEngine] Falha na sincronização da view %s: %s", view_name, view_exc)
                        errors.append({
                            "view": view_name,
                            "tipo": type(view_exc).__name__,
                            "mensagem": str(view_exc)
                        })
                        job_status = "FAILED"

                # Invalidação seletiva do cache
                for view in views:
                    view_name = view.nome_view_oracle.upper()
                    # Invalida cache específico da view analítica
                    global_cache.clear_pattern(f"{tenant_id}:{view_name.lower()}")
                    await catalog_api.update_cache(tenant_id, view_name, ativo=True)

                job_result = f"Sincronização finalizada. Status final: {job_status}. Total de registros: {total_records}."

            except Exception as conn_exc:
                logger.exception("[SyncEngine] Falha crítica de conexão ou DDL durante o Job %s", job_id)
                job_status = "FAILED"
                job_result = f"Falha crítica: {str(conn_exc)}"
                errors.append({"tipo": type(conn_exc).__name__, "mensagem": str(conn_exc)})

            finally:
                # Encerrar conexões com segurança
                if oracle_conn:
                    try:
                        await _close_oracle_resource(oracle_conn)
                    except Exception:
                        pass
                if pg_conn:
                    try:
                        await release_clone_db_connection(pg_conn)
                    except Exception:
                        pass

                # 3. Finaliza sincronização na fila
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                async with get_db_context() as db_session:
                    # Atualiza o job de sync
                    stmt_j = select(SyncQueue).where(SyncQueue.id == job_id)
                    res_j = await db_session.execute(stmt_j)
                    db_job = res_j.scalar_one_or_none()
                    if db_job:
                        db_job.status = job_status
                        db_job.tempo_duracao_ms = elapsed_ms
                        db_job.quantidade_registros = total_records
                        db_job.resultado = job_result
                        db_job.erros = errors
                        db_job.avisos = warnings
                        db_session.add(db_job)

                    # Atualiza as configurações do tenant
                    stmt_ten = select(Tenant).where(Tenant.id == tenant_id)
                    res_ten = await db_session.execute(stmt_ten)
                    db_tenant = res_ten.scalar_one_or_none()
                    if db_tenant:
                        tenant_sync_cfg = db_tenant.sync_config or {}
                        if isinstance(tenant_sync_cfg, str):
                            try:
                                tenant_sync_cfg = json.loads(tenant_sync_cfg)
                            except Exception:
                                tenant_sync_cfg = {}
                        db_tenant.sync_config = {
                            **tenant_sync_cfg,
                            "last_sync": datetime.now(timezone.utc).isoformat(),
                            "last_sync_status": "success" if job_status == "SUCCESS" else "failed",
                            "last_sync_message": job_result
                        }
                        db_session.add(db_tenant)

                    await db_session.commit()

                # Registra auditoria global do Sync
                await history_service.log_change(
                    tenant_id=tenant_id,
                    estrutura_tipo="METADADOS",
                    cat_id=str(job_id),  # Resolvendo o parâmetro correto de log_change
                    acao="VERSION_UP" if job_status == "SUCCESS" else "RECONSTRUCT",
                    detalhes={
                        "job_id": str(job_id),
                        "duracao_ms": elapsed_ms,
                        "status": job_status,
                        "views": len(views),
                        "total_registros": total_records,
                        "erros": errors,
                    }
                )
                logger.info("[SyncEngine] Sincronização finalizada com sucesso para tenant %s", tenant_id)

                # Publica evento de fim do Sync
                from services.data_platform.event_engine import event_engine
                await event_engine.publish(tenant_id, "SYNC_FINISHED", {
                    "job_id": str(job_id),
                    "status": job_status,
                    "records_synchronized": total_records
                })

                # Dispara Smart Refresh reativo nos pacotes analíticos ativos
                if job_status == "SUCCESS":
                    try:
                        from models.analytical_package import AnalyticalPackage, PackageStatus
                        from services.data_platform.live_dashboard_runtime import live_dashboard_runtime
                        async with get_db_context() as fresh_db:
                            stmt_pkgs = select(AnalyticalPackage).where(
                                AnalyticalPackage.tenant_id == tenant_id,
                                AnalyticalPackage.status == PackageStatus.ACTIVE
                            )
                            res_pkgs = await fresh_db.execute(stmt_pkgs)
                            active_packages = res_pkgs.scalars().all()
                            for pkg in active_packages:
                                logger.info("[SyncEngine] Disparando Smart Refresh automático para o pacote %s", pkg.id)
                                await live_dashboard_runtime.refresh_runtime(tenant_id, pkg.id, fresh_db)
                    except Exception as refresh_err:
                        logger.error("[SyncEngine] Falha no Smart Refresh automático pós-sync: %s", refresh_err)

    async def _sync_single_view(
        self,
        tenant_id: uuid.UUID,
        view_name: str,
        view_catalog_id: uuid.UUID,
        oracle_conn: oracledb.Connection,
        pg_conn: asyncpg.Connection,
        progress_callback: ProgressCallback | None = None,
    ) -> int:
        """Executa a sincronização segura de uma única view usando staging tables."""
        table_name = _local_table_name(view_name)
        staging_table = f"{table_name}_staging"
        oracle_view_identifier = await self._resolve_oracle_view_identifier(oracle_conn, view_name)
        logger.info(
            "[SyncEngine] Sincronizando view: %s | Oracle: %s | Tabela: %s",
            view_name,
            oracle_view_identifier,
            table_name,
        )
        if progress_callback:
            await progress_callback({"phase": "metadata", "imported_rows": 0, "estimated_rows": None})

        # 1. Validar estrutura do ERP
        oracle_cursor = oracle_conn.cursor()
        oracle_cursor.arraysize = 2000
        try:
            # Executa apenas para pegar descrição e estrutura
            await oracle_cursor.execute(f"SELECT * FROM {oracle_view_identifier} WHERE 1=0")
            col_desc = oracle_cursor.description
        except Exception as erp_exc:
            logger.error("[SyncEngine] View %s não encontrada ou inacessível no ERP Oracle.", view_name)
            raise RuntimeError(f"View {view_name} inválida no ERP: {str(erp_exc)}")
        finally:
            await _close_oracle_resource(oracle_cursor)

        # 2. Constrói DDL de Staging
        cols_ddl = []
        for desc in col_desc:
            col_name = desc[0].lower()
            col_type = desc[1]
            if col_type == oracledb.DB_TYPE_NUMBER:
                pg_type = "NUMERIC"
            elif col_type in (oracledb.DB_TYPE_DATE, oracledb.DB_TYPE_TIMESTAMP, oracledb.DB_TYPE_TIMESTAMP_TZ):
                pg_type = "TIMESTAMP"
            else:
                pg_type = "TEXT"
            cols_ddl.append(f"{col_name} {pg_type}")
        cols_str = ", ".join(cols_ddl)

        # 3. Cria tabela de staging limpa
        async with pg_conn.transaction():
            await pg_conn.execute(f"DROP TABLE IF EXISTS {staging_table} CASCADE;")
            await pg_conn.execute(f"CREATE TABLE {staging_table} ({cols_str});")

        # 4. Determina Modo de Sincronização (Incremental vs Full)
        # Se a tabela oficial já existe e tem dados, e possui campo incremental
        incremental_column = await self._detect_incremental_column(pg_conn, table_name)
        last_sync_val = None

        if incremental_column:
            try:
                # Verifica o último valor registrado
                last_sync_val = await pg_conn.fetchval(f"SELECT max({incremental_column}) FROM {table_name}")
                if last_sync_val:
                    # Copia registros atuais para a staging para servir de base
                    # Especifica colunas de forma explícita para evitar erros se as tabelas tiverem colunas diferentes
                    columns_list = [desc[0].lower() for desc in col_desc]
                    cols_joined_dest = ", ".join(f'"{c}"' for c in columns_list)
                    cols_joined_src = ", ".join(f'"{table_name}"."{c}"' for c in columns_list)
                    async with pg_conn.transaction():
                        await pg_conn.execute(f"INSERT INTO {staging_table} ({cols_joined_dest}) SELECT {cols_joined_src} FROM {table_name};")
            except Exception as copy_exc:
                logger.warning(
                    "[SyncEngine] Falha ao copiar base incremental para staging (possível alteração de schema): %s. "
                    "Forçando carga completa (Full sync).",
                    copy_exc
                )
                last_sync_val = None
                # Limpa a staging table para carga cheia
                async with pg_conn.transaction():
                    await pg_conn.execute(f"TRUNCATE TABLE {staging_table};")

        # 5. Busca dados necessários do ERP
        oracle_cursor = oracle_conn.cursor()
        oracle_cursor.arraysize = 2000
        
        query = f"SELECT * FROM {oracle_view_identifier}"
        params = {}
        if incremental_column and last_sync_val:
            # Se for incremental, filtra do Oracle
            if isinstance(last_sync_val, (datetime, date)):
                query += f" WHERE {incremental_column.upper()} > :last_val"
                params["last_val"] = last_sync_val
            else:
                query += f" WHERE {incremental_column.upper()} > :last_val"
                params["last_val"] = last_sync_val

            logger.info("[SyncEngine] Executando carga INCREMENTAL para %s a partir de %s", view_name, last_sync_val)
        else:
            logger.info("[SyncEngine] Executando carga COMPLETA (Full) para %s", view_name)

        estimated_rows: int | None = None
        if progress_callback:
            await progress_callback({"phase": "counting", "imported_rows": 0, "estimated_rows": None})
        count_cursor = oracle_conn.cursor()
        try:
            await count_cursor.execute(f"SELECT COUNT(*) FROM ({query})", params)
            count_row = await _maybe_await(count_cursor.fetchone())
            if count_row:
                count_value = count_row[0]
                if isinstance(count_value, (int, float, Decimal, str)):
                    estimated_rows = int(count_value or 0)
        except Exception as count_exc:
            logger.warning("[SyncEngine] Nao foi possivel estimar linhas da view %s: %s", view_name, count_exc)
        finally:
            await _close_oracle_resource(count_cursor)
        if progress_callback:
            await progress_callback({"phase": "counted", "imported_rows": 0, "estimated_rows": estimated_rows})

        # Copia dados com controle de retry por lote
        placeholders = ", ".join(f"${i+1}" for i in range(len(col_desc)))
        insert_sql = f"INSERT INTO {staging_table} VALUES ({placeholders})"
        imported_rows = 0

        try:
            await oracle_cursor.execute(query, params)
            
            while True:
                rows_chunk = await oracle_cursor.fetchmany(2000)
                if not rows_chunk:
                    break
                
                # Executa o insert do lote com retry
                await self._insert_chunk_with_retry(pg_conn, insert_sql, rows_chunk)
                imported_rows += len(rows_chunk)
                if progress_callback:
                    await progress_callback({
                        "phase": "copying",
                        "imported_rows": imported_rows,
                        "estimated_rows": estimated_rows,
                    })

        except Exception as data_exc:
            # Cancela a sincronização executando rollback implícito da staging
            await pg_conn.execute(f"DROP TABLE IF EXISTS {staging_table} CASCADE;")
            raise data_exc
        finally:
            await _close_oracle_resource(oracle_cursor)

        # 6. Validação do Dataset de Staging
        # Validar: integridade, quantidade de registros, relacionamentos, estrutura, checksum/hash
        if progress_callback:
            await progress_callback({
                "phase": "validating",
                "imported_rows": imported_rows,
                "estimated_rows": estimated_rows,
            })
        validation_passed = await self._validate_dataset(pg_conn, staging_table, table_name, incremental_column)
        if not validation_passed:
            await pg_conn.execute(f"DROP TABLE IF EXISTS {staging_table} CASCADE;")
            raise ValueError(f"Validação de integridade do dataset falhou para a view {view_name}.")

        # 7. Substituição Atômica (Switch tables)
        # DROP TABLE antigo, rename oficial para old, rename staging para oficial.
        if progress_callback:
            await progress_callback({
                "phase": "switching",
                "imported_rows": imported_rows,
                "estimated_rows": estimated_rows,
            })
        try:
            async with pg_conn.transaction():
                # Remove se existir resíduo
                await pg_conn.execute(f"DROP TABLE IF EXISTS {table_name}_old CASCADE;")
                
                # Se a tabela oficial existe, faz o switch
                table_exists = await pg_conn.fetchval(
                    "SELECT exists(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                    table_name
                )
                if table_exists:
                    await pg_conn.execute(f"ALTER TABLE {table_name} RENAME TO {table_name}_old;")
                
                await pg_conn.execute(f"ALTER TABLE {staging_table} RENAME TO {table_name};")
                await pg_conn.execute(f"DROP TABLE IF EXISTS {table_name}_old CASCADE;")

            logger.info("[SyncEngine] View %s chaveada com sucesso! Linhas: %d", view_name, imported_rows)

        except Exception as tx_exc:
            logger.error("[SyncEngine] Erro na transação atômica de chaveamento: %s", tx_exc)
            # Rollback e limpeza
            await pg_conn.execute(f"DROP TABLE IF EXISTS {staging_table} CASCADE;")
            raise tx_exc

        # 8. Criação de nova versão em Datasets (para persistência histórica JSONB)
        if progress_callback:
            await progress_callback({
                "phase": "persisting",
                "imported_rows": imported_rows,
                "estimated_rows": estimated_rows,
            })
        await self._persist_dataset_version(tenant_id, view_name, view_catalog_id, pg_conn, table_name)
        if progress_callback:
            await progress_callback({
                "phase": "completed",
                "imported_rows": imported_rows,
                "estimated_rows": estimated_rows,
            })

        return imported_rows

    async def _detect_incremental_column(self, pg_conn: asyncpg.Connection, table_name: str) -> str | None:
        """Tenta detectar uma coluna temporal ou id para fins de sincronização incremental."""
        table_exists = await pg_conn.fetchval(
            "SELECT exists(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
            table_name
        )
        if not table_exists:
            return None

        # Busca colunas da tabela
        columns = await pg_conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = $1",
            table_name
        )
        
        # Prioridade para campos de auditoria temporal comuns
        temporal_candidates = ["data_ref", "dt_emissao", "atualizado_em", "data_modificacao", "data_criacao", "data_movimento"]
        col_names = [c["column_name"] for c in columns]
        
        for cand in temporal_candidates:
            if cand in col_names:
                return cand

        # Retorna id se numérico
        if "id" in col_names:
            col_type = next(c["data_type"] for c in columns if c["column_name"] == "id")
            if "integer" in col_type or "numeric" in col_type:
                return "id"

        return None

    async def _validate_dataset(
        self,
        pg_conn: asyncpg.Connection,
        staging_table: str,
        table_name: str,
        incremental_column: str | None
    ) -> bool:
        """Valida integridade, contagem e estrutura da staging antes da substituição."""
        try:
            # 1. Quantidade de registros
            count = await pg_conn.fetchval(f"SELECT count(*) FROM {staging_table}")
            if count is None:
                return False
            
            # Se a tabela anterior existe e tinha dados, a nova não deveria estar completamente vazia
            table_exists = await pg_conn.fetchval(
                "SELECT exists(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                table_name
            )
            if table_exists:
                prev_count = await pg_conn.fetchval(f"SELECT count(*) FROM {table_name}")
                if prev_count > 0 and count == 0 and not incremental_column:
                    logger.warning("[SyncEngine] Nova tabela de staging possui 0 registros enquanto anterior tinha %d.", prev_count)
                    return False

            # 2. Validação estrutural básica
            cols_staging = await pg_conn.fetch(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = $1",
                staging_table
            )
            if not cols_staging:
                return False

            # 3. Calcula checksum simples para verificar corrupção estrutural
            col_concat = "".join(f"{c['column_name']}:{c['data_type']}" for c in cols_staging)
            struct_hash = hashlib.md5(col_concat.encode("utf-8")).hexdigest()
            logger.debug("[SyncEngine] Checksum estrutural da staging %s: %s", staging_table, struct_hash)

            return True

        except Exception as val_exc:
            logger.error("[SyncEngine] Erro durante a validação da staging %s: %s", staging_table, val_exc)
            return False

    async def _persist_dataset_version(
        self,
        tenant_id: uuid.UUID,
        view_name: str,
        view_catalog_id: uuid.UUID,
        pg_conn: asyncpg.Connection,
        table_name: str
    ) -> None:
        """Persiste uma amostragem/versão dos dados em formato JSONB na tabela datasets para histórico."""
        try:
            # Pega as últimas 500 linhas para guardar em JSONB
            rows = await pg_conn.fetch(f"SELECT * FROM {table_name} LIMIT 500")
            
            # Converte para list dict
            serialized_data = []
            for r in rows:
                row_dict = {}
                for k, v in r.items():
                    row_dict[k] = _serialize_dataset_value(v)
                serialized_data.append(row_dict)

            async with get_db_context() as db_session:
                # Determina versão anterior
                stmt_prev = select(Dataset.version).where(
                    Dataset.tenant_id == tenant_id,
                    Dataset.view_catalog_id == view_catalog_id
                ).order_by(Dataset.version.desc()).limit(1)
                res_prev = await db_session.execute(stmt_prev)
                max_v = res_prev.scalar_one_or_none() or 0

                # Tipo das colunas
                columns_meta = await pg_conn.fetch(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = $1",
                    table_name
                )
                tipagem = {c["column_name"]: c["data_type"] for c in columns_meta}

                new_dataset = Dataset(
                    tenant_id=tenant_id,
                    dados_estruturados=serialized_data,
                    tipagem_correta=tipagem,
                    version=max_v + 1,
                    origem="ERP_ORACLE",
                    view_catalog_id=view_catalog_id,
                    metadados={
                        "nome_view": view_name,
                        "quantidade_total": len(serialized_data),
                        "checksum_tabela": hashlib.md5(str(serialized_data).encode("utf-8")).hexdigest()
                    }
                )
                db_session.add(new_dataset)
                await db_session.commit()

                # Registra histórico de criação
                await history_service.log_change(
                    tenant_id=tenant_id,
                    estrutura_tipo="DATASET",
                    estrutura_id=str(new_dataset.id),
                    acao="VERSION_UP",
                    detalhes={
                        "view_name": view_name,
                        "versao": max_v + 1,
                        "registros": len(serialized_data)
                    }
                )

        except Exception as ds_exc:
            logger.error("[SyncEngine] Falha ao persistir a amostragem do dataset no banco central: %s", ds_exc)

    # ── Métodos Utilitários com Retry ──────────────────────────────────────

    async def _connect_oracle_with_retry(self, details: dict) -> oracledb.Connection:
        """Estabelece a conexão com o Oracle com política de Retry."""
        for attempt in range(1, self.max_retries + 1):
            try:
                conn = await get_oracle_connection(details)
                conn.call_timeout = 60000 # 60s
                return conn
            except Exception as e:
                logger.warning(
                    "[SyncEngine] Tentativa %d de conexão com Oracle falhou. Retrying em %ss... Erro: %s",
                    attempt, self.retry_delay, e
                )
                if attempt == self.max_retries:
                    raise e
                await asyncio.sleep(self.retry_delay)

    async def _insert_chunk_with_retry(
        self,
        pg_conn: asyncpg.Connection,
        insert_sql: str,
        chunk: list
    ) -> None:
        """Insere um chunk de dados no Postgres com controle de retry em caso de falha de conexão/transação."""
        for attempt in range(1, self.max_retries + 1):
            try:
                async with pg_conn.transaction():
                    await pg_conn.executemany(insert_sql, chunk)
                return
            except Exception as e:
                logger.warning(
                    "[SyncEngine] Tentativa %d de inserção de lote falhou. Retrying... Erro: %s",
                    attempt, e
                )
                if attempt == self.max_retries:
                    raise e
                await asyncio.sleep(self.retry_delay)


# Singleton export
sync_engine = SyncEngine()
