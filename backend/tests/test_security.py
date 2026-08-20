import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from main import app
from config import settings
from models.user import User
from database import AsyncSessionLocal

BASE_URL = "http://testserver/api/v1"


@pytest_asyncio.fixture
async def admin_client():
    """Retorna um cliente logado como ADMIN para teste de rotas de segurança."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE_URL
    ) as client:
        # Login com administrador tecnico totalmente sintetico.
        login_res = await client.post("/auth/login", json={
            "email": "technical.admin@lumina.internal",
            "password": "SyntheticUser@2026"
        })
        assert login_res.status_code == 200, f"Falha ao autenticar admin de testes: {login_res.text}"
        token = login_res.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


@pytest.mark.asyncio(loop_scope="session")
async def test_cross_tenant_user_creation(admin_client: AsyncClient):
    """
    Testa se um administrador autenticado em um tenant é bloqueado 
    ao tentar cadastrar um usuário em outro tenant (Prevenção Cross-Tenant).
    """
    other_tenant_id = str(uuid.uuid4())
    
    payload = {
        "nome": "Usuário Infiltrado",
        "email": "infiltrado@outrotenant.com",
        "role": "CONSULTA",
        "tenant_id": other_tenant_id
    }
    
    res = await admin_client.post("/users/", json=payload)
    assert res.status_code == 403
    assert "Acesso negado" in res.json()["error"]["message"]


@pytest.mark.asyncio(loop_scope="session")
async def test_invalid_view_name_registration(admin_client: AsyncClient):
    """
    Testa se o schema Pydantic do Catálogo bloqueia nomes de view Oracle inválidos 
    contendo caracteres especiais e SQL Injection (ex: ponto e vírgula, espaços, etc.).
    """
    payload_sql_injection = {
        "nome_view_oracle": "VW_VENDAS; DROP TABLE USERS; --",
        "descricao_para_ia": "View de vendas mensais com injeção de DDL para teste de segurança.",
        "tipo_grafico_padrao": "BAR",
        "parametros_schema": {}
    }
    
    res = await admin_client.post("/catalog/", json=payload_sql_injection)
    # Deve falhar na validação do Pydantic (HTTP 422 Unprocessable Entity)
    assert res.status_code == 422
    # Confere se a falha é relacionada à validação de regex pattern do campo
    errors = res.json()["detail"]
    assert any("nome_view_oracle" in err["loc"] for err in errors)


@pytest.mark.asyncio(loop_scope="session")
async def test_master_password_debug_disabled(admin_client: AsyncClient):
    """
    Testa se a senha backdoor "AdminLumina@2026" foi completamente desativada, 
    mesmo quando simulamos que o ambiente está com a flag DEBUG ativa.
    """
    # Patcheamos a flag DEBUG para True para simular o comportamento de desenvolvimento
    with patch("config.settings.DEBUG", True):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=BASE_URL
        ) as client:
            # Tenta logar no admin com a senha mestra backdoor desativada
            res = await client.post("/auth/login", json={
                "email": "technical.admin@lumina.internal",
                "password": "AdminLumina@2026"
            })
            # Deve ser rejeitado com 401 Unauthorized
            assert res.status_code == 401
            assert "E-mail ou senha incorretos" in res.json()["error"]["message"]
