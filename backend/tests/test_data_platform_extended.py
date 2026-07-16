import pytest
import pytest_asyncio
import uuid
import json
from sqlalchemy import select, delete
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from main import app
from database import AsyncSessionLocal
from models.tenant import Tenant
from models.view_catalog import ViewCatalog, ChartType
from models.metadata_catalog import MetadataCatalog
from models.dataset import Dataset
from models.data_platform_history import DataPlatformHistory
from services.data_platform.integrity_service import integrity_service
from services.data_platform.history_service import history_service

BASE_URL = "http://testserver/api/v1"

@pytest_asyncio.fixture
async def test_client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE_URL
    ) as client:
        yield client

@pytest_asyncio.fixture
async def auth_headers(test_client):
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

@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    """Limpa dados de testes da Data Platform antes e depois de cada teste para evitar poluição."""
    names = [
        "VW_TEST_EXTENDED_DATAPLATFORM",
        "VW_INTEGRITY_TEST_OK",
        "VW_INTEGRITY_TEST_ERR",
        "VW_ISOLATION_TEST"
    ]
    async with AsyncSessionLocal() as db_sess:
        await db_sess.execute(delete(Dataset).where(Dataset.origem.in_(names)))
        await db_sess.execute(delete(MetadataCatalog).where(MetadataCatalog.nome_view.in_(names)))
        await db_sess.execute(delete(ViewCatalog).where(ViewCatalog.nome_view_oracle.in_(names)))
        await db_sess.commit()
    yield
    async with AsyncSessionLocal() as db_sess:
        await db_sess.execute(delete(Dataset).where(Dataset.origem.in_(names)))
        await db_sess.execute(delete(MetadataCatalog).where(MetadataCatalog.nome_view.in_(names)))
        await db_sess.execute(delete(ViewCatalog).where(ViewCatalog.nome_view_oracle.in_(names)))
        await db_sess.commit()

