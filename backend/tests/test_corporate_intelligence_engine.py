"""
LuminaAI — Test Suite: Corporate Intelligence Engine (CIE)
-----------------------------------------------------------
Testes para os 12 motores e a fachada central do CIE.
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai.schemas import CIEContextSchema, BusinessIntentSchema, VisualStrategySchema
from services.ai.corporate_intelligence_engine import corporate_intelligence_engine
from services.ai.context_engine import context_engine
from services.ai.memory_context_engine import memory_context_engine
from services.ai.semantic_engine import semantic_engine
from services.ai.business_understanding_engine import business_understanding_engine
from services.ai.kpi_discovery_engine import kpi_discovery_engine
from services.ai.visualization_strategy_engine import visualization_strategy_engine
from services.ai.blueprint_builder import blueprint_builder
from services.ai.package_matcher import package_matcher
from services.ai.confidence_engine import confidence_engine
from services.ai.executive_analysis_engine import executive_analysis_engine
from services.ai.response_builder import response_builder


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Tests: Sub-Engines ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_context_engine_builds_context(tenant_id):
    """ContextEngine deve construir o CIEContextSchema oficial para o tenant."""
    mock_db = AsyncMock(spec=AsyncSession)
    ctx = await context_engine.build_context(
        tenant_id=tenant_id,
        db=mock_db,
        departamento="Financeiro",
        history=[{"role": "user", "content": "Ver faturamento"}],
        custom_instructions="Priorizar LTV"
    )
    assert ctx.tenant_id == tenant_id
    assert ctx.departamento == "Financeiro"
    assert len(ctx.historico_recente) == 1
    assert ctx.custom_instructions == "Priorizar LTV"


def test_memory_context_engine_session_profile(tenant_id):
    """MemoryContextEngine deve mapear preferências implícitas de gráficos e tópicos."""
    ctx = CIEContextSchema(
        tenant_id=tenant_id,
        historico_recente=[
            {"role": "user", "content": "Quem é o melhor vendedor?"},
            {"role": "user", "content": "Mostre isso em gráfico de pizza, por favor."},
        ]
    )
    profile = memory_context_engine.analyze_session_history(ctx)
    assert "PIE" in profile
    assert "VENDEDOR" in profile


def test_semantic_engine_normalization_and_synonyms():
    """SemanticEngine deve normalizar termos e mapear sinônimos corporativos."""
    clean = semantic_engine.clean_text("Tôp Vendêdôres! ")
    assert clean == "top vendedores!"
    
    # Resolução de sinônimos
    term1 = semantic_engine.resolve_synonyms("Melhores vendedores")
    assert term1 == "ranking de vendedores"
    
    term2 = semantic_engine.resolve_synonyms("faturamento")
    assert term2 == "receita_total"

    term3 = semantic_engine.resolve_synonyms("total_vendas")
    assert term3 == "receita_total"


@pytest.mark.asyncio
async def test_business_understanding_and_kpi_discovery(tenant_id):
    """BusinessUnderstanding e KPIDiscovery devem validar conceitos de negócio via BKE."""
    mock_db = AsyncMock(spec=AsyncSession)

    concept_mock = MagicMock()
    concept_mock.nome = "receita_total"
    concept_mock.descricao = "Total arrecadado"
    concept_mock.definicao_oficial = "sum(valor)"
    concept_mock.area = "Comercial"

    # Mock no BKE dictionary
    mock_get = AsyncMock(return_value=concept_mock)
    with patch("services.business.business_knowledge_engine.business_knowledge_engine.dictionary.get_concept", mock_get):
        meaning = await business_understanding_engine.get_concept_meaning(tenant_id, "receita", db=mock_db)
        assert meaning["nome"] == "receita_total"
        assert meaning["area"] == "Comercial"
        
        discovered = await kpi_discovery_engine.discover_metrics(tenant_id, ["receita"], db=mock_db)
        assert discovered == ["receita_total"]


@pytest.mark.asyncio
async def test_kpi_discovery_falls_back_to_central_semantic_normalizer(tenant_id):
    mock_db = AsyncMock(spec=AsyncSession)

    with patch("services.business.business_knowledge_engine.business_knowledge_engine.dictionary.get_concept", AsyncMock(return_value=None)), \
         patch("services.business.business_knowledge_engine.business_knowledge_engine.kpi_registry.get_kpi", AsyncMock(return_value=None)):
        discovered = await kpi_discovery_engine.discover_metrics(
            tenant_id,
            ["total vendido", "pedidos_totais", "ticket médio"],
            db=mock_db,
        )

    assert discovered == ["receita_total", "quantidade_pedidos", "ticket_medio"]


def test_visualization_strategy_engine():
    """VisualizationStrategyEngine deve sugerir layouts de gráficos ideais."""
    strat1 = visualization_strategy_engine.determine_strategy("RANKING", "VENDEDOR")
    assert strat1.componente_principal == "BAR"
    assert "TABLE" in strat1.componentes_secundarios

    # Explicit override
    strat2 = visualization_strategy_engine.determine_strategy("SOMA", "RECEITA", explicit_chart="PIE")
    assert strat2.componente_principal == "PIE"


def test_blueprint_builder_compiles_blueprint():
    """BlueprintBuilder deve gerar um Blueprint analítico sem conter SQL ou tabelas físicas."""
    intent = BusinessIntentSchema(
        objetivo="TOTAL",
        entidade="RECEITA",
        indicadores=["receita_total"],
        kpis=["receita_total"],
        filtros={"vendedor_nome": "João"},
        periodo="HOJE",
        agrupamentos=[],
        prioridade="ALTA",
        complexidade="BAIXA",
        visual_sugerido="KPI",
    )
    
    strat = VisualStrategySchema(
        componente_principal="KPI",
        componentes_secundarios=[],
        interatividade=["drill-down"],
    )
    
    blueprint = blueprint_builder.compile_blueprint(intent, strat)
    assert blueprint.kpis == ["receita_total"]
    assert blueprint.filtros == {"vendedor_nome": "João"}
    assert blueprint.dashboard_sugerida == "TEMPLATE_KPI_CARDS"
    assert blueprint.criado_em != ""


@pytest.mark.asyncio
async def test_package_matcher_finds_reusable_package(tenant_id):
    """PackageMatcher deve buscar AnalyticalPackages existentes baseando-se em fingerprints sem tempo."""
    mock_db = AsyncMock(spec=AsyncSession)
    
    intent = BusinessIntentSchema(
        objetivo="TOTAL",
        entidade="RECEITA",
        indicadores=["receita_total"],
        kpis=["receita_total"],
        filtros={},
        periodo="MES_PASSADO",
        agrupamentos=[],
    )

    package_mock = MagicMock()
    package_mock.id = uuid.uuid4()

    with patch("services.data_platform.package_compatibility.package_compatibility_engine.find_compatible_package", return_value=(package_mock, 0.95)):
        package, score = await package_matcher.match_package(tenant_id, intent, db=mock_db)
        assert package is not None
        assert package.id == package_mock.id
        assert score == 0.95


def test_confidence_engine():
    """ConfidenceEngine deve classificar e tratar limites de score corretamente."""
    res1 = confidence_engine.process_confidence(0.9)
    assert res1["status"] == "APPROVED"
    assert res1["executar"] is True

    res2 = confidence_engine.process_confidence(0.6)
    assert res2["status"] == "WARNING"
    assert res2["executar"] is False

    res3 = confidence_engine.process_confidence(0.2)
    assert res3["status"] == "REJECTED"


# ── Tests: Facade Orchestration ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_corporate_intelligence_engine_facade(tenant_id):
    """CIE Facade deve coordenar fluxo completo de NLU analítico."""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_client = AsyncMock()

    raw_mock = MagicMock()
    raw_mock.view_catalog_id = uuid.uuid4()
    raw_mock.fora_de_escopo = False
    raw_mock.resposta_direta = None
    raw_mock.operacao = "RANKING"
    raw_mock.entidade_alvo = "VENDEDOR"
    raw_mock.chart_type_sobrescrever = "BAR"
    raw_mock.chart_types_solicitados = []
    raw_mock.confianca = 0.95
    raw_mock.parametros = [MagicMock(chave="vendedor_nome", valor="Maria")]
    raw_mock.justificativa = "Ranking de vendedores em barras"
    raw_mock.plano_estruturado = MagicMock()
    raw_mock.plano_estruturado.metrics = ["receita"]
    raw_mock.plano_estruturado.group_by = ["vendedor"]
    raw_mock.nivel_confianca = "ALTA"
    raw_mock.periodo_referencia = "MES_PASSADO"
    raw_mock.is_comparacao = False
    raw_mock.comparativo_detalhe = None
    raw_mock.visualizacao_preferida = "BAR"
    raw_mock.quantidade_limite = None

    catalog_mock = MagicMock()
    catalog_mock.id = uuid.uuid4()
    catalog_mock.nome_view_oracle = "VW_VENDAS"
    catalog_mock.descricao_para_ia = "Visualização de vendas"
    catalog_mock.tipo_grafico_padrao.value = "BAR"
    catalog_mock.parametros_schema = {}

    concept_mock = MagicMock()
    concept_mock.nome = "receita_total"
    
    mock_get_concept = AsyncMock(return_value=concept_mock)
    mock_get_kpi = AsyncMock(return_value=None)

    with patch("services.ai.intent_engine.intent_engine.extract_intent", return_value=[raw_mock]), \
         patch("services.ai.package_matcher.package_matcher.match_package", return_value=(None, 0.0)), \
         patch("services.business.business_knowledge_engine.business_knowledge_engine.dictionary.get_concept", mock_get_concept), \
         patch("services.business.business_knowledge_engine.business_knowledge_engine.kpi_registry.get_kpi", mock_get_kpi):
        
        results = await corporate_intelligence_engine.identify_intention(
            pergunta="Vendedores mais produtivos do mês passado",
            catalog=[catalog_mock],
            client=mock_client,
            target_model="gpt-4o-mini",
            db=mock_db,
            tenant_id=tenant_id,
            request_id="req-123",
        )

        assert len(results) == 1
        res = results[0]
        assert res.operacao == "RANKING"
        assert res.entidade_alvo == "VENDEDOR"
        assert res.parametros == {"vendedor_nome": "Maria"}
        assert res.plano_estruturado.visualization.type == "BAR"
        assert res.plano_estruturado.requires_insight is True
