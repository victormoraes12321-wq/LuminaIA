"""
Testes de Integração e Unitários do Sync Scheduler (Sync Orchestrator)
---------------------------------------------------------------------
Valida as políticas de agendamento, controle de concorrência, geração de fila,
logs de auditoria e cálculo de métricas para o Dashboard Administrativo.
"""
from __future__ import annotations

import uuid
import pytest
import asyncio
from datetime import datetime, timezone, date, time
from unittest.mock import AsyncMock, MagicMock, patch

from database import get_db_context
from models.tenant import Tenant
from models.sync_queue import SyncQueue
from models.view_catalog import ViewCatalog
from services.data_platform.sync_scheduler import SyncOrchestrator

# UUIDs de teste isolados
TENANT_A = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")


def make_mock_job(status: str = "SUCCESS", duration_ms: float = 5000.0, records: int = 200) -> MagicMock:
    j = MagicMock()
    j.id = uuid.uuid4()
    j.tenant_id = TENANT_A
    j.data_execucao = date.today()
    j.hora_execucao = time(12, 0)
    j.status = status
    j.tempo_duracao_ms = duration_ms
    j.quantidade_views = 3
    j.quantidade_registros = records
    j.resultado = "Sync finalizado"
    j.erros = []
    j.avisos = []
    return j


class TestSyncScheduler:

    def test_should_trigger_sync_enabled_and_time_match(self):
        """Deve retornar True se estiver ativo e o horário coincidir."""
        orchestrator = SyncOrchestrator()
        config = {
            "enabled": True,
            "times": ["08:00", "13:00", "18:00"],
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "timezone": "America/Sao_Paulo"
        }
        # Segunda-feira às 13:00
        current = datetime(2026, 7, 6, 13, 0)
        assert orchestrator.should_trigger_sync(config, current) is True

    def test_should_not_trigger_sync_disabled(self):
        """Não deve rodar se o agendamento estiver desativado."""
        orchestrator = SyncOrchestrator()
        config = {
            "enabled": False,
            "times": ["13:00"]
        }
        current = datetime(2026, 7, 6, 13, 0)
        assert orchestrator.should_trigger_sync(config, current) is False

    def test_should_not_trigger_sync_day_not_enabled(self):
        """Não deve rodar em dias da semana não permitidos."""
        orchestrator = SyncOrchestrator()
        config = {
            "enabled": True,
            "times": ["13:00"],
            "days_of_week": [0, 1, 2, 3, 4] # Apenas dias úteis
        }
        # Sábado às 13:00 (dia = 5)
        current = datetime(2026, 7, 11, 13, 0)
        assert orchestrator.should_trigger_sync(config, current) is False

    def test_calculate_next_run(self):
        """Deve calcular corretamente o próximo horário agendado de execução."""
        orchestrator = SyncOrchestrator()
        config = {
            "enabled": True,
            "times": ["08:00", "13:00"],
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "timezone": "America/Sao_Paulo"
        }
        # Simulando que a data atual local é às 10:00. Próxima deve ser 13:00
        with patch.object(orchestrator, "_get_localized_time", return_value=datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc)):
            next_run = orchestrator.calculate_next_run(config)
            assert next_run is not None
            assert next_run.hour == 13
            assert next_run.minute == 0

    def test_calculate_next_run_next_day(self):
        """Deve calcular para o próximo dia se todos os horários do dia atual já passaram."""
        orchestrator = SyncOrchestrator()
        config = {
            "enabled": True,
            "times": ["08:00"],
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "timezone": "America/Sao_Paulo"
        }
        # Simulando data atual local às 10:00. A próxima deve ser às 08:00 do dia seguinte (Terça-feira, 7 de Julho)
        with patch.object(orchestrator, "_get_localized_time", return_value=datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc)):
            next_run = orchestrator.calculate_next_run(config)
            assert next_run is not None
            assert next_run.day == 7
            assert next_run.hour == 8

    @pytest.mark.asyncio
    async def test_get_admin_dashboard_metrics(self):
        """Deve prover métricas consolidadas corretamente a partir dos jobs anteriores."""
        orchestrator = SyncOrchestrator()

        tenant = MagicMock()
        tenant.sync_config = {
            "enabled": True,
            "times": ["08:00", "13:00"],
            "timezone": "America/Sao_Paulo",
            "last_sync": "2026-07-06T13:00:00Z",
            "last_sync_status": "success"
        }

        jobs = [
            make_mock_job(status="SUCCESS", duration_ms=4000.0, records=100),
            make_mock_job(status="SUCCESS", duration_ms=6000.0, records=200),
            make_mock_job(status="FAILED", duration_ms=2000.0, records=0),
        ]

        # Mocks de banco de dados
        mock_result_jobs = MagicMock()
        mock_result_jobs.scalars.return_value.all.return_value = jobs
        mock_result_tenant = MagicMock()
        mock_result_tenant.scalar_one_or_none.return_value = tenant

        mock_session = AsyncMock()
        mock_session.execute.side_effect = [mock_result_jobs, mock_result_tenant]

        with patch("services.data_platform.sync_scheduler.get_db_context") as mock_ctx, \
             patch("services.data_platform.sync_scheduler.catalog_api.summary", return_value={"health_medio": 95.0, "alertas_ativos": 1}):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            metrics = await orchestrator.get_admin_dashboard_metrics(TENANT_A)

            assert metrics["ultima_sincronizacao"] == "2026-07-06T13:00:00Z"
            assert metrics["tempo_medio_ms"] == 5000.0 # Média dos dois com sucesso (4s + 6s) / 2
            assert metrics["quantidade_total_registros"] == 300
            assert metrics["health_score"] == 95.0
            assert len(metrics["historico_fila"]) == 3

    @pytest.mark.asyncio
    async def test_scheduler_loop_lock_global(self):
        """Deve impedir que duas execuções iniciem concorrentemente para o mesmo tenant."""
        orchestrator = SyncOrchestrator()
        
        # Simula lock já ocupado
        from services.data_platform.sync_scheduler import get_orchestrator_lock
        lock = await get_orchestrator_lock(TENANT_A)
        await lock.acquire()

        try:
            # Tenta executar a sincronização, deve retornar None imediatamente (bloqueado)
            job = await orchestrator.execute_scheduled_sync(TENANT_A, reason="Concorrência teste")
            assert job is None
        finally:
            # Libera o lock
            lock.release()
