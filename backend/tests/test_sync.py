import pytest
import pytest_asyncio
import uuid
import re
import asyncio
import oracledb
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet

from main import app
from config import settings
from models.tenant import Tenant
from models.user import User
from models.view_catalog import ViewCatalog
from services.sync_service import sync_tenant_database
from services.postgresql_clone_service import get_clone_db_connection, release_clone_db_connection
from services.oracle_service import decrypt_connection_details

BASE_URL = "http://testserver/api/v1"


@pytest_asyncio.fixture
async def admin_client():
    """Retorna um cliente logado como ADMIN para teste de rotas."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE_URL
    ) as client:
        # Usa administrador tecnico sintetico, sem troca de senha obrigatoria.
        login_res = await client.post("/auth/login", json={
            "email": "technical.admin@lumina.internal",
            "password": "SyntheticUser@2026"
        })
        if login_res.status_code != 200:
            # Fallback para o admin padrão
            login_res = await client.post("/auth/login", json={
                "email": "admin@luminaai.demo",
                "password": "AdminLumina@2026"
            })
        
        token = login_res.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


@pytest.mark.asyncio(loop_scope="session")
async def test_database_sync_and_concurrency(admin_client: AsyncClient):
    """
    Testa de ponta a ponta a sincronização de views do Oracle para o Postgres Clone,
    incluindo locks de concorrência e o endpoint HTTP de sync manual.
    """
    # 1. Obter tenant e configurar clone_db_conn apontando para o próprio banco de testes
    match = re.match(
        r"postgresql\+asyncpg://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)",
        settings.DATABASE_URL
    )
    if match:
        user, password, host, port, database = match.groups()
        port = int(port) if port else 5432
    else:
        user, password, host, port, database = "postgres", "postgres", "localhost", 5432, "luminaai_test"

    clone_details = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database
    }
    
    # Criptografa credenciais do clone
    f = Fernet(settings.ENCRYPTION_KEY.encode("utf-8"))
    encrypted_clone = f.encrypt(json.dumps(clone_details).encode("utf-8")).decode("utf-8")
    
    # Criptografa credenciais do oracle (fictícias)
    oracle_details = {
        "host": "localhost",
        "port": 1521,
        "user": "oracle_user",
        "password": "oracle_password",
        "sid": "XE"
    }
    encrypted_oracle = f.encrypt(json.dumps(oracle_details).encode("utf-8")).decode("utf-8")

    # Injeta credenciais de teste no tenant do banco
    tenant_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as db_session:
        stmt = select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        res = await db_session.execute(stmt)
        tenant = res.scalar_one_or_none()
        
        tenant.clone_db_conn = {
            "encrypted": True,
            "algorithm": "Fernet",
            "payload": encrypted_clone
        }
        tenant.oracle_conn = {
            "encrypted": True,
            "algorithm": "Fernet",
            "payload": encrypted_oracle
        }
        # O baseline usa VW_VENDAS_LM como view SQL deterministica. Este teste
        # sincroniza a view dedicada de performance para exercitar o swap de
        # tabelas sem alterar a fonte analitica compartilhada pelo baseline.
        await db_session.execute(
            delete(ViewCatalog).where(
                ViewCatalog.tenant_id == tenant.id,
                ViewCatalog.nome_view_oracle == "VW_VENDAS_LM",
            )
        )
        db_session.add(tenant)
        await db_session.commit()

    # 2. Mockar o banco Oracle (fonte)
    mock_oracle_conn = MagicMock()
    mock_cursor = MagicMock()
    
    mock_oracle_conn.close = AsyncMock()
    mock_cursor.close = AsyncMock()
    
    has_data = True
    async def mock_execute(*args, **kwargs):
        nonlocal has_data
        has_data = True

    async def mock_fetchmany(size=2000):
        nonlocal has_data
        if has_data:
            has_data = False
            return [(1, "trimestre", 250000.0, datetime(2024, 6, 1))]
        return []

    mock_cursor.execute = mock_execute
    mock_cursor.fetchmany = mock_fetchmany
    
    mock_cursor.description = [
        ("id", oracledb.DB_TYPE_NUMBER),
        ("periodo", oracledb.DB_TYPE_VARCHAR),
        ("receita", oracledb.DB_TYPE_NUMBER),
        ("data_ref", oracledb.DB_TYPE_DATE)
    ]
    mock_oracle_conn.cursor = MagicMock(return_value=mock_cursor)
    
    # Executa a sincronização usando o mock
    with patch("services.sync_service.get_oracle_connection", return_value=mock_oracle_conn):
        async with AsyncSessionLocal() as db_session:
            await sync_tenant_database(tenant_id, db_session)
            
            # Confere se os metadados do tenant foram salvos com sucesso
            stmt = select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
            res = await db_session.execute(stmt)
            tenant = res.scalar_one_or_none()
            
            sync_config_dict = tenant.sync_config
            if isinstance(sync_config_dict, str):
                sync_config_dict = json.loads(sync_config_dict)
            assert sync_config_dict["last_sync_status"] == "success"
            assert "Sincronização concluída com sucesso" in sync_config_dict["last_sync_message"]

    # 3. Testar controle de concorrência a nível de serviço
    async def delayed_sync():
        async with AsyncSessionLocal() as db_session:
            # Patcheamos get_oracle_connection para simular lentidão
            async def slow_conn(*args, **kwargs):
                await asyncio.sleep(2)
                return mock_oracle_conn
            with patch("services.sync_service.get_oracle_connection", side_effect=slow_conn):
                try:
                    await sync_tenant_database(tenant_id, db_session)
                except Exception:
                    pass

    # Dispara a primeira sincronização lenta em background
    task1 = asyncio.create_task(delayed_sync())
    await asyncio.sleep(0.2)  # Aguarda o registro do lock
    
    # A segunda deve falhar imediatamente com erro de concorrência
    async with AsyncSessionLocal() as db_session:
        with pytest.raises(RuntimeError) as exc_info:
            await sync_tenant_database(tenant_id, db_session)
        assert "Sincronização já em andamento" in str(exc_info.value)
        
    await task1  # Aguarda a finalização da task lenta

    # 4. Testar a rota POST /sync-now do endpoint HTTP
    with patch("services.sync_service.get_oracle_connection", return_value=mock_oracle_conn):
        res = await admin_client.post("/tenant/sync-now")
        assert res.status_code == 200
        assert res.json()["success"] is True

    # Testar conflito concorrente via HTTP (retorno 409)
    async def run_http_sync():
        async def slow_conn(*args, **kwargs):
            await asyncio.sleep(2)
            return mock_oracle_conn
        with patch("services.sync_service.get_oracle_connection", side_effect=slow_conn):
            return await admin_client.post("/tenant/sync-now")
            
    task_http1 = asyncio.create_task(run_http_sync())
    await asyncio.sleep(0.5)  # Dá tempo do primeiro request travar no socket lento
    
    # O segundo request concorrente deve falhar imediatamente com HTTP 409
    res_http2 = await admin_client.post("/tenant/sync-now")
    assert res_http2.status_code == 409
    assert "Sincronização já em andamento" in res_http2.json()["error"]["message"]
    
    try:
        await task_http1
    except Exception:
        pass
