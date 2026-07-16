import pytest
import pytest_asyncio
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from services.ai.csie import csie, STABLE_METRICS, STABLE_DIMENSIONS, STABLE_PERIODS
from models.semantic_memory import SemanticMemory


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_csie_tables():
    from database import engine, Base
    import models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def test_csie_clean_text():
    """Valida a limpeza ortográfica, remoção de acentos e caixa baixa."""
    assert csie.clean_text("Faturamento Mensal!") == "faturamento mensal"
    assert csie.clean_text("Açúcar & Soja") == "acucar soja"
    assert csie.clean_text("  Quanto   Vendemos?  ") == "quanto vendemos"
    assert csie.clean_text(None) == ""


def test_csie_match_static_fast():
    """Valida a busca rápida estática em memória para aliases cadastrados."""
    # Métricas
    res_m, score_m = csie._match_static_fast("quanto vendemos")
    assert res_m is not None
    assert "MET_001" in res_m["metrics"]
    assert score_m == 0.95

    # Dimensões
    res_d, score_d = csie._match_static_fast("vendedor")
    assert res_d is not None
    assert "DIM_002" in res_d["dimensions"]
    assert score_d == 0.95

    # Períodos
    res_p, score_p = csie._match_static_fast("este mes")
    assert res_p is not None
    assert res_p["period"] == "PER_CURRENT_MONTH"
    assert score_p == 0.95


def test_csie_resolve_metric_fallback():
    """Valida a resolução síncrona de métricas para o validador."""
    assert csie.resolve_metric_fallback("quanto vendemos") == "receita_total"
    assert csie.resolve_metric_fallback("faturamento") == "faturamento_realizado"
    assert csie.resolve_metric_fallback("lucro bruto") == "lucro_bruto"
    assert csie.resolve_metric_fallback("lucro") == "lucro_bruto"
    assert csie.resolve_metric_fallback("inexistente") is None


@pytest.mark.asyncio
async def test_csie_translate_plan_to_physical():
    """Valida a tradução de planos semânticos estáveis em planos físicos reais."""
    stable_plan = {
        "metrics": ["MET_001", "MET_003"],
        "dimensions": ["DIM_002"],
        "period": "PER_CURRENT_MONTH",
        "filters": {
            "DIM_003": ["Semente de Milho"]
        }
    }
    
    tenant_id = uuid.uuid4()
    # Mock do catálogo de metadados
    meta_catalog = []

    physical_plan = await csie.translate_plan_to_physical(
        stable_plan=stable_plan,
        view_name="VW_AGRO_PERFORMANCE",
        tenant_id=tenant_id,
        meta_catalog=meta_catalog
    )

    assert "receita_total" in physical_plan["metrics"]
    assert "lucro_bruto" in physical_plan["metrics"]
    assert "vendedor" in physical_plan["group_by"]
    assert "produto" in physical_plan["filters"]
    assert physical_plan["filters"]["produto"] == ["Semente de Milho"]
    assert "date_range" in physical_plan["filters"]


@pytest.mark.asyncio
async def test_csie_generates_cip_for_product_ranking_without_physical_metadata():
    """CSIE deve gerar CIP conceitual para ranking de produtos sem dados fisicos."""
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as db_session:
        tenant_id = uuid.uuid4()

        cip, score, origin = await csie.generate_corporate_intent_plan(
            pergunta="Quais os produtos mais vendidos nos ultimos 3 meses?",
            tenant_id=tenant_id,
            db=db_session,
        )

        legacy = cip.to_legacy_semantic_plan()
        serialized = str(cip.model_dump()).lower()

        assert origin == "STATIC"
        assert score >= 0.90
        assert "MET_006" in legacy["metrics"]
        assert "DIM_003" in legacy["dimensions"]
        assert legacy["period"] == "PER_LAST_90_DAYS"
        assert cip.hypotheses
        assert cip.audit["contains_physical_metadata"] is False
        assert "physical_col" not in serialized
        assert "sql" not in serialized


@pytest.mark.asyncio
async def test_csie_generates_cip_for_product_financial_return():
    """Retorno financeiro por produto deve virar metricas corporativas, nao rejeicao."""
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as db_session:
        tenant_id = uuid.uuid4()

        cip, score, origin = await csie.generate_corporate_intent_plan(
            pergunta="Qual o produto que mais tem retorno financeiro para a empresa?",
            tenant_id=tenant_id,
            db=db_session,
        )

        legacy = cip.to_legacy_semantic_plan()

        assert origin == "STATIC"
        assert score >= 0.90
        assert "MET_001" in legacy["metrics"]
        assert "MET_004" in legacy["metrics"]
        assert "DIM_003" in legacy["dimensions"]
        assert cip.confidence_level == "ALTA"
        assert len(cip.hypotheses) >= 2


@pytest.mark.asyncio
async def test_csie_resolve_query_memory_hit():
    """Valida a resolução direta via repositório de memória semântica (hit)."""
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as db_session:
        tenant_id = uuid.UUID('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11')
        text_clean = "quanto vendemos hoje"
        obj_expected = {"metrics": ["MET_001"], "dimensions": [], "period": "PER_TODAY", "filters": {}}

        # Salva pré-requisito de memória semântica
        memory = SemanticMemory(
            tenant_id=tenant_id,
            expressao=text_clean,
            objeto_resolvido=obj_expected,
            score=98.00,
            confianca="ALTA",
            origem="IA"
        )
        db_session.add(memory)
        await db_session.commit()

        obj_res, score_res, origem_res = await csie.resolve_query(
            pergunta="Quanto vendemos hoje?",
            tenant_id=tenant_id,
            db=db_session
        )

        assert obj_res == obj_expected
        assert score_res == 98.00
        assert origem_res == "MEMORY"


@pytest.mark.asyncio
async def test_csie_resolve_query_ia_fallback():
    """Valida o fallback de IA estruturado quando não há hit de memória nem estático."""
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as db_session:
        tenant_id = uuid.UUID('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11')
        mock_openai_client = AsyncMock()
        
        # Mock do retorno da API OpenAI
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content='{"metrics": ["MET_001"], "dimensions": ["DIM_002"], "period": "PER_CURRENT_MONTH", "confidence": 0.96}'
                )
            )
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        obj_res, score_res, origem_res = await csie.resolve_query(
            pergunta=f"Qual bla bla bla xyz {uuid.uuid4()}?",
            tenant_id=tenant_id,
            db=db_session,
            client=mock_openai_client
        )

        assert "MET_001" in obj_res["metrics"]
        assert "DIM_002" in obj_res["dimensions"]
        assert obj_res["period"] == "PER_CURRENT_MONTH"
        assert score_res == 0.96
        assert origem_res == "IA"
