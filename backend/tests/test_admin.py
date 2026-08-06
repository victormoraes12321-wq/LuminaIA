"""
LuminaAI — Testes de Integração do Painel Administrativo
-------------------------------------------------------
Valida todos os fluxos do painel administrativo:
  1. CRUD do Catálogo de Views (GET, POST, PUT, DELETE) com controle de papéis (ADMIN/GESTOR).
  2. Gerenciamento de Usuários (GET, DELETE, toggle-active) pelo ADMIN.
  3. Atualização de Configurações do Tenant e teste de conexão Oracle pelo ADMIN.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from main import app
from models.user import UserRole

BASE_URL = "http://testserver/api/v1"


@pytest_asyncio.fixture
async def admin_client():
    """Retorna um cliente logado como ADMIN após garantir a redefinição de senha via API."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        # 1. Tenta login com a nova senha
        login_res = await client.post("/auth/login", json={
            "email": "admin@luminaai.demo",
            "password": "NewAdminLumina@2026"
        })
        
        current_pwd = "NewAdminLumina@2026"
        if login_res.status_code != 200:
            # 2. Tenta login com a senha padrão
            current_pwd = "AdminLumina@2026"
            login_res = await client.post("/auth/login", json={
                "email": "admin@luminaai.demo",
                "password": current_pwd
            })
            
        assert login_res.status_code == 200, f"Login admin falhou: {login_res.status_code} - {login_res.text}"
        data = login_res.json()
        
        # 3. Se ainda precisa alterar a senha, chama /auth/change-password via API
        if data.get("must_change_password"):
            token = data["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            target_pwd = "NewAdminLumina@2026" if current_pwd == "AdminLumina@2026" else "AdminLumina@2026_alt"
            
            pwd_res = await client.post("/auth/change-password", json={
                "old_password": current_pwd,
                "new_password": target_pwd
            }, headers=headers)
            assert pwd_res.status_code == 200, f"Alteração de senha falhou: {pwd_res.status_code} - {pwd_res.text}"
            
            login_res = await client.post("/auth/login", json={
                "email": "admin@luminaai.demo",
                "password": target_pwd
            })
            assert login_res.status_code == 200, f"Re-login pós-senha falhou: {login_res.status_code} - {login_res.text}"

        token_final = login_res.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token_final}"})
        yield client



