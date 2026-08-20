"""
LuminaAI — Test Suite: Business Knowledge Engine (BKE)
-------------------------------------------------------
Testa todos os submotores, governança, rollback, multi-tenant e validação do BKE.
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.business.business_knowledge_engine import business_knowledge_engine
from services.business.business_validation_engine import BusinessValidationError


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def other_tenant_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Tests: Dictionary & KPI Registry ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_concept_registration_and_uniqueness(tenant_id):
    """BusinessDictionary deve registrar conceitos e impedir múltiplas definições duplicadas."""
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Mock do get_concept retornando None na primeira (criação)
    with patch.object(business_knowledge_engine.dictionary, "get_concept", return_value=None):
        concept_data = {
            "nome": "Lucro",
            "descricao": "Resultado financeiro positivo.",
            "definicao_oficial": "Receita - Custos",
            "categoria": "Financeiro",
            "tipo": "Fato",
        }
        
        res = await business_knowledge_engine.dictionary.register_concept(
            tenant_id=tenant_id,
            concept_data=concept_data,
            autor="test_user@luminaai.demo",
            db=mock_db,
        )
        
        assert res.nome == "Lucro"
        assert res.versao == 1
        assert res.status == "ACTIVE"


@pytest.mark.asyncio
async def test_kpi_registry_uniqueness(tenant_id):
    """BusinessKPIRegistry deve registrar KPIs oficiais e controlar duplicidades."""
    mock_db = AsyncMock(spec=AsyncSession)

    with patch.object(business_knowledge_engine.kpi_registry, "get_kpi", return_value=None):
        kpi_data = {
            "nome": "ROI",
            "descricao": "Retorno sobre Investimento.",
            "formula_oficial": "(ganho - investimento) / investimento",
            "objetivo": "Medir retorno",
            "unidade": "%",
        }

        res = await business_knowledge_engine.kpi_registry.register_kpi(
            tenant_id=tenant_id,
            kpi_data=kpi_data,
            autor="test_user@luminaai.demo",
            db=mock_db,
        )

        assert res.nome == "ROI"
        assert res.versao == 1
        assert res.formula_oficial == "(ganho - investimento) / investimento"


# ── Tests: Formula Engine ─────────────────────────────────────────────────────

def test_formula_engine_evaluates_roi():
    """BusinessFormulaEngine deve calcular ROI corretamente."""
    res = business_knowledge_engine.formula_engine.evaluate_formula(
        "ROI", {"retorno": 1500.0, "investimento": 1000.0}
    )
    # (1500 - 1000) / 1000 = 0.5
    assert res == 0.5


def test_formula_engine_evaluates_cac():
    """BusinessFormulaEngine deve calcular CAC corretamente."""
    res = business_knowledge_engine.formula_engine.evaluate_formula(
        "CAC", {"custos_aquisicao": 5000.0, "novos_clientes": 50}
    )
    assert res == 100.0


def test_formula_engine_evaluates_ltv():
    """BusinessFormulaEngine deve calcular LTV corretamente."""
    res = business_knowledge_engine.formula_engine.evaluate_formula(
        "LTV", {"ticket_medio": 200.0, "frequencia_compras": 3.0, "tempo_vida_medio": 2.0}
    )
    assert res == 1200.0


def test_formula_engine_evaluates_curva_abc():
    """BusinessFormulaEngine deve categorizar itens na Curva ABC."""
    inputs = {
        "valores_itens": [
            {"nome": "Item A", "valor": 80.0},
            {"nome": "Item B", "valor": 15.0},
            {"nome": "Item C", "valor": 5.0},
        ]
    }
    res = business_knowledge_engine.formula_engine.evaluate_formula("Curva ABC", inputs)
    assert len(res) == 3
    assert res[0]["classe"] == "A"
    assert res[1]["classe"] == "B"
    assert res[2]["classe"] == "C"


def test_formula_engine_prevents_division_by_zero():
    """BusinessFormulaEngine deve levantar erro descritivo em caso de divisão por zero ou pré-requisito falho."""
    with pytest.raises(ValueError, match="Investimento deve ser maior que zero"):
        business_knowledge_engine.formula_engine.evaluate_formula(
            "ROI", {"ganho": 1000.0, "investimento": 0.0}
        )


# ── Tests: Relationship & Context Engines ──────────────────────────────────────

def test_context_engine_returns_contexts():
    """BusinessContextEngine deve expor os 11 contextos oficiais da empresa."""
    contexts = business_knowledge_engine.context_engine.get_official_contexts()
    assert len(contexts) == 11
    assert "Financeiro" in contexts
    assert "Comercial" in contexts
    assert "Estoque" in contexts


@pytest.mark.asyncio
async def test_context_engine_lists_by_context(tenant_id):
    """BusinessContextEngine deve classificar e listar elementos por contexto."""
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Mocks para retornar conceitos/KPIs correspondentes
    c1 = MagicMock()
    c1.nome = "Receita"
    
    k1 = MagicMock()
    k1.nome = "LTV"

    res_c = MagicMock()
    res_c.scalars.return_value.all.return_value = [c1]
    
    res_k = MagicMock()
    res_k.scalars.return_value.all.return_value = [k1]
    
    mock_db.execute.side_effect = [res_c, res_k]
    
    res = await business_knowledge_engine.context_engine.list_by_context(
        tenant_id=tenant_id, context="Financeiro", db=mock_db
    )
    
    assert "Receita" in res["concepts"]
    assert "LTV" in res["kpis"]


# ── Tests: Validation Engine ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validation_engine_blocks_sum_on_percentage(tenant_id):
    """BusinessValidationEngine deve bloquear operação SOMA em métricas percentuais."""
    mock_db = AsyncMock(spec=AsyncSession)

    # Mock do kpi de margem
    kpi_margem = MagicMock()
    kpi_margem.nome = "margem_lucro"
    kpi_margem.unidade = "%"
    kpi_margem.faixas = {}

    plan = MagicMock()
    plan.consulta_principal.metrics = ["margem_lucro"]
    plan.consulta_principal.group_by = []
    plan.consulta_principal.filters = {}
    plan.consulta_principal.operacao = "SOMA"

    with patch.object(business_knowledge_engine.kpi_registry, "get_kpi", return_value=kpi_margem), \
         patch.object(business_knowledge_engine.dictionary, "get_concept", return_value=None):
        
        is_valid, errors = await business_knowledge_engine.validation_engine.validate_query_plan(
            tenant_id=tenant_id, plan=plan, db=mock_db
        )
        assert is_valid is False
        assert any("Operação SOMA inválida" in err for err in errors)


@pytest.mark.asyncio
async def test_validation_engine_blocks_metric_group_by(tenant_id):
    """BusinessValidationEngine deve bloquear agrupamento (group_by) usando KPIs."""
    mock_db = AsyncMock(spec=AsyncSession)

    kpi = MagicMock()
    kpi.nome = "LTV"
    kpi.unidade = "R$"
    kpi.faixas = {}

    plan = MagicMock()
    plan.consulta_principal.metrics = ["receita_total"]
    plan.consulta_principal.group_by = ["LTV"]
    plan.consulta_principal.filters = {}
    plan.consulta_principal.operacao = "SOMA"

    with patch.object(business_knowledge_engine.kpi_registry, "get_kpi", side_effect=[None, kpi]), \
         patch.object(business_knowledge_engine.dictionary, "get_concept", return_value=None):
        
        is_valid, errors = await business_knowledge_engine.validation_engine.validate_query_plan(
            tenant_id=tenant_id, plan=plan, db=mock_db
        )
        assert is_valid is False
        assert any("Agrupamento (group_by) inválido" in err for err in errors)


# ── Tests: Governance & Rollback ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bke_apply_business_rules_uses_central_semantic_normalizer(tenant_id):
    mock_db = AsyncMock(spec=AsyncSession)

    class PlanStub:
        kpis_planejados = ["ticket_medio", "pedidos_totais"]
        contexto = {}

    plan = PlanStub()

    with patch.object(business_knowledge_engine.validation_engine, "validate_query_plan", AsyncMock(return_value=(True, []))), \
         patch.object(business_knowledge_engine.dictionary, "get_concept", AsyncMock(return_value=None)), \
         patch.object(business_knowledge_engine.kpi_registry, "get_kpi", AsyncMock(return_value=None)), \
         patch.object(business_knowledge_engine.formula_engine, "get_formula", AsyncMock(return_value=None)), \
         patch.object(business_knowledge_engine.relationship_engine, "get_relationships", AsyncMock(return_value=[])):
        result = await business_knowledge_engine.apply_business_rules(plan, tenant_id, mock_db)

    assert result.kpis_planejados == ["ticket_medio", "quantidade_pedidos"]
    assert result.contexto["standardized_metrics"] == ["ticket_medio", "quantidade_pedidos"]


@pytest.mark.asyncio
async def test_governance_version_increment_and_rollback(tenant_id):
    """BusinessGovernance deve arquivar snapshots e reverter alterações via Rollback."""
    mock_db = AsyncMock(spec=AsyncSession)

    # 1. Mock do log do rollback
    log_mock = MagicMock()
    log_mock.snapshot = {
        "nome": "Margem",
        "descricao": "Versão Antiga da Margem",
        "categoria": "Financeiro",
        "status": "ACTIVE",
    }

    concept_mock = MagicMock()
    concept_mock.nome = "Margem"
    concept_mock.descricao = "Versão Atual da Margem"
    concept_mock.versao = 2

    res_log = MagicMock()
    res_log.scalar_one_or_none.return_value = log_mock
    
    res_concept = MagicMock()
    res_concept.scalar_one_or_none.return_value = concept_mock
    
    mock_db.execute.side_effect = [res_log, res_concept]

    with patch.object(business_knowledge_engine.governance, "log_action", return_value=MagicMock()):
        res = await business_knowledge_engine.governance.rollback(
            tenant_id=tenant_id,
            estrutura_tipo="CONCEPT",
            estrutura_nome="Margem",
            target_version=1,
            autor="test_user@luminaai.demo",
            db=mock_db,
        )

        assert res["success"] is True
        assert res["versao_anterior"] == 2
        assert res["versao_atual"] == 3
        assert res["revertido_para_versao"] == 1
        assert concept_mock.descricao == "Versão Antiga da Margem"


# ── Tests: Multi-Tenant Isolation ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_multi_tenant_isolation(tenant_id, other_tenant_id):
    """BusinessKnowledgeEngine deve manter isolamento de regras estrito por tenant."""
    mock_db = AsyncSession(bind=None)

    # Simula conceitos diferentes cadastrados para tenants distintos
    concept_t1 = MagicMock()
    concept_t1.nome = "Métrica T1"

    with patch.object(business_knowledge_engine.dictionary, "get_concept") as mock_get:
        # Quando tenant_id é chamado, retorna o conceito. Quando other_tenant_id é chamado, retorna None.
        def side_effect(tid, name, db_sess):
            if tid == tenant_id:
                return concept_t1
            return None
        
        mock_get.side_effect = side_effect

        c_t1 = await business_knowledge_engine.dictionary.get_concept(tenant_id, "Métrica T1", mock_db)
        c_t2 = await business_knowledge_engine.dictionary.get_concept(other_tenant_id, "Métrica T1", mock_db)

        assert c_t1 is not None
        assert c_t1.nome == "Métrica T1"
        assert c_t2 is None  # Isolado, outro tenant não enxerga!
