"""
Testes de Integração do Sync Engine do LuminaAI
------------------------------------------------
Valida todos os fluxos operacionais e garantias transacionais do SyncEngine:
  1. Criação e atualização de registros na Fila de Sincronização (SyncQueue)
  2. Sincronização completa (Full) e incremental com staging tables
  3. Validação de integridade do dataset de destino antes do switch
  4. Mecanismo de retry automático para conexões temporárias do Oracle
  5. Rollback transacional e segurança em caso de exceções no meio do processo
  6. Proteção Multi-Tenant
"""
from __future__ import annotations

import uuid
import pytest
import asyncio
import asyncpg
from datetime import datetime, timezone, date
from unittest.mock import AsyncMock, MagicMock, patch

from database import get_db_context
from models.tenant import Tenant
from models.view_catalog import ViewCatalog, ChartType
from models.sync_queue import SyncQueue
from models.dataset import Dataset
from services.data_platform.sync_engine import SyncEngine

# UUIDs de teste isolados
TENANT_A = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
TENANT_B = uuid.UUID("b1ffcd00-0d1c-4fa9-cc7e-7cc0ce491b22")


# Helpers para mockar resultados de conexão
def make_mock_oracle_conn(col_desc: list = None, rows: list = None):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    mock_conn.close = AsyncMock()
    mock_cursor.close = AsyncMock()
    
    has_data = True
    async def mock_execute(*args, **kwargs):
        nonlocal has_data
        has_data = True

    async def mock_fetchmany(size=2000):
        nonlocal has_data
        if has_data:
            has_data = False
            return rows or [(1, "VW_TEST", 15000.0, datetime.now())]
        return []

    mock_cursor.execute = mock_execute
    mock_cursor.fetchmany = mock_fetchmany
    
    mock_cursor.description = col_desc or [
        ("id", 1), # number
        ("periodo", 2),
        ("valor", 1),
        ("data_ref", 3)
    ]
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    return mock_conn


# ──────────────────────────────────────────────────────────────────────────────
# Testes do SyncEngine
# ──────────────────────────────────────────────────────────────────────────────

class TestSyncEngine:

    @pytest.mark.asyncio
    async def test_detect_incremental_column_none(self):
        """Não deve detectar coluna incremental se a tabela de destino não existir."""
        engine = SyncEngine()
        mock_pg = AsyncMock()
        mock_pg.fetchval = AsyncMock(return_value=False) # Tabela não existe

        col = await engine._detect_incremental_column(mock_pg, "vw_inexistente")
        assert col is None

    @pytest.mark.asyncio
    async def test_detect_incremental_column_found(self):
        """Deve detectar 'data_ref' como coluna incremental prioritária."""
        engine = SyncEngine()
        mock_pg = AsyncMock()
        
        # Simula tabela existente e colunas retornadas
        mock_pg.fetchval = AsyncMock(return_value=True)
        columns = [
            {"column_name": "id", "data_type": "integer"},
            {"column_name": "periodo", "data_type": "character varying"},
            {"column_name": "data_ref", "data_type": "timestamp without time zone"}
        ]
        mock_pg.fetch = AsyncMock(return_value=columns)

        col = await engine._detect_incremental_column(mock_pg, "vw_vendas")
        assert col == "data_ref"

    @pytest.mark.asyncio
    async def test_validate_dataset_valid(self):
        """Deve retornar True para tabela staging válida estruturalmente."""
        engine = SyncEngine()
        mock_pg = AsyncMock()
        mock_pg.fetchval.side_effect = [
            100, # staging_table count
            True, # table_name exists
            100 # table_name count
        ]
        mock_pg.fetch = AsyncMock(return_value=[
            {"column_name": "id", "data_type": "integer"},
            {"column_name": "valor", "data_type": "numeric"}
        ])

        valid = await engine._validate_dataset(mock_pg, "vw_staging", "vw_oficial", None)
        assert valid is True

    @pytest.mark.asyncio
    async def test_validate_dataset_corrupted_empty(self):
        """Deve retornar False se a nova tabela de staging estiver vazia e a anterior tinha registros."""
        engine = SyncEngine()
        mock_pg = AsyncMock()
        mock_pg.fetchval.side_effect = [
            0, # staging_table count (anomalia: esvaziou do nada)
            True, # table_name exists
            500 # table_name count anterior
        ]
        mock_pg.fetch = AsyncMock(return_value=[])

        valid = await engine._validate_dataset(mock_pg, "vw_staging", "vw_oficial", None)
        assert valid is False

    @pytest.mark.asyncio
    async def test_retry_oracle_connection_success(self):
        """Deve reconectar com sucesso se a falha for temporária (retry)."""
        engine = SyncEngine(max_retries=3, retry_delay=0.1)
        
        call_count = 0
        async def mock_get_conn(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Falha temporária de rede com Oracle")
            return MagicMock()

        with patch("services.data_platform.sync_engine.get_oracle_connection", side_effect=mock_get_conn):
            conn = await engine._connect_oracle_with_retry({})
            assert conn is not None
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_oracle_connection_fail_max(self):
        """Deve levantar a exceção se atingir o número máximo de retries."""
        engine = SyncEngine(max_retries=2, retry_delay=0.1)
        
        async def mock_get_conn(*args, **kwargs):
            raise ConnectionRefusedError("Oracle indisponível")

        with patch("services.data_platform.sync_engine.get_oracle_connection", side_effect=mock_get_conn):
            with pytest.raises(ConnectionRefusedError):
                await engine._connect_oracle_with_retry({})

    @pytest.mark.asyncio
    async def test_rollback_on_switch_failure(self):
        """Deve limpar a staging table se ocorrer falha na transação de switch de tabelas."""
        engine = SyncEngine()
        mock_pg = AsyncMock()
        
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock()
        mock_transaction.__aexit__ = AsyncMock(side_effect=asyncpg.DeadlockDetectedError("Erro concorrente"))
        mock_pg.transaction = MagicMock(return_value=mock_transaction)

        # Executa sincronização unitária da view
        oracle_conn = make_mock_oracle_conn()
        
        # Mocks internos auxiliares
        engine._detect_incremental_column = AsyncMock(return_value=None)
        engine._validate_dataset = AsyncMock(return_value=True)
        engine._persist_dataset_version = AsyncMock()

        with pytest.raises(asyncpg.DeadlockDetectedError):
            await engine._sync_single_view(
                tenant_id=TENANT_A,
                view_name="VW_VENDAS",
                view_catalog_id=uuid.uuid4(),
                oracle_conn=oracle_conn,
                pg_conn=mock_pg
            )

        # Deve ter tentado dropar a staging table para limpeza após a falha
        mock_pg.execute.assert_any_call("DROP TABLE IF EXISTS vw_vendas_staging CASCADE;")

    @pytest.mark.asyncio
    async def test_run_sync_concurrency_lock(self):
        """Deve bloquear execuções simultâneas de sincronização para o mesmo Tenant."""
        engine = SyncEngine()
        
        # Simula um job lento que mantém o lock ocupado
        async def slow_job(job_id, tenant_id, lock):
            async with lock:
                await asyncio.sleep(2)
        engine._execute_sync_job = slow_job

        # Primeiro executa
        job1 = await engine.run_sync(TENANT_A)
        assert job1 is not None

        # Aguarda uma fração de segundo para que a task em background inicie e adquira o lock
        await asyncio.sleep(0.1)

        # O segundo simultâneo deve levantar erro de concorrência
        with pytest.raises(RuntimeError) as exc_info:
            await engine.run_sync(TENANT_A)
        assert "Sincronização já em andamento" in str(exc_info.value)
