"""
Sync Orchestrator / Sync Scheduler — LuminaAI Data Platform
-----------------------------------------------------------
Controlador central de agendamento e execução de sincronizações da Data Platform.
Coordena quando, como e sob quais condições a sincronização (SyncEngine) é executada.

Funcionalidades:
  - Agendamento flexível por horários, dias da semana e fuso horário (zoneinfo).
  - Lock Global por Tenant (garante execução única por vez).
  - Janela de execução monitorada com geração de alertas se excedida.
  - Relatório consolidado para Dashboard Administrativo.
  - Validação de disponibilidade de conexões ERP e Data Platform antes de iniciar.
  - Auditoria completa via history_service.
"""
import asyncio
import logging
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Any

# Suporte nativo para fuso horário no Python 3.9+
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from sqlalchemy import select
from database import get_db_context
from models.tenant import Tenant
from models.sync_queue import SyncQueue
from models.view_catalog import ViewCatalog
from models.metadata_catalog import MetadataCatalog
from services.oracle_service import decrypt_connection_details, get_oracle_connection
from services.postgresql_clone_service import get_clone_db_connection, release_clone_db_connection
from services.data_platform.sync_engine import sync_engine
from services.data_platform.catalog_api import catalog_api
from services.data_platform.history_service import history_service

logger = logging.getLogger("luminaai.data_platform.sync_scheduler")

# Lock Global do Orchestrator (in-memory lock por Tenant)
_orchestrator_locks: dict[uuid.UUID, asyncio.Lock] = {}
_orchestrator_locks_lock = asyncio.Lock()


async def get_orchestrator_lock(tenant_id: uuid.UUID) -> asyncio.Lock:
    """Retorna o lock assíncrono global do orchestrator para o tenant."""
    async with _orchestrator_locks_lock:
        if tenant_id not in _orchestrator_locks:
            _orchestrator_locks[tenant_id] = asyncio.Lock()
        return _orchestrator_locks[tenant_id]