@pytest.mark.asyncio(loop_scope="session")
async def test_admin_users_flow(admin_client: AsyncClient):
    """Testa os endpoints de gerenciamento de usuários do tenant."""
    # ── Cenário 1: Listagem de Usuários ───────────────────────
    res = await admin_client.get("/users/")
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 1
    assert any(u["email"] == "admin@luminaai.demo" for u in users)

    # ── Cenário 2: Cadastro de Novo Usuário ────────────────────
    new_user_payload = {
        "nome": "Gestor de Teste",
        "email": "gestor.teste@luminaai.demo",
        "role": "GESTOR",
        "tenant_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    }
    create_res = await admin_client.post("/users/", json=new_user_payload)
    assert create_res.status_code == 201
    create_data = create_res.json()
    new_user_id = create_data["user"]["id"]
    
    # ── Cenário 3: Alternar Status Ativo ──────────────────────
    toggle_res = await admin_client.put(f"/users/{new_user_id}/toggle-active")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["ativo"] is False
    
    toggle_res2 = await admin_client.put(f"/users/{new_user_id}/toggle-active")
    assert toggle_res2.status_code == 200
    assert toggle_res2.json()["ativo"] is True

    # ── Cenário 4: Exclusão de Usuário ────────────────────────
    del_res = await admin_client.delete(f"/users/{new_user_id}")
    assert del_res.status_code == 204


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_catalog_flow(admin_client: AsyncClient):
    """Testa o CRUD do Catálogo de Views Oracle."""
    # ── Cenário 1: Cadastrar View ────────────────────────────
    catalog_payload = {
        "nome_view_oracle": "VW_TESTE_INTEGRACAO",
        "descricao_para_ia": "View de teste criada pelos testes de integracao do backend. Deve ser ignorada.",
        "tipo_grafico_padrao": "LINE",
        "parametros_schema": {"periodo": {"type": "string", "required": False}}
    }
    res_create = await admin_client.post("/catalog/", json=catalog_payload)
    assert res_create.status_code == 201
    view_data = res_create.json()
    view_id = view_data["id"]
    assert view_data["nome_view_oracle"] == "VW_TESTE_INTEGRACAO"
    
    # ── Cenário 2: Listar Views ──────────────────────────────
    res_list = await admin_client.get("/catalog/")
    assert res_list.status_code == 200
    views = res_list.json()
    assert any(v["id"] == view_id for v in views)
    
    # ── Cenário 3: Atualizar View ────────────────────────────
    update_payload = {
        "descricao_para_ia": "Nova descricao atualizada para os testes de integracao do backend.",
        "ativo": False
    }
    res_update = await admin_client.put(f"/catalog/{view_id}", json=update_payload)
    assert res_update.status_code == 200
    assert res_update.json()["ativo"] is False
    assert "Nova descricao atualizada" in res_update.json()["descricao_para_ia"]
    
    # ── Cenário 4: Deletar View ──────────────────────────────
    res_delete = await admin_client.delete(f"/catalog/{view_id}")
    assert res_delete.status_code == 204


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_tenant_settings(admin_client: AsyncClient):
    """Testa a leitura e alteração das configurações visuais/banco do Tenant."""
    # ── Cenário 1: Obter Configurações ───────────────────────
    res_get = await admin_client.get("/tenant/settings")
    assert res_get.status_code == 200
    settings = res_get.json()
    assert "nome" in settings
    # Aceita qualquer nome válido (o banco pode ter sido alterado por execuções anteriores dos testes)
    assert isinstance(settings["nome"], str) and len(settings["nome"]) > 0
    
    # ── Cenário 2: Atualizar Configurações ───────────────────
    update_payload = {
        "nome": "LuminaAI Test Corp",
        "logo_url": "https://cdn.luminaai.com/logos/test-corp.png",
        "tema_config": {
            "primary_color": "#FF00FF",
            "dark_mode": False
        },
        "ia_config": {
            "model": "gpt-4o",
            "temperature": 0.2,
            "api_key": "sk-proj-TESTKEY"
        },
        "oracle_conn": {
            "host": "localhost",
            "port": 1521,
            "user": "lumina_test",
            "password": "TestPassword@123",
            "sid": "XE"
        }
    }
    res_put = await admin_client.put("/tenant/settings", json=update_payload)
    assert res_put.status_code == 200
    assert res_put.json()["nome"] == "LuminaAI Test Corp"
    
    # ── Cenário 3: Validar Obtenção Pós-Atualização (Mapeamento/Mascara) ──
    res_get2 = await admin_client.get("/tenant/settings")
    assert res_get2.status_code == 200
    settings_new = res_get2.json()
    assert settings_new["nome"] == "LuminaAI Test Corp"
    assert settings_new["oracle_conn"]["password"] == "••••••••"
    assert "TKEY" in settings_new["ia_config"]["api_key"]

    
    # ── Cenário 4: Testar Conexão Oracle (deve usar o mock isolado) ──────
    test_conn_payload = {
        "host": "localhost",
        "port": 9999, # Porta inexistente para gerar timeout/erro rapido
        "user": "invalid_user",
        "password": "invalid_password",
        "sid": "XE"
    }
    res_test = await admin_client.post("/tenant/test-oracle", json=test_conn_payload)
    assert res_test.status_code == 200
    assert res_test.json()["success"] is True
    assert "Simulação" in res_test.json()["message"]

    # A senha mascarada também não pode provocar acesso à rede no ambiente de teste.
    test_conn_payload_masked = {
        "host": "localhost",
        "port": 9999,
        "user": "invalid_user",
        "password": "••••••••",
        "sid": "XE"
    }
    res_test_masked = await admin_client.post("/tenant/test-oracle", json=test_conn_payload_masked)
    assert res_test_masked.status_code == 200
    assert res_test_masked.json()["success"] is True

    # ── Cenário 5: Testar Conexão de IA (Deve falhar com chave inválida) ──
    test_ai_payload = {
        "id": "legacy-default",
        "model": "gpt-4o-mini",
        "api_key": "sk-proj-INVALID_KEY"
    }
    res_ai_test = await admin_client.post("/tenant/test-ai", json=test_ai_payload)
    assert res_ai_test.status_code == 400
    assert "Falha ao validar a chave de API da OpenAI" in res_ai_test.json()["error"]["message"]



@pytest.mark.asyncio(loop_scope="session")
async def test_admin_audit_logs(admin_client: AsyncClient):
    """Testa o endpoint de obtenção de logs de auditoria do tenant."""
    res = await admin_client.get("/tenant/audit-logs")
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    # Mesmo que esteja vazio no início do banco limpo, deve ser uma lista válida
    if len(logs) > 0:
        log = logs[0]
        assert "pergunta" in log
        assert "usuario" in log
        assert "email" in log["usuario"]
        assert "view" in log
