import pytest
import pytest_asyncio
import uuid
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from main import app
from services.query_intelligence_engine import query_intelligence_engine, BlueprintModel
from schemas.query import QueryRequest

BASE_URL = "http://testserver/api/v1"

@pytest_asyncio.fixture
async def test_client():
    """Retorna um cliente HTTP assíncrono para testar a aplicação FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE_URL
    ) as client:
        yield client

def test_qie_normalize_and_similarity():
    # 1. Test exact Jaccard matches (should be >= 95% similarity)
    score1, bp1 = query_intelligence_engine.get_similarity_score("quanto vendeu hoje", "tenant_id")
    assert score1 >= 0.95
    assert bp1 is not None
    assert bp1.intent_id == "daily_sales"

    score2, bp2 = query_intelligence_engine.get_similarity_score("quanto faturamos hoje", "tenant_id")
    assert score2 >= 0.95
    assert bp2 is not None
    assert bp2.intent_id == "daily_sales"

    # 2. Test Jaccard partial matches (should fall in 80%-94% range)
    score3, bp3 = query_intelligence_engine.get_similarity_score("qual produto vendeu mais ontem por vendedor", "tenant_id")
    assert 0.80 <= score3 <= 0.94
    assert bp3 is not None
    assert bp3.intent_id == "product_ranking"

    # 3. Test dissimilar queries (< 80% similarity)
    score4, bp4 = query_intelligence_engine.get_similarity_score("qual o salario dos vendedores", "tenant_id")
    assert score4 < 0.80

def test_qie_parameter_extraction():
    # Test date extraction
    params = query_intelligence_engine.extract_params_from_text("faturamento de hoje")
    assert "date_range" in params
    assert "2026-07-03" in params["date_range"]

    # Test names and dimensions extraction
    params2 = query_intelligence_engine.extract_params_from_text("vendas do vendedor Joao para geladeira na regiao sul")
    assert params2.get("vendedor_nome") == "João"
    assert params2.get("products") == ["geladeira"]
    assert params2.get("regions") == ["Sul"]

def test_blueprint_adaptation_and_evolution():
    # Get daily sales blueprint
    _, bp = query_intelligence_engine.get_similarity_score("quanto vendeu hoje", "tenant_id")
    assert bp is not None
    
    # 1. Adapt Blueprint (direct reuse)
    adapted = query_intelligence_engine.adapt_blueprint(bp, "vendas ontem do vendedor Joao")
    assert adapted.filters.get("vendedor_nome") == "João"
    assert "2026-07-02" in adapted.filters.get("date_range", "") # ontem relative to 2026-07-03
    assert adapted.version == 1  # version unchanged in direct reuse
    
    # 2. Evolve Blueprint (creating a new version)
    evolved = query_intelligence_engine.evolve_blueprint(bp, "quanto vendeu hoje por vendedor")
    assert evolved.version == 2
    assert "vendedor_nome" in evolved.group_by
    assert evolved.id == f"{bp.intent_id}_v2"
    assert any("bp_daily_sales_v1" in h for h in evolved.versionamento.historico)

@pytest.mark.asyncio
async def test_qie_router_integration(test_client: AsyncClient):
    # Perform login sequence to obtain auth headers
    login_payload = {
        "email": "admin@luminaai.demo",
        "password": "AdminLumina@2026"
    }
    response = await test_client.post("/auth/login", json=login_payload)
    token = response.json().get("access_token")
    if not token:
        # Se falhou, tenta com a senha alterada por outros testes
        login_payload["password"] = "NewAdminLumina@2026"
        response = await test_client.post("/auth/login", json=login_payload)
        token = response.json()["access_token"]
        
    headers = {"Authorization": f"Bearer {token}"}

    # Mock identify_intention to verify if it gets bypassed
    with patch("routers.query.identify_intention") as mock_nlu:
        # Envia uma pergunta que tem 100% de match de blueprint (deve ignorar NLU)
        response = await test_client.post(
            "/api/v1/query/",
            headers=headers,
            json={
                "pergunta": "quanto faturamos hoje",
                "tenant_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
            }
        )
        assert response.status_code == 200
        data = response.json()
        if (data.get("chart_data") or {}).get("catalog_gap"):
            assert data["view_name"] is None
            assert "vendas/faturamento" in (data.get("mensagem") or data.get("resposta_direta") or "")
        else:
            assert data["view_name"] == "VW_VENDAS_LM"
            assert "[Blueprint Reutilizado]" in data["ia_justificativa"]
        
        # Catalog guard or safe blueprint reuse must bypass NLU for exact blueprint-style questions.
        mock_nlu.assert_not_called()

@pytest.mark.asyncio
async def test_qie_intelligence_endpoint(test_client: AsyncClient):
    login_payload = {
        "email": "admin@luminaai.demo",
        "password": "AdminLumina@2026"
    }
    response = await test_client.post("/auth/login", json=login_payload)
    token = response.json().get("access_token")
    if not token:
        login_payload["password"] = "NewAdminLumina@2026"
        response = await test_client.post("/auth/login", json=login_payload)
        token = response.json()["access_token"]
        
    headers = {"Authorization": f"Bearer {token}"}

    # Test accessing the intelligence metrics endpoint
    response = await test_client.post(
        "/api/v1/query/",
        headers=headers,
        json={
            "pergunta": "quanto faturamos hoje",
            "tenant_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
        }
    )
    assert response.status_code == 200

    response_int = await test_client.get("/api/v1/query/intelligence", headers=headers)
    assert response_int.status_code == 200
    data = response_int.json()
    assert "total_consultas_processadas" in data
    assert "taxa_reutilizacao_percentual" in data
    assert "economia_tokens_total" in data
    assert "tempo_economizado_segundos" in data
