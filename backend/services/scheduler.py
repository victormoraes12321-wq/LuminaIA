import asyncio
import logging
from datetime import datetime
from sqlalchemy import select

from database import get_db_context
from models.tenant import Tenant
from services.sync_service import sync_tenant_database

logger = logging.getLogger("luminaai.scheduler")

# Cache global na memória para evitar execuções duplicadas no mesmo minuto
# Estrutura: { "tenant_id:HH:MM:YYYY-MM-DD": True }
_last_runs: dict[str, bool] = {}
_scheduler_task: asyncio.Task | None = None


async def run_sync_task(tenant_id) -> None:
    """Executa a sincronização do tenant em uma task assíncrona isolada utilizando o SyncOrchestrator."""
    try:
        from services.data_platform.sync_scheduler import sync_orchestrator
        await sync_orchestrator.execute_scheduled_sync(tenant_id, reason="Scheduler loop")
        from services.daily_reconciliation import daily_reconciliation_service
        reconciliation = await daily_reconciliation_service.run_for_tenant(tenant_id)
        logger.info("Reconciliacao diaria do tenant %s: %s", tenant_id, reconciliation.get("status"))
    except Exception as exc:
        logger.error("Falha no agendador ao sincronizar o tenant %s: %s", tenant_id, exc)


async def _scheduler_loop() -> None:
    """Loop principal do agendador executado a cada 60 segundos."""
    logger.info("⏰ Agendador de sincronização iniciado.")
    
    # Limpeza periódica do cache de runs antigas (uma vez ao dia)
    last_cleaned_date = datetime.now().strftime("%Y-%m-%d")
    
    from services.data_platform.sync_scheduler import sync_orchestrator

    while True:
        try:
            # 1. Limpeza do cache se virar o dia
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            if current_date != last_cleaned_date:
                global _last_runs
                # Remove chaves de datas anteriores
                _last_runs = {k: v for k, v in _last_runs.items() if current_date in k}
                last_cleaned_date = current_date
                logger.info("🧹 Cache do agendador limpo para o novo dia.")

            # 2. Varre os tenants e agenda execuções usando o SyncOrchestrator
            # (que possui validação avançada de fusos horários, dias da semana e concorrência)
            async with get_db_context() as session:
                stmt = select(Tenant).where(Tenant.ativo.is_(True))
                res = await session.execute(stmt)
                tenants = res.scalars().all()
                
                for tenant in tenants:
                    config = tenant.sync_config or {}
                    if isinstance(config, str):
                        try:
                            config = json.loads(config)
                        except Exception:
                            config = {}
                            
                    if config.get("enabled", False):
                        local_time = sync_orchestrator._get_localized_time(config.get("timezone", "America/Sao_Paulo"))
                        time_str = local_time.strftime("%H:%M")
                        
                        if sync_orchestrator.should_trigger_sync(config, local_time):
                            run_key = f"{tenant.id}:{time_str}:{current_date}"
                            
                            if run_key not in _last_runs:
                                _last_runs[run_key] = True
                                logger.info(
                                    "⏰ Horário correspondente detectado (%s) no fuso %s para o tenant %s. Iniciando...",
                                    time_str,
                                    config.get("timezone", "America/Sao_Paulo"),
                                    tenant.nome
                                )
                                # Dispara a sincronização em background para não travar o loop
                                asyncio.create_task(run_sync_task(tenant.id))

        except Exception as exc:
            logger.error("Erro crítico no loop do agendador: %s", exc)
            
        # Dorme por 60 segundos antes de verificar novamente
        await asyncio.sleep(60)


def start_scheduler() -> None:
    """Inicia a execução do agendador em background."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop())
        _scheduler_task.add_done_callback(_restart_scheduler_after_failure)
        logger.info("⏰ Agendador iniciado com sucesso.")


def _restart_scheduler_after_failure(task: asyncio.Task) -> None:
    """Restarts an unexpectedly terminated scheduler without masking shutdown cancellation."""
    if task.cancelled():
        return
    try:
        error = task.exception()
    except asyncio.CancelledError:
        return
    if error is None:
        return
    logger.error("Agendador encerrou inesperadamente; reinicio automatico em 5 segundos: %s", error)
    asyncio.get_running_loop().call_later(5, start_scheduler)


def get_scheduler_status() -> dict[str, object]:
    task = _scheduler_task
    return {
        "status": "healthy" if task is not None and not task.done() else "degraded",
        "running": bool(task is not None and not task.done()),
        "restart_policy": "automatic",
    }


async def stop_scheduler() -> None:
    """Interrompe e limpa a execução do agendador."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        logger.info("🛑 Parando o agendador de sincronização...")
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
        logger.info("⏰ Agendador desligado com sucesso.")