@pytest.mark.asyncio
async def test_datasets_persistence_and_versioning(test_client, auth_headers):
    # Setup view
    tenant_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    view_name = "VW_TEST_EXTENDED_DATAPLATFORM"
    
    # Register new view in catalog
    async with AsyncSessionLocal() as db_sess:
        view_cat = ViewCatalog(
            tenant_id=uuid.UUID(tenant_id),
            nome_view_oracle=view_name,
            descricao_para_ia="View para testes estendidos da Data Platform",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={"limite": {"type": "number", "required": False}},
            ativo=True
        )
        db_sess.add(view_cat)
        await db_sess.commit()
        await db_sess.refresh(view_cat)
        
        # Register in metadata catalog
        meta_cat = MetadataCatalog(
            tenant_id=uuid.UUID(tenant_id),
            nome_view=view_name,
            origem="ERP_ORACLE",
            tabelas_utilizadas=["TEST_EXTENDED"],
            versao=1,
            status="success",
            integridade="valid"
        )
        db_sess.add(meta_cat)
        await db_sess.commit()

    # 2. Register mock intention and execute query
    from services.ai_service import IntentionResponse, StructuredPlanSchema, PlanFiltersSchema, PlanVisualizationSchema
    mock_intention = IntentionResponse(
        view_catalog_id=view_cat.id,
        confianca=0.98,
        parametros={"limite": "5"},
        justificativa="Testando persistência do dataset",
        fora_de_escopo=False,
        operacao="SOMA",
        entidade_alvo="VENDA",
        nivel_confianca="ALTA",
        plano_estruturado=StructuredPlanSchema(
            request_id=str(uuid.uuid4()),
            intent=view_name,
            query_type="AGGREGATION",
            metrics=["receita_total"],
            group_by=[],
            filters=PlanFiltersSchema(date_range="", products=[], customers=[], regions=[]),
            visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA"),
            requires_insight=True,
            confidence_score=0.98
        )
    )
    
    # Registra o mock da view na camada semântica
    from services.semantic_layer import _BUSINESS_DICT
    if "receita_total" in _BUSINESS_DICT and view_name not in _BUSINESS_DICT["receita_total"]["data_sources"]:
        _BUSINESS_DICT["receita_total"]["data_sources"].append(view_name)

    # Executa a query duas vezes para validar versionamento incremental (v1 e v2)
    with patch("routers.query.identify_intention", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = [mock_intention]
        
        with patch("services.query_intelligence_engine.QueryIntelligenceEngine.get_similarity_score", return_value=(0.0, None)):
            with patch("services.data_platform.data_access_layer.DataAccessLayer.read_view_data", new_callable=AsyncMock) as mock_read:
                mock_read.return_value = [{"id": 1, "receita_total": 1500.0, "vendedor": "John"}]
                
                res1 = await test_client.post(
                    "/api/v1/query/",
                    headers=auth_headers,
                    json={"pergunta": "Executar query estendida v1", "tenant_id": tenant_id}
                )
                assert res1.status_code == 200
                
                res2 = await test_client.post(
                    "/api/v1/query/",
                    headers=auth_headers,
                    json={"pergunta": "Executar query estendida v2", "tenant_id": tenant_id}
                )
                assert res2.status_code == 200

    # 3. Verifica datasets persistidos no banco de dados analítico
    async with AsyncSessionLocal() as db_sess:
        stmt = select(Dataset).where(
            Dataset.tenant_id == uuid.UUID(tenant_id),
            Dataset.origem == view_name
        ).order_by(Dataset.version.asc())
        
        res_d = await db_sess.execute(stmt)
        datasets = res_d.scalars().all()
        
        assert len(datasets) == 2
        assert datasets[0].version == 1
        assert datasets[1].version == 2
        assert datasets[0].origem == view_name
        
        dados = datasets[0].dados_estruturados
        if isinstance(dados, str):
            dados = json.loads(dados)
        assert len(dados) == 1
        assert dados[0]["receita_total"] == 1500.0

@pytest.mark.asyncio
async def test_integrity_service_checks(test_client, auth_headers):
    tenant_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    view_name_ok = "VW_INTEGRITY_TEST_OK"
    view_name_err = "VW_INTEGRITY_TEST_ERR"
    
    async with AsyncSessionLocal() as db_sess:
        # 1. Cria uma view íntegra (deixando hash vazio para auto-geração)
        v_ok = ViewCatalog(
            tenant_id=uuid.UUID(tenant_id),
            nome_view_oracle=view_name_ok,
            descricao_para_ia="View integra para teste de consistencia",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={"mes": {"type": "integer"}},
            ativo=True
        )
        db_sess.add(v_ok)
        await db_sess.flush()
        
        m_ok = MetadataCatalog(
            tenant_id=uuid.UUID(tenant_id),
            nome_view=view_name_ok,
            origem="ERP_ORACLE",
            tabelas_utilizadas=["TAB_OK"],
            versao=1,
            status="success",
            integridade="valid",
            hash_integridade="" # Vazio para auto-calcular
        )
        db_sess.add(m_ok)
        
        # 2. Cria uma view com hash inconsistente (para disparar HASH_MISMATCH)
        v_err = ViewCatalog(
            tenant_id=uuid.UUID(tenant_id),
            nome_view_oracle=view_name_err,
            descricao_para_ia="View com erro de hash no catalog",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={"mes": {"type": "integer"}},
            ativo=True
        )
        db_sess.add(v_err)
        await db_sess.flush()
        
        m_err = MetadataCatalog(
            tenant_id=uuid.UUID(tenant_id),
            nome_view=view_name_err,
            origem="ERP_ORACLE",
            tabelas_utilizadas=["TAB_ERR"],
            versao=1,
            status="success",
            integridade="valid",
            hash_integridade="HASH_FALSO_INCORRETO" # hash que vai dar mismatch
        )
        db_sess.add(m_err)
        await db_sess.commit()

    # 3. Executa a auditoria de integridade
    relatorio = await integrity_service.validate_tenant_integrity(uuid.UUID(tenant_id))
    
    assert relatorio["valid"] is False
    assert len(relatorio["inconsistencies"]) >= 1
    
    # O mismatch do hash_integridade deve ter sido pego!
    mismatch = next((inc for inc in relatorio["inconsistencies"] if inc["tipo"] == "HASH_MISMATCH"), None)
    assert mismatch is not None
    assert mismatch["alvo"] == view_name_err

@pytest.mark.asyncio
async def test_history_service_logging(test_client, auth_headers):
    tenant_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    estrutura_id = "bp_extended_v1"
    
    # 1. Limpa registros históricos antigos deste alvo
    async with AsyncSessionLocal() as db_sess:
        await db_sess.execute(delete(DataPlatformHistory).where(
            DataPlatformHistory.tenant_id == uuid.UUID(tenant_id),
            DataPlatformHistory.estrutura_id == estrutura_id
        ))
        await db_sess.commit()
        
    # 2. Grava um novo log de mudança
    log = await history_service.log_change(
        tenant_id=uuid.UUID(tenant_id),
        estrutura_tipo="BLUEPRINT",
        estrutura_id=estrutura_id,
        acao="VERSION_UP",
        detalhes={"autor": "Teste Estendido", "campos": ["faturamento"]}
    )
    
    assert log.id is not None
    assert log.acao == "VERSION_UP"
    assert log.estrutura_tipo == "BLUEPRINT"
    
    # 3. Recupera o histórico
    logs = await history_service.get_history(uuid.UUID(tenant_id), estrutura_tipo="BLUEPRINT")
    
    # Garante que nosso log recém-criado está no topo (ordem descrescente)
    assert len(logs) >= 1
    latest_log = logs[0]
    assert latest_log.estrutura_id == estrutura_id
    assert latest_log.acao == "VERSION_UP"
    
    detalhes = latest_log.detalhes
    if isinstance(detalhes, str):
        detalhes = json.loads(detalhes)
    assert detalhes["autor"] == "Teste Estendido"

@pytest.mark.asyncio
async def test_multi_tenant_isolation_and_security(test_client, auth_headers):
    tenant_a = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    tenant_b = "b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b22" # Tenant B fictício para isolamento
    view_name = "VW_ISOLATION_TEST"
    
    # Cria uma view no Tenant A
    async with AsyncSessionLocal() as db_sess:
        v_a = ViewCatalog(
            tenant_id=uuid.UUID(tenant_a),
            nome_view_oracle=view_name,
            descricao_para_ia="View no Tenant A para teste de isolamento multi-tenant",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={},
            ativo=True
        )
        db_sess.add(v_a)
        await db_sess.commit()
        
    # 1. Tenta recuperar o catálogo ou realizar integridade para o Tenant B
    # O IntegrityService deve isolar e não revelar a view do Tenant A no relatório do Tenant B
    relatorio_b = await integrity_service.validate_tenant_integrity(uuid.UUID(tenant_b))
    
    # Como o Tenant B está vazio e não tem nenhuma view ou metadado, seu relatório de integridade é limpo
    assert relatorio_b["valid"] is True
    assert len(relatorio_b["inconsistencies"]) == 0
    
    # O relatório do Tenant A deve flaggar inconsistência de metadados para a view recém criada
    relatorio_a = await integrity_service.validate_tenant_integrity(uuid.UUID(tenant_a))
    assert relatorio_a["valid"] is False
    assert any(inc["alvo"] == view_name for inc in relatorio_a["inconsistencies"])
