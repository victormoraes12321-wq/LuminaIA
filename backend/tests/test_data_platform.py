import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from database import AsyncSessionLocal
from models.tenant import Tenant
from models.blueprint import Blueprint
from models.metadata_catalog import MetadataCatalog
from models.view_catalog import ViewCatalog, ChartType
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


@pytest_asyncio.fixture
async def auth_headers(test_client):
    """Realiza login e retorna os cabeçalhos de autorização."""
    login_payload = {
        "email": "admin@luminaai.demo",
        "password": "AdminLumina@2026"
    }
    response = await test_client.post("/auth/login", json=login_payload)
    token = response.json().get("access_token")
    if not token:
        login_payload["password"] = "NovaSenhaAdmin@2026"
        response = await test_client.post("/auth/login", json=login_payload)
        token = response.json()["access_token"]
        
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_data_platform_first_and_future_queries(test_client, auth_headers):
    # Registra a view de teste na camada semântica para a validação passar
    from services.semantic_layer import _BUSINESS_DICT
    if "receita_total" in _BUSINESS_DICT and "VW_TEST_DATAPLATFORM" not in _BUSINESS_DICT["receita_total"]["data_sources"]:
        _BUSINESS_DICT["receita_total"]["data_sources"].append("VW_TEST_DATAPLATFORM")

    # 1. Setup: Cria uma view analítica de teste no catálogo do banco se não existir
    tenant_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    view_name = "VW_TEST_DATAPLATFORM"
    
    async with AsyncSessionLocal() as db_sess:
        # Garante a limpeza de registros pré-existentes de testes anteriores
        from models.blueprint import Blueprint
        from models.metadata_catalog import MetadataCatalog
        from sqlalchemy import delete
        
        await db_sess.execute(delete(Blueprint).where(
            Blueprint.tenant_id == uuid.UUID(tenant_id),
            Blueprint.view_name == view_name
        ))
        await db_sess.execute(delete(MetadataCatalog).where(
            MetadataCatalog.tenant_id == uuid.UUID(tenant_id),
            MetadataCatalog.nome_view == view_name
        ))
        await db_sess.commit()

        stmt = select(ViewCatalog).where(
            ViewCatalog.nome_view_oracle == view_name,
            ViewCatalog.tenant_id == uuid.UUID(tenant_id)
        )
        res = await db_sess.execute(stmt)
        view_cat = res.scalar_one_or_none()
        
        if view_cat:
            view_cat.ativo = True
            view_cat.descricao_para_ia = "View de teste de vendas e faturamento diario da Data Platform"
            db_sess.add(view_cat)
            await db_sess.commit()
        else:
            view_cat = ViewCatalog(
                tenant_id=uuid.UUID(tenant_id),
                nome_view_oracle=view_name,
                descricao_para_ia="View de teste de vendas e faturamento diario da Data Platform",
                tipo_grafico_padrao=ChartType.BAR,
                parametros_schema={"limite": {"type": "number", "required": False}},
                ativo=True
            )
            db_sess.add(view_cat)
            await db_sess.commit()
            await db_sess.refresh(view_cat)
            
        view_catalog_id = view_cat.id

    # 2. Primeira Consulta: Simula consulta que não existe blueprint ainda
    from services.ai_service import StructuredPlanSchema, PlanFiltersSchema, PlanVisualizationSchema
    mock_intention = IntentionResponse(
        view_catalog_id=view_catalog_id,
        confianca=0.96,
        parametros={"limite": "10"},
        justificativa="Performance comercial da nova view de teste.",
        fora_de_escopo=False,
        operacao="SOMA",
        entidade_alvo="VENDA",
        nivel_confianca="ALTA",
        plano_estruturado=StructuredPlanSchema(
            request_id=str(uuid.uuid4()),
            intent="VW_TEST_DATAPLATFORM",
            query_type="AGGREGATION",
            metrics=["receita_total"],
            group_by=[],
            filters=PlanFiltersSchema(date_range="", products=[], customers=[], regions=[]),
            visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA"),
            requires_insight=True,
            confidence_score=0.96
        )
    )

    with patch("routers.query.identify_intention", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = [mock_intention]
        
        # Dispara a primeira consulta (desativando QIE temporariamente para forçar criação de blueprint)
        with patch("services.query_intelligence_engine.QueryIntelligenceEngine.get_similarity_score", return_value=(0.0, None)):
            res = await test_client.post(
                "/api/v1/query/",
                headers=auth_headers,
                json={
                    "pergunta": "Como estão os testes na data platform?",
                    "tenant_id": tenant_id
                }
            )
        assert res.status_code == 200
        print("DEBUG FIRST QUERY RESPONSE:", res.json())
        
        # Confere se o blueprint foi salvo no banco de dados da Data Platform
        async with AsyncSessionLocal() as db_sess:
            bp_stmt = select(Blueprint).where(
                Blueprint.tenant_id == uuid.UUID(tenant_id),
                Blueprint.view_name == view_name
            )
            bp_res = await db_sess.execute(bp_stmt)
            bp = bp_res.scalar_one_or_none()
            assert bp is not None
            assert bp.version == 1
            
            # Confere se os metadados foram registrados no Metadata Catalog
            meta_stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == uuid.UUID(tenant_id),
                MetadataCatalog.nome_view == view_name
            )
            meta_res = await db_sess.execute(meta_stmt)
            meta = meta_res.scalar_one_or_none()
            assert meta is not None
            assert meta.quantidade_consultas == 1
            assert float(meta.tempo_medio_execucao) > 0.0

    # 3. Consulta Futura: Simula a mesma consulta ou consulta similar que deve reutilizar o blueprint
    # Patch identify_intention para garantir que ele NÃO é chamado
    with patch("routers.query.identify_intention", new_callable=AsyncMock) as mock_ai:
        res = await test_client.post(
            "/api/v1/query/",
            headers=auth_headers,
            json={
                "pergunta": "Como estão os testes na data platform?",
                "tenant_id": tenant_id
            }
        )
        assert res.status_code == 200
        
        # identify_intention não deve ter sido chamado devido ao bypass do QIE
        mock_ai.assert_not_called()
        
        # Confere se a quantidade de consultas subiu para 2 no Metadata Catalog
        async with AsyncSessionLocal() as db_sess:
            meta_stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == uuid.UUID(tenant_id),
                MetadataCatalog.nome_view == view_name
            )
            meta_res = await db_sess.execute(meta_stmt)
            meta = meta_res.scalar_one()
            assert meta.quantidade_consultas == 2