class SyncOrchestrator:
    """
    Coordenador e Controlador Central de Sincronizações da Data Platform.
    """

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval_seconds = check_interval_seconds

    def _get_localized_time(self, tz_name: str | None) -> datetime:
        """Retorna o horário local atual com base no fuso horário configurado."""
        now_utc = datetime.now(timezone.utc)
        if ZoneInfo and tz_name:
            try:
                return now_utc.astimezone(ZoneInfo(tz_name))
            except Exception as e:
                logger.warning("[SyncOrchestrator] Fuso horário inválido '%s': %s. Usando UTC.", tz_name, e)
        
        # Fallback para fuso horário UTC ou tentativa manual simples se zoneinfo falhar
        if tz_name == "America/Sao_Paulo":
            return now_utc.astimezone(timezone(timedelta(hours=-3)))
        return now_utc

    def should_trigger_sync(self, sync_config: dict, current_time_local: datetime) -> bool:
        """
        Determina se a sincronização deve rodar de acordo com a configuração e data local atual.
        """
        if not sync_config.get("enabled", False):
            return False

        # 1. Verifica dias da semana (0 = Segunda, 6 = Domingo)
        days_of_week = sync_config.get("days_of_week")
        if days_of_week is not None:
            # Garante formato de lista
            if not isinstance(days_of_week, list):
                days_of_week = [int(days_of_week)]
            if current_time_local.weekday() not in days_of_week:
                return False

        # 2. Verifica horário programado (HH:MM)
        scheduled_times = sync_config.get("times", [])
        time_str = current_time_local.strftime("%H:%M")
        if time_str not in scheduled_times:
            return False

        return True

    async def execute_scheduled_sync(self, tenant_id: uuid.UUID, reason: str = "Agendamento Automático") -> uuid.UUID | None:
        """
        Executa o fluxo completo do Orchestrator para disparar a sincronização.
        Garante locks, validações de infraestrutura antes da execução, monitora janela de tempo e cria alertas.
        """
        lock = await get_orchestrator_lock(tenant_id)
        
        # Garante que apenas uma sincronização ocorra por vez
        if lock.locked():
            logger.warning("[SyncOrchestrator] Concorrência bloqueada: Sincronização já ativa para tenant %s", tenant_id)
            return None

        async with lock:
            start_time = time.perf_counter()
            job_id = uuid.uuid4()
            logger.info("[SyncOrchestrator] [Job %s] Iniciando verificação de disponibilidade...", job_id)

            # 1. Busca configurações e conexões do Tenant
            async with get_db_context() as db_session:
                stmt = select(Tenant).where(Tenant.id == tenant_id)
                res = await db_session.execute(stmt)
                tenant = res.scalar_one_or_none()
                if not tenant or not tenant.ativo:
                    logger.error("[SyncOrchestrator] Tenant %s não existe ou está inativo.", tenant_id)
                    return None

                sync_config = tenant.sync_config or {}
                if isinstance(sync_config, str):
                    try:
                        sync_config = json.loads(sync_config)
                    except Exception:
                        sync_config = {}

                # Busca quantidade de views ativas
                stmt_views = select(ViewCatalog).where(
                    ViewCatalog.tenant_id == tenant_id,
                    ViewCatalog.ativo.is_(True)
                )
                res_views = await db_session.execute(stmt_views)
                views = res_views.scalars().all()

            # Registrar a execução na Fila de sincronização como PENDING
            async with get_db_context() as db_session:
                job_entry = SyncQueue(
                    id=job_id,
                    tenant_id=tenant_id,
                    status="PENDING",
                    quantidade_views=len(views),
                    resultado=f"Aguardando validações de infraestrutura. Iniciado por: {reason}",
                )
                db_session.add(job_entry)
                await db_session.commit()

            # 2. Validações de Infraestrutura (Conexões) antes de delegar
            validation_errors = []
            oracle_conn = None
            pg_conn = None
            try:
                # Validar conexão com ERP (Oracle)
                oracle_details = decrypt_connection_details(tenant.oracle_conn)
                oracle_conn = await get_oracle_connection(oracle_details)
                await oracle_conn.close() # Conecta e fecha
            except Exception as e:
                validation_errors.append(f"Conexão com ERP Oracle falhou: {str(e)}")

            try:
                # Validar conexão com Data Platform (PostgreSQL)
                pg_details = decrypt_connection_details(tenant.clone_db_conn)
                pg_conn = await get_clone_db_connection(pg_details)
                await release_clone_db_connection(pg_conn)
            except Exception as e:
                validation_errors.append(f"Conexão com Data Platform falhou: {str(e)}")

            if validation_errors:
                # Se falhar validações, aborta antes de chamar o SyncEngine
                err_msg = "; ".join(validation_errors)
                logger.error("[SyncOrchestrator] Validação de infraestrutura falhou: %s", err_msg)
                
                async with get_db_context() as db_session:
                    stmt_j = select(SyncQueue).where(SyncQueue.id == job_id)
                    res_j = await db_session.execute(stmt_j)
                    db_job = res_j.scalar_one_or_none()
                    if db_job:
                        db_job.status = "FAILED"
                        db_job.resultado = f"Falha na validação de infraestrutura: {err_msg}"
                        db_job.erros = [{"tipo": "INFRA_VALIDATION_ERROR", "mensagem": err_msg}]
                        db_session.add(db_job)
                    await db_session.commit()

                # Notifica falha
                await catalog_api.update_sync(tenant_id, "SYSTEM", {
                    "status": "failed",
                    "duracao_ms": 0.0,
                    "registros": 0,
                    "erros": [{"tipo": "INFRA_ERROR", "mensagem": err_msg}]
                })
                
                await history_service.log_change(
                    tenant_id=tenant_id,
                    estrutura_tipo="METADADOS",
                    estrutura_id=str(job_id),
                    acao="RECONSTRUCT",
                    detalhes={"status": "FAILED", "motivo": err_msg}
                )
                return job_id

            # 3. Invoca o SyncEngine
            # Atualiza o status do job para RUNNING
            async with get_db_context() as db_session:
                stmt_j = select(SyncQueue).where(SyncQueue.id == job_id)
                res_j = await db_session.execute(stmt_j)
                db_job = res_j.scalar_one_or_none()
                if db_job:
                    db_job.status = "RUNNING"
                    db_job.resultado = "Validações completadas. Executando cópia de dados."
                    db_session.add(db_job)
                await db_session.commit()

            # Dispara a execução síncrona/inline do sync_tenant_database
            # (que já utiliza staging e realiza o rename de tabelas sob transações de forma atômica)
            try:
                from services.sync_service import sync_tenant_database
                # Para fins de compatibilidade e locks, o sync_tenant_database gerencia seu próprio ciclo,
                # mas o orchestrator fica monitorando externamente a janela de tempo
                
                # Executa sync em tarefa de background e monitora
                sync_task = asyncio.create_task(self._run_sync_with_db_context(tenant_id))
                
                max_minutes = sync_config.get("max_execution_time_minutes", 60)
                max_seconds = max_minutes * 60
                
                # Aguarda com timeout da janela
                try:
                    await asyncio.wait_for(sync_task, timeout=max_seconds)
                except asyncio.TimeoutError:
                    logger.warning("[SyncOrchestrator] Janela de execução excedida (%d min) para tenant %s", max_minutes, tenant_id)
                    # Registra alerta no MetadataCatalog de sistema
                    await catalog_api.register(
                        tenant_id=tenant_id,
                        tipo="VIEW",
                        dados={
                            "estrutura_id": "SYSTEM_SYNC",
                            "nome_view": "SYSTEM_SYNC",
                            "alertas": [{
                                "tipo": "TIMEOUT",
                                "score": 50.0,
                                "descricao": f"Janela de sincronização ultrapassou {max_minutes} minutos.",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }]
                        }
                    )
                    # Continua aguardando sem interromper de forma abrupta a sincronização em andamento
                    await sync_task

            except Exception as sync_exc:
                logger.error("[SyncOrchestrator] Falha de processamento na execução: %s", sync_exc)
                # O status do job e do tenant já foi atualizado pelo sync_tenant_database/SyncEngine em caso de erro

            # Atualiza o tempo final e logs
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info("[SyncOrchestrator] Job %s finalizado em %.2f ms", job_id, elapsed_ms)
            return job_id

    async def _run_sync_with_db_context(self, tenant_id: uuid.UUID) -> None:
        """Abre contexto de banco e executa a sincronização."""
        from services.sync_service import sync_tenant_database
        async with get_db_context() as session:
            await sync_tenant_database(tenant_id, session)

    async def check_and_trigger_scheduled_syncs(self) -> None:
        """
        Método de batimento periódico que varre os tenants ativos
        e decide se dispara a execução de sincronização para o minuto atual.
        """
        async with get_db_context() as db_session:
            stmt = select(Tenant).where(Tenant.ativo.is_(True))
            res = await db_session.execute(stmt)
            tenants = res.scalars().all()

        for tenant in tenants:
            config = tenant.sync_config or {}
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except Exception:
                    config = {}

            if config.get("enabled", False):
                local_time = self._get_localized_time(config.get("timezone", "America/Sao_Paulo"))
                if self.should_trigger_sync(config, local_time):
                    logger.info(
                        "[SyncOrchestrator] Horário agendado correspondente detectado (%s) no fuso %s para o tenant %s. Disparando sync...",
                        local_time.strftime("%H:%M"),
                        config.get("timezone", "America/Sao_Paulo"),
                        tenant.nome
                    )
                    # Dispara em background para não travar o loop principal do scheduler
                    asyncio.create_task(self.execute_scheduled_sync(tenant.id))

    # ── APIs para Dashboard Administrativo ─────────────────────────────────

    async def get_admin_dashboard_metrics(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        """
        Prover estatísticas completas e consolidadas para futuras telas administrativas.
        """
        async with get_db_context() as session:
            # 1. Histórico de execuções
            stmt_hist = select(SyncQueue).where(
                SyncQueue.tenant_id == tenant_id
            ).order_by(SyncQueue.criado_em.desc()).limit(20)
            res_hist = await session.execute(stmt_hist)
            jobs = res_hist.scalars().all()

            # 2. Configurações do tenant
            stmt_t = select(Tenant).where(Tenant.id == tenant_id)
            res_t = await session.execute(stmt_t)
            tenant = res_t.scalar_one_or_none()

        if not tenant:
            return {}

        sync_config = tenant.sync_config or {}
        if isinstance(sync_config, str):
            try:
                sync_config = json.loads(sync_config)
            except Exception:
                sync_config = {}

        last_sync = sync_config.get("last_sync")
        last_status = sync_config.get("last_sync_status", "N/A")
        
        # 3. Calcula Próxima Sincronização
        next_sync = self.calculate_next_run(sync_config)

        # 4. Estatísticas agregadas de performance
        durations = [float(j.tempo_duracao_ms) for j in jobs if j.status == "SUCCESS"]
        avg_duration_ms = sum(durations) / len(durations) if durations else 0.0
        
        total_records = sum(j.quantidade_registros for j in jobs if j.status == "SUCCESS")

        # 5. Health do catálogo analítico
        health_summary = await catalog_api.summary(tenant_id)

        # Histórico formatado para o dashboard
        formatted_jobs = []
        for j in jobs:
            formatted_jobs.append({
                "id": str(j.id),
                "data": j.data_execucao.isoformat(),
                "hora": j.hora_execucao.strftime("%H:%M:%S"),
                "status": j.status,
                "duracao_ms": float(j.tempo_duracao_ms),
                "views": j.quantidade_views,
                "registros": j.quantidade_registros,
                "resultado": j.resultado,
                "erros": j.erros,
                "avisos": j.avisos,
            })

        return {
            "ultima_sincronizacao": last_sync,
            "ultima_sincronizacao_status": last_status,
            "proxima_sincronizacao": next_sync.isoformat() if next_sync else None,
            "tempo_medio_ms": round(avg_duration_ms, 2),
            "quantidade_total_registros": total_records,
            "health_score": health_summary.get("health_medio", 100.0),
            "alertas_ativos": health_summary.get("alertas_ativos", 0),
            "historico_fila": formatted_jobs,
        }

    def calculate_next_run(self, sync_config: dict) -> datetime | None:
        """Calcula o próximo horário agendado de acordo com a configuração."""
        if not sync_config.get("enabled", False) or not sync_config.get("times"):
            return None

        tz_name = sync_config.get("timezone", "America/Sao_Paulo")
        current_local = self._get_localized_time(tz_name)
        
        times_parsed = []
        for t_str in sync_config["times"]:
            try:
                h, m = map(int, t_str.split(":"))
                times_parsed.append((h, m))
            except Exception:
                pass
        
        if not times_parsed:
            return None

        # Ordena horários
        times_parsed.sort()
        days_enabled = sync_config.get("days_of_week")
        if days_enabled is not None and not isinstance(days_enabled, list):
            days_enabled = [int(days_enabled)]

        # Busca nos próximos 7 dias
        for day_offset in range(8):
            test_date = current_local + timedelta(days=day_offset)
            
            # Se tiver filtro de dia da semana, valida
            if days_enabled is not None and test_date.weekday() not in days_enabled:
                continue

            for h, m in times_parsed:
                candidate = test_date.replace(hour=h, minute=m, second=0, microsecond=0)
                if candidate > current_local:
                    return candidate

        return None


# Singleton export
sync_orchestrator = SyncOrchestrator()
