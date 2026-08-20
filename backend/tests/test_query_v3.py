"""
LuminaAI — Testes de Integração de Consulta e Segurança v3.0

Valida:
  1. Login e liberação de troca de senha inicial.
  2. Queries livres de vendas válidas (com mock de IA).
  3. Respostas textuais diretas da IA (sem dados).
  4. Bloqueio de escopo (salários, dados médicos, etc.).
  5. Prevenção contra injeção SQL/Prompt nos parâmetros livres.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from database import get_db
from models.user import User
from models.tenant import Tenant
from models.view_catalog import ViewCatalog
from services.ai_service import IntentionResponse

BASE_URL = "http://testserver/api/v1"


@pytest_asyncio.fixture
async def test_client():
    """Retorna um cliente HTTP assíncrono para testar a aplicação FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE_URL
    ) as client:
        yield client


@pytest.mark.asyncio(loop_scope="session")
async def test_query_engine_v3_flow(test_client: AsyncClient):
    from unittest.mock import patch, AsyncMock
    patcher_qie = patch("services.query_intelligence_engine.QueryIntelligenceEngine.get_similarity_score", return_value=(0.0, None))
    patcher_qie.start()
    
    mock_find_pkg = AsyncMock(return_value=(None, 0.0))
    patcher_pkg = patch("services.data_platform.package_compatibility.package_compatibility_engine.find_compatible_package", mock_find_pkg)
    patcher_pkg.start()
    # ── 1. Login com a senha padrão e redefinição obrigatória ──
    login_payload = {
        "email": "admin@luminaai.demo",
        "password": "AdminLumina@2026"
    }
    response = await test_client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Redefine a senha para sair da trava de PASSWORD_CHANGE_REQUIRED
    res_change = await test_client.post("/auth/change-password", json={
        "old_password": "AdminLumina@2026",
        "new_password": "NovaSenhaAdmin@2026"
    }, headers=headers)
    assert res_change.status_code == 200

    # Faz login novamente com a nova senha
    login_payload["password"] = "NovaSenhaAdmin@2026"
    response = await test_client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Obtém dados do Tenant para o payload
    res_tenant = await test_client.get("/tenant/settings", headers=headers)
    assert res_tenant.status_code == 200
    tenant_data = res_tenant.json()
    tenant_id = tenant_data["id"]

    # Popula o catálogo com as views de vendas para o banco de teste
    from database import AsyncSessionLocal
    target_tenant_uuid = uuid.UUID(tenant_id)
    async with AsyncSessionLocal() as db_sess:
        # Cria as views de vendas de teste se não existirem
        from models.view_catalog import ChartType
        views_to_create = [
            {
                "nome": "VW_PERFORMANCE_VENDEDORES",
                "tipo": ChartType.BAR,
                "desc": "Performance de vendedores por meta"
            },
            {
                "nome": "VW_VENDAS_CONTEXTO_GERAL",
                "tipo": ChartType.TABLE,
                "desc": "Tabela de vendas gerais"
            }
        ]
        
        performance_view_id = None
        vendas_view_id = None
        
        for vdef in views_to_create:
            # Verifica se já existe
            stmt_existing = select(ViewCatalog).where(
                ViewCatalog.nome_view_oracle == vdef["nome"],
                ViewCatalog.tenant_id == target_tenant_uuid
            )
            res_exist = await db_sess.execute(stmt_existing)
            existing_view = res_exist.scalar_one_or_none()
            
            if existing_view:
                existing_view.tipo_grafico_padrao = vdef["tipo"]
                existing_view.ativo = True  # Garante que a view está ativa para o pipeline
                db_sess.add(existing_view)
                if vdef["nome"] == "VW_PERFORMANCE_VENDEDORES":
                    performance_view_id = existing_view.id
                else:
                    vendas_view_id = existing_view.id
            else:
                view = ViewCatalog(
                    tenant_id=target_tenant_uuid,
                    nome_view_oracle=vdef["nome"],
                    descricao_para_ia=vdef["desc"],
                    tipo_grafico_padrao=vdef["tipo"],
                    parametros_schema={"limite": {"type": "number", "required": False}},
                    ativo=True
                )
                db_sess.add(view)
                await db_sess.flush() # Atribui o ID
                if vdef["nome"] == "VW_PERFORMANCE_VENDEDORES":
                    performance_view_id = view.id
                else:
                    vendas_view_id = view.id
                    
        await db_sess.commit()

    # ── 2. Teste: Consulta Válida (Deve retornar mock do Oracle/Clone) ──
    mock_intention_valid = IntentionResponse(
        view_catalog_id=performance_view_id,
        confianca=0.95,
        parametros={"vendedor_nome": "Marcos", "mes": "6"},
        justificativa="Performance de vendas do Marcos em junho.",
        fora_de_escopo=False,
        operacao="SOMA",
        entidade_alvo="VENDEDOR",
        quantidade_limite=None,
        periodo_referencia="MES_PASSADO",
        is_comparacao=False,
        nivel_confianca="ALTA",
        chart_type_sobrescrever="BAR"
    )

    with patch("routers.query.identify_intention", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = [mock_intention_valid]
        
        res_query = await test_client.post("/query/", json={
            "pergunta": "Como foi a performance do Marcos em junho?",
            "tenant_id": tenant_id
        }, headers=headers)
        
        assert res_query.status_code == 200, res_query.text
        query_res = res_query.json()
        assert query_res["view_catalog_id"] == str(performance_view_id)
        assert query_res["chart_type"] == "BAR"
        assert "datasets" in query_res["chart_data"]
        assert query_res["parametros_extraidos"]["vendedor_nome"] == "Marcos"
        assert "plano_nlu" in query_res
        assert len(query_res["plano_nlu"]) == 1
        assert query_res["plano_nlu"][0]["operacao"] == "SOMA"
        assert query_res["plano_nlu"][0]["entidade_alvo"] == "VENDEDOR"
        assert "plano_execucao" in query_res
        assert query_res["plano_execucao"]["consulta_principal"]["view_name"] == "VW_PERFORMANCE_VENDEDORES"
        assert query_res["plano_execucao"]["consulta_principal"]["prioridade"] == "ALTA"

    # ── 3. Teste: Resposta Direta (Perguntas conceituais sem dados) ──
    mock_intention_direct = IntentionResponse(
        view_catalog_id=None,
        confianca=1.0,
        parametros={},
        justificativa="Pergunta conceitual simples.",
        fora_de_escopo=False,
        resposta_direta="Margem Bruta representa a lucratividade do produto...",
        operacao="RESUMO",
        entidade_alvo="MARGEM",
        nivel_confianca="ALTA"
    )

    with patch("routers.query.identify_intention", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = [mock_intention_direct]
        
        res_query = await test_client.post("/query/", json={
            "pergunta": "como calcular margem bruta?",
            "tenant_id": tenant_id
        }, headers=headers)
        
        assert res_query.status_code == 200
        query_res = res_query.json()
        assert query_res["view_catalog_id"] is None
        assert query_res["resposta_direta"] == mock_intention_direct.resposta_direta
        assert query_res["chart_data"]["resposta_direta"] == mock_intention_direct.resposta_direta
        assert "plano_nlu" in query_res
        assert query_res["plano_nlu"][0]["operacao"] == "RESUMO"
        assert "plano_execucao" in query_res
        assert query_res["plano_execucao"]["consulta_principal"]["sugestao_visualizacao"] == "KPI"

    # ── 4. Teste: Fora de Escopo (Deve ser bloqueada pelo Context Guard) ──
    mock_intention_blocked = IntentionResponse(
        view_catalog_id=None,
        confianca=0.0,
        parametros={},
        justificativa="Dados salariais solicitados.",
        fora_de_escopo=True,
        mensagem_bloqueio="Esta consulta está fora do escopo de vendas.",
        operacao="DETALHAMENTO",
        entidade_alvo="RECEITA",
        nivel_confianca="BAIXA"
    )

    with patch("routers.query.identify_intention", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = [mock_intention_blocked]
        
        res_query = await test_client.post("/query/", json={
            "pergunta": "Qual é o salário da secretária?",
            "tenant_id": tenant_id
        }, headers=headers)
        
        assert res_query.status_code == 403
        assert "escopo" in res_query.json()["error"]["message"].lower()

    # ── 5. Teste: Prompt/SQL Injection (Deve ser bloqueado pelo Context Guard) ──
    mock_intention_injection = IntentionResponse(
        view_catalog_id=vendas_view_id,
        confianca=0.90,
        parametros={"cliente_nome": "Maria; DROP TABLE users;--"},
        justificativa="Lista de compras da cliente Maria.",
        fora_de_escopo=False,
        operacao="LISTAGEM",
        entidade_alvo="CLIENTE",
        nivel_confianca="ALTA"
    )

    with patch("routers.query.identify_intention", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = [mock_intention_injection]
        
        res_query = await test_client.post("/query/", json={
            "pergunta": "Compras da Maria",
            "tenant_id": tenant_id
        }, headers=headers)
        
        assert res_query.status_code == 403
        assert "fora do escopo autorizado" in res_query.json()["error"]["message"].lower()

    # ── 6. Teste: Sobrescrita de Gráfico e Múltiplas Visualizações ──
    print("\n[TEST] 6. Testando sobrescrita de gráfico e geração de múltiplas visualizações...")
    mock_intention_multi = IntentionResponse(
        view_catalog_id=performance_view_id,
        confianca=0.98,
        parametros={"vendedor_nome": "Carlos"},
        justificativa="Usuário deseja ver performance do Carlos em tabela e barras.",
        fora_de_escopo=False,
        chart_type_sobrescrever="TABLE", # sobrescreve padrão BAR para TABLE
        chart_types_solicitados=["BAR", "TABLE"], # pede ambos
        operacao="RANKING",
        entidade_alvo="VENDEDOR",
        nivel_confianca="ALTA"
    )

    with patch("routers.query.identify_intention", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = [mock_intention_multi]
        
        res_query = await test_client.post("/query/", json={
            "pergunta": "Performance do Carlos em barras e tabela",
            "tenant_id": tenant_id
        }, headers=headers)
        
        assert res_query.status_code == 200, res_query.text
        query_res = res_query.json()
        
        # O gráfico principal legado deve ser TABLE (sobrescrito)
        assert query_res["chart_type"] == "TABLE"
        
        # A lista de visualizações múltiplas deve ter pelo menos 2 itens: BAR e TABLE
        assert "visualizations" in query_res
        visualizations = query_res["visualizations"]
        assert len(visualizations) >= 2
        assert visualizations[0]["chart_type"] == "TABLE"
        assert visualizations[1]["chart_type"] == "BAR"
        assert "rows" in visualizations[0]["chart_data"] # formato de tabela
        assert "datasets" in visualizations[1]["chart_data"] # formato de barras
        print("   [OK] SUCESSO: Sobrescrita de grafico e multiplas visualizacoes validadas!")
    patcher_qie.stop()

    # ── 7. Teste: Validação do Prompt Builder com Schema de Parâmetros ──
    print("\n[TEST] 7. Testando injeção de schemas de parâmetros no prompt do Motor de IA...")
    from services.ai_service import _build_system_prompt
    from schemas.view_catalog import ViewCatalogSummary
    
    view_summary = ViewCatalogSummary(
        id=performance_view_id,
        nome_view_oracle="VW_PERFORMANCE_VENDEDORES",
        descricao_para_ia="Visão de performance",
        tipo_grafico_padrao="BAR",
        parametros_schema={"mes": {"type": "number"}, "ano": {"type": "number"}} # parâmetros declarados
    )
    
    prompt = _build_system_prompt([view_summary])
    # Deve conter os parâmetros declarados formatados
    assert "['mes', 'ano']" in prompt or "mes" in prompt
    print("   [OK] SUCESSO: Schemas de parametros injetados no prompt da IA!")

