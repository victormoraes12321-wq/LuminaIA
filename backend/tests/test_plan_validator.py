import pytest
from datetime import date
from services.ai_service import StructuredPlanSchema, PlanFiltersSchema, PlanVisualizationSchema
from services.plan_validator import (
    validate_and_normalize_plan,
    resolve_relative_date_range,
    ANCHOR_DATE
)


def test_resolve_relative_date_range():
    # Hoje: 2026-07-03
    assert resolve_relative_date_range("hoje") == ("2026-07-03", "2026-07-03")
    assert resolve_relative_date_range("ontem") == ("2026-07-02", "2026-07-02")
    assert resolve_relative_date_range("este mês") == ("2026-07-01", "2026-07-31")
    assert resolve_relative_date_range("mês passado") == ("2026-06-01", "2026-06-30")
    assert resolve_relative_date_range("este ano") == ("2026-01-01", "2026-12-31")
    assert resolve_relative_date_range("ano passado") == ("2025-01-01", "2025-12-31")
    assert resolve_relative_date_range("últimos 7 dias") == ("2026-06-27", "2026-07-03")
    assert resolve_relative_date_range("Q1") == ("2026-01-01", "2026-03-31")
    assert resolve_relative_date_range("dia 05/06/2026") == ("2026-06-05", "2026-06-05")
    assert resolve_relative_date_range("mes 04/2026") == ("2026-04-01", "2026-04-30")
    assert resolve_relative_date_range("meses 2, 3 e 4 de 2026") == ("2026-02-01", "2026-04-30")


