import pytest
import uuid
from services.roqg_service import roqg
from services.query_planner import QueryPlan, QueryPlanItem
from schemas.roqg import ComponentStatus, DeliveryDecision, ComponentPriority


@pytest.fixture
def dummy_query_plan():
    """Retorna um plano de consulta fictício contendo 3 componentes planejados."""
    principal = QueryPlanItem(
        id="principal",
        view_name="VW_VENDAS_MENSAIS",
        prioridade="ALTA",
        sugestao_visualizacao="BAR",
        objetivo="Análise principal de faturamento"
    )
    comp1 = QueryPlanItem(
        id="composto_1",
        view_name="VW_COMPRAS",
        prioridade="MEDIA",
        sugestao_visualizacao="TABLE",
        objetivo="Top fornecedores"
    )
    comp2 = QueryPlanItem(
        id="composto_2",
        view_name="VW_KPI_EXECUTIVO",
        prioridade="BAIXA",
        sugestao_visualizacao="KPI",
        objetivo="KPI estratégico executivo"
    )
    return QueryPlan(
        consulta_principal=principal,
        consultas_complementares=[comp1, comp2],
        ordem_execucao=[["principal", "composto_1"], ["composto_2"]]
    )


@pytest.mark.anyio
async def test_roqg_full_rendering(dummy_query_plan):
    """ROQG deve aprovar renderização completa caso todas as consultas executem com sucesso."""
    tenant_id = uuid.uuid4()
    resultados_dict = {
        "principal": {"view_name": "VW_VENDAS_MENSAIS", "raw_rows": [{"faturamento": 100}], "sugestao_visualizacao": "BAR", "view_catalog_id": uuid.uuid4()},
        "composto_1": {"view_name": "VW_COMPRAS", "raw_rows": [{"compra": 50}], "sugestao_visualizacao": "TABLE", "view_catalog_id": uuid.uuid4()},
        "composto_2": {"view_name": "VW_KPI_EXECUTIVO", "raw_rows": [{"kpi": 1}], "sugestao_visualizacao": "KPI", "view_catalog_id": uuid.uuid4()}
    }

    response = await roqg.process(
        tenant_id=tenant_id,
        query_text="vendas e compras",
        analytical_package=None,
        query_plan=dummy_query_plan,
        resultados_dict=resultados_dict
    )

    assert response.audited is True
    assert response.render_plan.completeness_score == 100.0
    assert response.render_plan.decision == DeliveryDecision.FULL_RENDERING
    assert len(response.render_plan.componentes) == 3
    assert response.render_plan.componentes[0].status == ComponentStatus.AVAILABLE


@pytest.mark.anyio
async def test_roqg_partial_rendering_degradation(dummy_query_plan):
    """ROQG deve degradar para renderização parcial caso componentes secundários falhem."""
    tenant_id = uuid.uuid4()
    # "composto_2" (prioridade BAIXA) falhou na execução
    resultados_dict = {
        "principal": {"view_name": "VW_VENDAS_MENSAIS", "raw_rows": [{"faturamento": 100}], "sugestao_visualizacao": "BAR", "view_catalog_id": uuid.uuid4()},
        "composto_1": {"view_name": "VW_COMPRAS", "raw_rows": [{"compra": 50}], "sugestao_visualizacao": "TABLE", "view_catalog_id": uuid.uuid4()}
    }

    response = await roqg.process(
        tenant_id=tenant_id,
        query_text="vendas e compras",
        analytical_package=None,
        query_plan=dummy_query_plan,
        resultados_dict=resultados_dict
    )

    # Score de completude deve refletir a falha de composto_2 de forma ponderada
    assert response.render_plan.completeness_score < 100.0
    assert response.render_plan.completeness_score >= 80.0
    assert response.render_plan.decision == DeliveryDecision.PARTIAL_RENDERING
    
    # Composto 2 deve usar placeholder de negócio
    comp_fail = next(c for c in response.render_plan.componentes if c.id == "composto_2")
    assert comp_fail.status == ComponentStatus.FAILED
    assert "Falha temporária" in comp_fail.mensagem
    assert comp_fail.placeholder is not None


@pytest.mark.anyio
async def test_roqg_unavailable_on_critical_failure(dummy_query_plan):
    """ROQG deve retornar resposta indisponível se a consulta principal (crítica) falhar."""
    tenant_id = uuid.uuid4()
    # Apenas o KPI opcional executou, a consulta principal falhou
    resultados_dict = {
        "composto_2": {"view_name": "VW_KPI_EXECUTIVO", "raw_rows": [{"kpi": 1}], "sugestao_visualizacao": "KPI", "view_catalog_id": uuid.uuid4()}
    }

    response = await roqg.process(
        tenant_id=tenant_id,
        query_text="vendas e compras",
        analytical_package=None,
        query_plan=dummy_query_plan,
        resultados_dict=resultados_dict
    )

    # Como a consulta principal (peso 4) falhou, o score geral despenca abaixo de 60%
    assert response.render_plan.completeness_score < 60.0
    assert response.render_plan.decision == DeliveryDecision.UNAVAILABLE
    
    # Todos os componentes devem ser bloqueados e instruídos a exibir placeholders de erro geral
    for comp in response.render_plan.componentes:
        assert comp.status == ComponentStatus.BLOCKED
        assert "indisponível" in comp.mensagem.lower()


@pytest.mark.anyio
async def test_roqg_nan_infinity_sanitization(dummy_query_plan):
    """ROQG deve higienizar valores inválidos NaN/Infinity de floats nos dados analíticos."""
    tenant_id = uuid.uuid4()
    import math
    resultados_dict = {
        "principal": {
            "view_name": "VW_VENDAS_MENSAIS",
            "raw_rows": [{"faturamento": 100.0, "nan_val": float('nan'), "inf_val": float('inf')}],
            "sugestao_visualizacao": "BAR",
            "view_catalog_id": uuid.uuid4()
        },
        "composto_1": {"view_name": "VW_COMPRAS", "raw_rows": [{"compra": 50}], "sugestao_visualizacao": "TABLE", "view_catalog_id": uuid.uuid4()},
        "composto_2": {"view_name": "VW_KPI_EXECUTIVO", "raw_rows": [{"kpi": 1}], "sugestao_visualizacao": "KPI", "view_catalog_id": uuid.uuid4()}
    }

    response = await roqg.process(
        tenant_id=tenant_id,
        query_text="vendas",
        analytical_package=None,
        query_plan=dummy_query_plan,
        resultados_dict=resultados_dict
    )

    assert response.render_plan.decision == DeliveryDecision.FULL_RENDERING
    assert len(response.audit_notes) > 0
    # O valor float de NaN deve ter sido limpo e transformado em None (que é serializado como null no JSON)
    assert any("NaN/Inf" in note for note in response.audit_notes)
