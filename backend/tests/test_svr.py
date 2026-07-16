import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from database import AsyncSessionLocal
from services.svr_service import svr_service
from services.svr_migration import svr_migration
from services.cache_service import global_cache
from models.blueprint import Blueprint
from models.user import User

BASE_URL = "http://testserver/api/v1"
DEMO_TENANT_ID = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_svr_bootstrap_and_resolution():
    """Valida que um conceito desconhecido no SVR é auto-inicializado com sucesso (bootstrap)."""
    async with AsyncSessionLocal() as db_session:
        # Usa um concept_id novo aleatório para forçar o bootstrap
        random_concept = f"MET_TEMP_{uuid.uuid4().hex[:6].upper()}"
        
        # Tenta resolver o conceito antes de qualquer cadastro
        snapshot = await svr_service.resolve_concept(
            db=db_session,
            tenant_id=DEMO_TENANT_ID,
            concept_id=random_concept
        )
        
        assert snapshot is not None
        assert snapshot["name"] == random_concept
        assert snapshot["physical_col"] == random_concept.lower()


@pytest.mark.asyncio
async def test_svr_register_and_change_status():
    """Valida o registro de nova versão de conceito e atualização de status na matriz."""
    async with AsyncSessionLocal() as db_session:
        concept_id = f"MET_UNIT_{uuid.uuid4().hex[:6].upper()}"
        snap_v1 = {"name": "Receita Teste", "physical_col": "receita_v1"}
        
        # 1. Registra v1.0
        version_rec = await svr_service.register_concept_version(
            db=db_session,
            tenant_id=DEMO_TENANT_ID,
            concept_id=concept_id,
            concept_type="METRIC",
            semantic_version="1.0",
            mapping_version="1",
            snapshot=snap_v1,
            autor="Test Runner",
            motivo="Versão inicial de teste"
        )
        
        assert version_rec.id is not None
        
        # Resolve v1.0 (deve retornar ativo por padrão)
        resolved = await svr_service.resolve_concept(
            db=db_session,
            tenant_id=DEMO_TENANT_ID,
            concept_id=concept_id
        )
        assert resolved["physical_col"] == "receita_v1"

        # 2. Altera status para LEGACY
        success = await svr_service.set_version_status(
            db=db_session,
            tenant_id=DEMO_TENANT_ID,
            concept_id=concept_id,
            semantic_version="1.0",
            mapping_version="1",
            status="LEGACY",
            autor="Test Runner",
            motivo="Depreciação temporária"
        )
        assert success is True


@pytest.mark.asyncio
async def test_svr_cache_isolation():
    """Valida que o cache do LuminaAI isola chaves com base nas versões do SVR."""
    key_hash = "my_custom_key_hash"
    value_v1 = "Data from V1"
    value_v2 = "Data from V2"

    # Set v1
    global_cache.set(
        tenant_id=DEMO_TENANT_ID,
        namespace="query",
        key_hash=key_hash,
        value=value_v1,
        semantic_version="1.0",
        mapping_version="1"
    )

    # Set v2
    global_cache.set(
        tenant_id=DEMO_TENANT_ID,
        namespace="query",
        key_hash=key_hash,
        value=value_v2,
        semantic_version="2.0",
        mapping_version="2"
    )

    # Get v1 e v2 (devem ser diferentes!)
    res_v1 = global_cache.get(
        tenant_id=DEMO_TENANT_ID,
        namespace="query",
        key_hash=key_hash,
        semantic_version="1.0",
        mapping_version="1"
    )
    res_v2 = global_cache.get(
        tenant_id=DEMO_TENANT_ID,
        namespace="query",
        key_hash=key_hash,
        semantic_version="2.0",
        mapping_version="2"
    )

    assert res_v1 == value_v1
    assert res_v2 == value_v2


@pytest.mark.asyncio
async def test_svr_migration_impact():
    """Valida o Migration Engine auditando impactos sobre blueprints de teste."""
    async with AsyncSessionLocal() as db_session:
        # Cria um blueprint temporário de teste
        temp_bp = Blueprint(
            tenant_id=DEMO_TENANT_ID,
            intent_id=f"test_bp_{uuid.uuid4().hex[:6]}",
            nome_consulta="Relatório de Teste SVR",
            objetivo="Testar SVR",
            view_name="VW_MOCK",
            metrics=["MET_MIG_001"],
            group_by=["DIM_MIG_001"],
            filters={}
        )
        db_session.add(temp_bp)
        await db_session.commit()

        # Avalia o impacto de migração para MET_MIG_001
        report = await svr_migration.evaluate_migration_impact(
            db=db_session,
            tenant_id=DEMO_TENANT_ID,
            concept_id="MET_MIG_001",
            new_semantic_version="2.0",
            new_mapping_version="2"
        )

        assert report["affected_blueprints_count"] >= 1
        assert any(bp["nome"] == "Relatório de Teste SVR" for bp in report["affected_blueprints"])

        # Limpeza
        await db_session.delete(temp_bp)
        await db_session.commit()


@pytest.mark.asyncio
async def test_svr_endpoints():
    """Valida os endpoints REST do SVR via roteador do FastAPI."""
    from sqlalchemy import update
    async with AsyncSessionLocal() as db_session:
        stmt_pwd = update(User).where(User.email == "admin@luminaai.demo").values(must_change_password=False)
        await db_session.execute(stmt_pwd)
        await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        # 1. Login para obter as headers de autenticação
        login_payload = {
            "email": "admin@luminaai.demo",
            "password": "AdminLumina@2026"
        }
        # Redefine a senha caso seja necessário nos testes integrados
        login_res = await client.post("/auth/login", json=login_payload)
        if login_res.status_code == 403:
            # Tenta trocar a senha padrão
            # (No pytest geral o banco é resetado, mas se o admin já tiver mudado a senha de teste)
            login_payload["password"] = "NewAdminLumina@2026"
            login_res = await client.post("/auth/login", json=login_payload)
            
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Teste GET /svr/ (Summary)
        res_sum = await client.get("/svr/", headers=headers)
        assert res_sum.status_code == 200
        assert "total_concepts" in res_sum.json()

        # 3. Teste POST /svr/concepts/register
        reg_payload = {
            "concept_id": "MET_API_TEST",
            "concept_type": "METRIC",
            "semantic_version": "1.0",
            "mapping_version": "1",
            "snapshot": {"name": "Receita API", "physical_col": "receita_api"},
            "motivo": "Homologação de teste via API",
            "impacto": "Nenhum"
        }
        res_reg = await client.post("/svr/concepts/register", json=reg_payload, headers=headers)
        assert res_reg.status_code == 201
        assert res_reg.json()["success"] is True

        # 4. Teste GET /svr/concepts/{id}/history
        res_hist = await client.get("/svr/concepts/MET_API_TEST/history", headers=headers)
        assert res_hist.status_code == 200
        data_hist = res_hist.json()
        assert len(data_hist["versions"]) >= 1
        assert data_hist["concept_id"] == "MET_API_TEST"

        # 5. Teste POST /svr/migration/evaluate
        eval_payload = {
            "concept_id": "MET_API_TEST",
            "new_semantic_version": "2.0",
            "new_mapping_version": "2"
        }
        res_eval = await client.post("/svr/migration/evaluate", json=eval_payload, headers=headers)
        assert res_eval.status_code == 200
        assert "affected_blueprints_count" in res_eval.json()
