import asyncio
import inspect
import logging
import uuid
import time
import oracledb
import asyncpg
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tenant import Tenant
from models.view_catalog import ViewCatalog
from models.sync_queue import SyncQueue
from services.oracle_service import decrypt_connection_details, get_oracle_connection
from services.postgresql_clone_service import get_clone_db_connection
from services.data_platform.catalog_api import catalog_api
from services.cache_service import global_cache

logger = logging.getLogger("luminaai.services.sync")

# Conjunto global para rastrear sincronizações ativas por Tenant (Thread/Async Safe)
_active_syncs: set[uuid.UUID] = set()
_active_syncs_lock = asyncio.Lock()
_sync_progress: dict[uuid.UUID, dict[str, Any]] = {}
_sync_progress_lock = asyncio.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _set_sync_progress(tenant_id: uuid.UUID | str, **updates: Any) -> dict[str, Any]:
    tenant_key = uuid.UUID(str(tenant_id))
    async with _sync_progress_lock:
        current = dict(_sync_progress.get(tenant_key, {}))
        current.update(updates)
        current["tenant_id"] = str(tenant_key)
        current["updated_at"] = _now_iso()
        _sync_progress[tenant_key] = current
        return dict(current)


async def get_sync_progress(tenant_id: uuid.UUID | str) -> dict[str, Any] | None:
    tenant_key = uuid.UUID(str(tenant_id))
    async with _sync_progress_lock:
        progress = _sync_progress.get(tenant_key)
        return dict(progress) if progress else None


async def _close_oracle_resource(resource) -> None:
    """Close Oracle resources safely across async and thin/sync driver modes."""
    if not resource:
        return
    result = resource.close()
    if inspect.isawaitable(result):
        await result


def _get_sync_config(sync_config) -> dict:
    if isinstance(sync_config, dict):
        return sync_config
    if isinstance(sync_config, str) and sync_config.strip():
        import json
        try:
            return json.loads(sync_config)
        except Exception:
            pass
    return {}