def test_plan_validator_valid_plan():
    plan = StructuredPlanSchema(
        request_id="test-req-id",
        intent="analisar performance de vendas",
        query_type="SELECT",
        metrics=["receita_total"],
        group_by=["vendedor"],
        filters=PlanFiltersSchema(date_range="2026-06-01 to 2026-06-30"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(plan, query_text="Qual a receita de cada vendedor em junho?")
    assert res.validated is True
    assert res.corrected is False
    assert res.metrics == ["receita_total"]
    assert res.filters["date_range"] == "2026-06-01 to 2026-06-30"
    assert res.visualization["type"] == "BAR"


def test_plan_validator_vague_query_expansion():
    plan = StructuredPlanSchema(
        request_id="test-req-id",
        intent="vendas hoje",
        query_type="SELECT",
        metrics=[],
        group_by=[],
        filters=PlanFiltersSchema(date_range="hoje"),
        visualization=PlanVisualizationSchema(type="", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(plan, query_text="vendas hoje")
    assert res.validated is True
    assert res.corrected is True
    assert "receita_total" in res.metrics
    assert "quantidade_pedidos" in res.metrics
    assert "ticket_medio" in res.metrics
    assert res.filters["date_range"] == "2026-07-03 to 2026-07-03"
    # Auto-corrected visualization type for sales overview
    assert res.visualization["type"] == "BAR"


def test_plan_validator_normalizes_total_sales_alias_from_ai():
    plan = StructuredPlanSchema(
        request_id="test-req-total-vendas",
        intent="total vendido no dia",
        query_type="SELECT",
        metrics=["total_vendas"],
        group_by=[],
        filters=PlanFiltersSchema(date_range="2026-06-05 to 2026-06-05"),
        visualization=PlanVisualizationSchema(type="KPI", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(
        plan,
        query_text="Quanto vendeu no total no dia 05/06/2026?",
        view_name="VW_DETALHE_PEDIDOS",
    )
    assert res.validated is True
    assert res.corrected is True
    assert res.metrics == ["receita_total"]
    assert res.filters["date_range"] == "2026-06-05 to 2026-06-05"


def test_plan_validator_adapts_financial_metrics_to_seller_performance_view():
    plan = StructuredPlanSchema(
        request_id="test-req-ranking-sellers",
        intent="ranking dos vendedores",
        query_type="RANKING",
        metrics=["faturamento_realizado", "meta_mensal", "atingimento_meta"],
        group_by=["vendedor"],
        filters=PlanFiltersSchema(date_range="04/2026"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )

    res = validate_and_normalize_plan(
        plan,
        query_text="Ranking dos vendedores no mês 04/2026",
        view_name="VW_PERFORMANCE_VENDEDORES",
    )

    assert res.validated is True
    assert res.metrics == ["valor_vendido", "meta_valor", "atingimento"]
    assert res.filters["date_range"] == "2026-04-01 to 2026-04-30"




def test_plan_validator_adapts_generic_sales_metric_to_seller_performance_view():
    plan = StructuredPlanSchema(
        request_id="test-req-ranking-sellers-generic-sales",
        intent="ranking dos vendedores",
        query_type="RANKING",
        metrics=["receita_total"],
        group_by=["vendedor"],
        filters=PlanFiltersSchema(date_range="04/2026"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )

    res = validate_and_normalize_plan(
        plan,
        query_text="Ranking dos vendedores no mes 04/2026",
        view_name="VW_PERFORMANCE_VENDEDORES",
    )

    assert res.validated is True
    assert res.metrics == ["valor_vendido"]
    assert res.filters["date_range"] == "2026-04-01 to 2026-04-30"


def test_plan_validator_adapts_product_quantity_metric_to_product_ranking_view():
    plan = StructuredPlanSchema(
        request_id="test-req-product-ranking",
        intent="produtos mais vendidos",
        query_type="RANKING",
        metrics=["quantidade_pedidos", "receita_total"],
        group_by=["produto_nome"],
        filters=PlanFiltersSchema(date_range="ultimos 3 meses"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )

    res = validate_and_normalize_plan(
        plan,
        query_text="Quais os produtos mais vendidos nos ultimos 3 meses?",
        view_name="VW_PRODUTOS_MAIS_VENDIDOS",
    )

    assert res.validated is True
    assert res.metrics == ["unidades_vendidas", "receita_total"]
    assert res.filters["date_range"] == "2026-04-05 to 2026-07-03"


def test_plan_validator_lucro_mapping():
    plan = StructuredPlanSchema(
        request_id="test-req-id",
        intent="analisar lucro",
        query_type="SELECT",
        metrics=["lucro"],
        group_by=[],
        filters=PlanFiltersSchema(date_range="2026-06-01 to 2026-06-30"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(plan, query_text="Quero ver o lucro obtido")
    assert res.validated is True
    assert res.corrected is True
    assert "lucro_bruto" in res.metrics
    assert "margem_lucro" in res.metrics
    assert "lucro" not in res.metrics


def test_plan_validator_top_product_group_by():
    plan = StructuredPlanSchema(
        request_id="test-req-id",
        intent="top produto",
        query_type="SELECT",
        metrics=["receita_total"],
        group_by=[],
        filters=PlanFiltersSchema(date_range="2026-06-01 to 2026-06-30"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(plan, query_text="quais os top produtos vendidos?")
    assert res.validated is True
    assert res.corrected is True
    assert "produto_nome" in res.group_by


def test_plan_validator_missing_period_fallback():
    plan = StructuredPlanSchema(
        request_id="test-req-id",
        intent="faturamento",
        query_type="SELECT",
        metrics=["receita_total"],
        group_by=[],
        filters=PlanFiltersSchema(date_range=""),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(plan, query_text="faturamento geral")
    assert res.validated is True
    assert res.corrected is True
    assert res.fallback_applied is True
    assert res.filters["date_range"] == "2026-07-01 to 2026-07-31"


def test_plan_validator_extracts_brazilian_absolute_date_from_query_text():
    plan = StructuredPlanSchema(
        request_id="test-req-date-from-query",
        intent="total vendido no dia",
        query_type="SELECT",
        metrics=["total_vendas"],
        group_by=[],
        filters=PlanFiltersSchema(date_range=""),
        visualization=PlanVisualizationSchema(type="KPI", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(
        plan,
        query_text="Quanto vendeu no total no dia 05/06/2026?",
        view_name="VW_DETALHE_PEDIDOS",
    )
    assert res.validated is True
    assert res.metrics == ["receita_total"]
    assert res.filters["date_range"] == "2026-06-05 to 2026-06-05"
    assert res.fallback_applied is False


def test_plan_validator_prioritizes_explicit_query_date_over_inferred_period():
    plan = StructuredPlanSchema(
        request_id="test-req-date-override",
        intent="total vendido no dia",
        query_type="SELECT",
        metrics=["total_vendas"],
        group_by=[],
        filters=PlanFiltersSchema(date_range="2026-07-01 to 2026-07-31"),
        visualization=PlanVisualizationSchema(type="KPI", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(
        plan,
        query_text="Quanto vendeu no total no dia 05/06/2026?",
        view_name="VW_DETALHE_PEDIDOS",
    )
    assert res.validated is True
    assert res.metrics == ["receita_total"]
    assert res.filters["date_range"] == "2026-06-05 to 2026-06-05"


def test_plan_validator_conflicting_dates_swap():
    plan = StructuredPlanSchema(
        request_id="test-req-id",
        intent="vendas",
        query_type="SELECT",
        metrics=["receita_total"],
        group_by=[],
        filters=PlanFiltersSchema(date_range="2026-07-31 to 2026-07-01"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(plan, query_text="faturamento")
    assert res.validated is True
    assert res.corrected is True
    assert res.filters["date_range"] == "2026-07-01 to 2026-07-31"


def test_plan_validator_visualization_auto_correction():
    plan = StructuredPlanSchema(
        request_id="test-req-id",
        intent="analisar evolucao das vendas",
        query_type="TIME_SERIES",
        metrics=["receita_total"],
        group_by=["mes"],
        filters=PlanFiltersSchema(date_range="2026-01-01 to 2026-12-31"),
        visualization=PlanVisualizationSchema(type="", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(plan, query_text="Qual a evolução das vendas mês a mês?")
    assert res.validated is True
    assert res.corrected is True
    assert res.visualization["type"] == "LINE"


def test_plan_validator_rejection():
    # Intent ausente/muito curto
    plan = StructuredPlanSchema(
        request_id="test-req-id",
        intent="",
        query_type="SELECT",
        metrics=["receita_total"],
        group_by=[],
        filters=PlanFiltersSchema(date_range="2026-01-01 to 2026-12-31"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )
    res = validate_and_normalize_plan(plan, query_text="...")
    assert res.validated is False
    assert res.error == "INSUFFICIENT_INFORMATION"
    assert res.suggested_refinement is not None
