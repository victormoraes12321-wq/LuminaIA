import pytest
import pytest_asyncio
import json
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status
from httpx import AsyncClient, ASGITransport

from main import app

BASE_URL = "http://testserver/api/v1"

@pytest_asyncio.fixture
async def admin_client():
    """Retorna um cliente logado como ADMIN para teste de rotas."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE_URL
    ) as client:
        login_res = await client.post("/auth/login", json={
            "email": "ti@casadocampo.vet.br",
            "password": "H0llyw00d26"
        })
        if login_res.status_code != 200:
            login_res = await client.post("/auth/login", json={
                "email": "admin@luminaai.demo",
                "password": "AdminLumina@2026"
            })
        
        token = login_res.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client

@pytest.mark.anyio
async def test_sync_now_production_restrictions(admin_client: AsyncClient):
    """
    Valida que em produção a rota /sync-now bloqueia sincronizações manuais
    fora das janelas programadas configuradas no tenant.
    """
    from config import settings
    from database import get_db_context
    from models.tenant import Tenant
    from models.user import User
    
    tenant_id = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
    
    # Mock do objeto Tenant e sua configuração de sync
    mock_sync_config = {
        "enabled": True,
        "timezone": "America/Sao_Paulo",
        "times": ["02:00", "04:00"], # Horários agendados
        "days_of_week": [0, 1, 2, 3, 4, 5, 6]
    }
    
    # 1. Configura ambiente para produção
    with patch("config.settings.ENVIRONMENT", "production"):
        # Força o get_db a retornar o tenant ou o user dependendo do modelo na query
        db_mock = MagicMock()
        
        tenant_mock = Tenant(
            id=tenant_id,
            nome="Empresa Teste Restricoes",
            ativo=True,
            sync_config=json.dumps(mock_sync_config),
            oracle_conn="{}",
            clone_db_conn="{}"
        )
        
        user_mock = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email="ti@casadocampo.vet.br",
            role="ADMIN",
            must_change_password=False,
            ativo=True
        )
        
        # Executando queries simuladas com base na entidade do SQLAlchemy
        async def mock_execute(stmt, *args, **kwargs):
            scalar_mock = MagicMock()
            
            # Inspeciona a entidade selecionada no statement
            try:
                entity = stmt.column_descriptions[0]["entity"]
            except Exception:
                entity = None
                
            if entity == Tenant:
                scalar_mock.scalar_one_or_none.return_value = tenant_mock
                scalar_mock.scalars.return_value.all.return_value = [tenant_mock]
            else:
                scalar_mock.scalar_one_or_none.return_value = user_mock
                scalar_mock.scalars.return_value.all.return_value = [user_mock]
                
            return scalar_mock

        db_mock.execute = mock_execute
        
        # Override do Depends(get_db) para injetar o mock
        from database import get_db
        
        async def override_db():
            yield db_mock
            
        app.dependency_overrides[get_db] = override_db
        
        try:
            # Chama a rota /tenant/sync-now
            res = await admin_client.post("/tenant/sync-now")
            
            # Deve ser rejeitado (HTTP 400) pois o horário atual (ex: 10:14) não é 02:00 nem 04:00
            assert res.status_code == status.HTTP_400_BAD_REQUEST
            assert "Operação rejeitada" in res.json()["error"]["message"]
            
        finally:
            # Limpa dependências overrides
            app.dependency_overrides.pop(get_db, None)