async def sync_tenant_database(tenant_id: uuid.UUID | str, db_session: AsyncSession, *, force_full: bool = False) -> None:
    """
    Sincroniza o banco de dados Oracle de produção com a base de dados PostgreSQL clonada local.
    Copia todas as views ativas do catálogo do tenant utilizando o SyncEngine com staging tables e atomicidade.
    """
    tenant_key = uuid.UUID(str(tenant_id))
    
    # 1. Busca as configurações do Tenant
    stmt = select(Tenant).where(Tenant.id == tenant_key)
    res = await db_session.execute(stmt)
    tenant = res.scalar_one_or_none()
    
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} não encontrado no sistema.")
        
    tenant_name = tenant.nome

    # 2. Controle de concorrência para proteger o banco Oracle de múltiplas conexões simultâneas
    async with _active_syncs_lock:
        if tenant_key in _active_syncs:
            raise RuntimeError("Sincronização já em andamento para esta empresa.")
        _active_syncs.add(tenant_key)
        
    try:
        # 3. Busca as views ativas do catálogo
        stmt_views = select(ViewCatalog).where(
            ViewCatalog.tenant_id == tenant_key,
            ViewCatalog.ativo.is_(True)
        )
        res_views = await db_session.execute(stmt_views)
        views = res_views.scalars().all()

        await _set_sync_progress(
            tenant_key,
            active=True,
            status="running",
            phase="starting",
            percent=0.0,
            current_view=None,
            current_view_index=0,
            total_views=len(views),
            current_view_rows=0,
            current_view_estimated_rows=None,
            processed_views=0,
            processed_rows=0,
            total_rows=0,
            message="Preparando sincronizacao das views cadastradas.",
            started_at=_now_iso(),
            finished_at=None,
            error=None,
        )
        
        if not views:
            logger.info("Nenhuma view ativa encontrada para o tenant %s. Ignorando sincronização.", tenant_name)
            tenant.sync_config = {
                **_get_sync_config(tenant.sync_config),
                "last_sync": datetime.now(timezone.utc).isoformat(),
                "last_sync_status": "success",
                "last_sync_message": "Sincronização ignorada: nenhuma view ativa cadastrada no catálogo."
            }
            db_session.add(tenant)
            await db_session.commit()
            await _set_sync_progress(
                tenant_key,
                active=False,
                status="completed",
                phase="completed",
                percent=100.0,
                message="Sincronizacao ignorada: nenhuma view ativa cadastrada.",
                finished_at=_now_iso(),
            )
            return

        # 4. Inicializa o Fila de Sincronização
        job_id = uuid.uuid4()
        job = SyncQueue(
            id=job_id,
            tenant_id=tenant_key,
            status="RUNNING",
            quantidade_views=len(views),
            quantidade_registros=0,
            resultado="Sincronização iniciada",
        )
        db_session.add(job)
        await db_session.commit()

        # 5. Inicia as conexões utilizando os imports patcheados nos testes

        # 4. Inicializa o Fila de Sincronização
        job_id = uuid.uuid4()
        job = SyncQueue(
            id=job_id,
            tenant_id=tenant_key,
            status="RUNNING",
            quantidade_views=len(views),
            quantidade_registros=0,
            resultado="Sincronização iniciada",
        )
        db_session.add(job)
        await db_session.commit()

        # 5. Inicia as conexões utilizando os imports patcheados nos testes
        oracle_conn = None
        pg_conn = None
        total_records = 0
        job_status = "SUCCESS"
        job_result = ""
        errors = []
        warnings = []
        start_time = time.perf_counter()
        try:
            logger.info("Iniciando sincronização para o tenant %s via SyncEngine...", tenant_name)
            
            # Conexão Oracle (fonte)
            oracle_details = decrypt_connection_details(tenant.oracle_conn)
            oracle_conn = await get_oracle_connection(oracle_details)
            oracle_conn.call_timeout = 600000  # 10 minutos para cargas volumosas
            
            # Conexão PostgreSQL Clone (destino)
            pg_details = decrypt_connection_details(tenant.clone_db_conn)
            pg_conn = await get_clone_db_connection(pg_details)
            
            # 6. Sincroniza view por view delegando para o SyncEngine
            from services.data_platform.sync_engine import (
                _oracle_identifier,
                _split_oracle_identifier,
                sync_engine,
            )
            import time as ptime
            
            total_views = max(len(views), 1)
            for view_index, view in enumerate(views, start=1):
                view_name_raw = view.nome_view_oracle
                
                clean_view_name = _oracle_identifier(*_split_oracle_identifier(view_name_raw))
                view_start_time = ptime.perf_counter()
                await _set_sync_progress(
                    tenant_key,
                    active=True,
                    status="running",
                    phase="syncing",
                    percent=round(((view_index - 1) / total_views) * 100, 2),
                    current_view=clean_view_name,
                    current_view_index=view_index,
                    total_views=len(views),
                    current_view_rows=0,
                    current_view_estimated_rows=None,
                    processed_views=view_index - 1,
                    processed_rows=total_records,
                    total_rows=total_records,
                    message=f"Sincronizando view {view_index} de {len(views)}: {clean_view_name}.",
                    error=None,
                )

                async def on_view_progress(
                    event: dict[str, Any],
                    *,
                    _view_index: int = view_index,
                    _view_name: str = clean_view_name,
                ) -> None:
                    imported_rows = int(event.get("imported_rows") or 0)
                    estimated_rows = event.get("estimated_rows")
                    estimated_int = (
                        int(estimated_rows)
                        if isinstance(estimated_rows, int) or str(estimated_rows or "").isdigit()
                        else None
                    )
                    phase = str(event.get("phase") or "syncing")
                    phase_label = {
                        "metadata": "Lendo estrutura da view",
                        "counting": "Calculando volume da view",
                        "counted": "Volume identificado",
                        "copying": "Copiando dados",
                        "validating": "Validando dataset",
                        "switching": "Publicando tabela atualizada",
                        "persisting": "Registrando versao do dataset",
                        "completed": "View concluida",
                    }.get(phase, "Sincronizando")
                    view_share = 100 / total_views
                    base_percent = ((_view_index - 1) / total_views) * 100
                    if estimated_int and estimated_int > 0:
                        view_percent = min(imported_rows / estimated_int, 1.0)
                    elif phase in {"validating", "switching", "persisting", "completed"}:
                        view_percent = 0.95 if phase != "completed" else 1.0
                    else:
                        view_percent = 0.05
                    overall_percent = min(99.0, base_percent + (view_percent * view_share))
                    await _set_sync_progress(
                        tenant_key,
                        active=True,
                        status="running",
                        phase=phase,
                        percent=round(overall_percent, 2),
                        current_view=_view_name,
                        current_view_index=_view_index,
                        total_views=len(views),
                        current_view_rows=imported_rows,
                        current_view_estimated_rows=estimated_int,
                        processed_views=_view_index - 1,
                        processed_rows=total_records + imported_rows,
                        total_rows=total_records + imported_rows,
                        message=f"{phase_label}: {_view_name}.",
                    )
                
                try:
                    # Executa a sincronização segura (com staging, transação, validação e retry)
                    imported = await sync_engine._sync_single_view(
                        tenant_id=tenant_key,
                        view_name=clean_view_name,
                        view_catalog_id=view.id,
                        oracle_conn=oracle_conn,
                        pg_conn=pg_conn,
                        progress_callback=on_view_progress,
                        force_full=force_full,
                    )
                    total_records += imported
                    await _set_sync_progress(
                        tenant_key,
                        active=True,
                        status="running",
                        phase="completed",
                        percent=round((view_index / total_views) * 100, 2),
                        current_view=clean_view_name,
                        current_view_index=view_index,
                        total_views=len(views),
                        current_view_rows=imported,
                        current_view_estimated_rows=imported,
                        processed_views=view_index,
                        processed_rows=total_records,
                        total_rows=total_records,
                        message=f"View {clean_view_name} sincronizada com sucesso.",
                    )
                    
                    view_elapsed_ms = (ptime.perf_counter() - view_start_time) * 1000
                    await catalog_api.update_sync(
                        tenant_id=tenant_key,
                        estrutura_id=clean_view_name,
                        resultado_sync={
                            "status": "success",
                            "duracao_ms": view_elapsed_ms,
                            "registros": imported,
                            "erros": [],
                            "avisos": [],
                        },
                    )
                    warnings.append(f"View {clean_view_name} sincronizada com sucesso. {imported} registros.")
                    
                except Exception as exc:
                    logger.error("Falha ao ler ou sincronizar dados da view %s: %s", clean_view_name, exc)
                    view_elapsed_ms = (ptime.perf_counter() - view_start_time) * 1000
                    await catalog_api.update_sync(
                        tenant_id=tenant_key,
                        estrutura_id=clean_view_name,
                        resultado_sync={
                            "status": "failed",
                            "duracao_ms": view_elapsed_ms,
                            "registros": 0,
                            "erros": [{"tipo": type(exc).__name__, "mensagem": str(exc)}],
                            "avisos": [],
                        },
                    )
                    errors.append({
                        "view": clean_view_name,
                        "tipo": type(exc).__name__,
                        "mensagem": str(exc)
                    })
                    job_status = "FAILED"
                    raise exc

            # Invalida o cache
            for view in views:
                global_cache.clear_pattern(f"{tenant_key}:{view.nome_view_oracle.lower()}")
                await catalog_api.update_cache(tenant_key, view.nome_view_oracle, ativo=True)

            job_result = f"Sincronização concluída com sucesso: {len(views)} views atualizadas. Total de registros: {total_records}."
            await _set_sync_progress(
                tenant_key,
                active=False,
                status="completed",
                phase="completed",
                percent=100.0,
                current_view=None,
                current_view_rows=0,
                current_view_estimated_rows=None,
                processed_views=len(views),
                processed_rows=total_records,
                total_rows=total_records,
                message=job_result,
                finished_at=_now_iso(),
                error=None,
            )

        except Exception as exc:
            logger.exception("❌ Falha na sincronização do tenant %s", tenant_name)
            job_status = "FAILED"
            job_result = f"Erro de sincronização: {str(exc)}"
            errors.append({"tipo": type(exc).__name__, "mensagem": str(exc)})
            current_progress = await get_sync_progress(tenant_key) or {}
            await _set_sync_progress(
                tenant_key,
                active=False,
                status="failed",
                phase="failed",
                percent=float(current_progress.get("percent") or 0),
                message=job_result,
                finished_at=_now_iso(),
                error=str(exc),
            )
            raise exc

        finally:
            # Finaliza o job na fila e atualiza o tenant
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Recarrega o tenant na sessão para evitar dessincronização de estado
            stmt_t_reload = select(Tenant).where(Tenant.id == tenant_key)
            res_t_reload = await db_session.execute(stmt_t_reload)
            db_tenant = res_t_reload.scalar_one_or_none()
            
            if db_tenant:
                db_tenant.sync_config = {
                    **_get_sync_config(db_tenant.sync_config),
                    "last_sync": datetime.now(timezone.utc).isoformat(),
                    "last_sync_status": "success" if job_status == "SUCCESS" else "failed",
                    "last_sync_message": job_result
                }
                db_session.add(db_tenant)
            
            # Recarrega o job
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

            await db_session.commit()

            # Encerra conexões
            if oracle_conn:
                try:
                    await _close_oracle_resource(oracle_conn)
                except Exception:
                    pass
            if pg_conn:
                try:
                    from services.postgresql_clone_service import release_clone_db_connection
                    await release_clone_db_connection(pg_conn)
                except Exception:
                    pass

    finally:
        async with _active_syncs_lock:
            _active_syncs.discard(tenant_key)
