import pytest
from services.semantic_layer import (
    canonicalize_metric_name,
    get_metric_info,
    resolve_metric_for_view,
    validate_metrics_and_sources,
    register_custom_metric
)
from services.ai_service import StructuredPlanSchema, PlanFiltersSchema, PlanVisualizationSchema
from services.data_platform.business_layer import BusinessLayer
from services.plan_validator import validate_and_normalize_plan


def test_mandatory_metrics_registry():
    # Verifica receita
    rec = get_metric_info("receita_total")
    assert rec is not None
    assert "vendas_aprovadas" in rec["formula"]
    assert "exclui_canceladas" in rec["validation_rules"]

    # Verifica faturamento
    fat = get_metric_info("faturamento")
    assert fat is not None
    assert "todas_as_vendas" in fat["formula"]

    # Verifica lucro
    luc = get_metric_info("lucro_bruto")
    assert luc is not None
    assert "receita_total - custo_total" in luc["formula"]

    # Verifica margem
    marg = get_metric_info("margem_lucro")
    assert marg is not None

    # Verifica ticket médio
    tkt = get_metric_info("ticket_medio")
    assert tkt is not None

    # Verifica cliente ativo
    act = get_metric_info("cliente_ativo")
    assert act is not None
    assert "compra_recente_30d" in act["formula"]

    # Verifica churn
    churn = get_metric_info("churn_rate")
    assert churn is not None

    # Verifica LTV
    ltv = get_metric_info("ltv_estimado")
    assert ltv is not None

    # Verifica CAC
    cac = get_metric_info("cac_estimado")
    assert cac is not None

    # Verifica Conversão
    conv = get_metric_info("taxa_conversao")
    assert conv is not None


def test_validate_metrics_and_sources_compatibility():
    # Receita total com VW_VENDAS_MENSAIS deve passar (sem erros)
    errors = validate_metrics_and_sources(["receita_total"], "VW_VENDAS_MENSAIS")
    assert len(errors) == 0

    # Churn rate com VW_VENDAS_MENSAIS deve falhar (incompatível)
    errors = validate_metrics_and_sources(["churn_rate"], "VW_VENDAS_MENSAIS")
    assert len(errors) > 0
    assert "incompatível" in errors[0]

    # Métrica inexistente deve falhar
    errors = validate_metrics_and_sources(["metrica_inexistente"], "VW_VENDAS_MENSAIS")
    assert len(errors) > 0
    assert "não está cadastrada" in errors[0]


def test_sales_metric_aliases_are_canonicalized_for_detail_view():
    assert canonicalize_metric_name("total_vendas") == "receita_total"
    assert canonicalize_metric_name("total de vendas") == "receita_total"
    assert canonicalize_metric_name("valor total") == "receita_total"
    assert canonicalize_metric_name("valor total de vendas") == "receita_total"
    assert canonicalize_metric_name("valor das vendas") == "receita_total"
    assert canonicalize_metric_name("vendas totais") == "receita_total"
    assert canonicalize_metric_name("totl vendas") == "receita_total"
    assert get_metric_info("total_vendas") == get_metric_info("receita_total")

    errors = validate_metrics_and_sources(["total_vendas"], "VW_DETALHE_PEDIDOS")
    assert errors == []


def test_semantic_normalizer_covers_common_kpi_variations():
    cases = {
        "pedidos_totais": "quantidade_pedidos",
        "total de pedidos": "quantidade_pedidos",
        "quantidade de vendas": "quantidade_pedidos",
        "qtd vendas": "quantidade_pedidos",
        "ticket médio": "ticket_medio",
        "valor_medio_compra": "ticket_medio",
        "margem bruta": "margem_lucro",
        "custo total": "custo_total",
        "taxa de churn": "churn_rate",
        "LTV": "ltv_estimado",
        "CAC": "cac_estimado",
        "taxa de conversão": "taxa_conversao",
    }

    for raw, expected in cases.items():
        assert canonicalize_metric_name(raw) == expected

    assert validate_metrics_and_sources(["pedidos_totais", "ticket médio"], "VW_DETALHE_PEDIDOS") == []


def test_view_metric_equivalents_adapt_seller_ranking_metrics():
    assert resolve_metric_for_view("receita_total", "VW_PERFORMANCE_VENDEDORES") == "valor_vendido"
    assert resolve_metric_for_view("vendas", "VW_PERFORMANCE_VENDEDORES") == "valor_vendido"
    assert resolve_metric_for_view("faturamento_realizado", "VW_PERFORMANCE_VENDEDORES") == "valor_vendido"
    assert resolve_metric_for_view("meta_mensal", "VW_PERFORMANCE_VENDEDORES") == "meta_valor"
    assert resolve_metric_for_view("atingimento_meta", "VW_PERFORMANCE_VENDEDORES") == "atingimento"

    errors = validate_metrics_and_sources(
        ["receita_total", "faturamento_realizado", "meta_mensal", "atingimento_meta"],
        "VW_PERFORMANCE_VENDEDORES",
    )
    assert errors == []


def test_view_metric_equivalents_adapt_product_ranking_metrics():
    assert resolve_metric_for_view("quantidade_pedidos", "VW_PRODUTOS_MAIS_VENDIDOS") == "unidades_vendidas"
    assert resolve_metric_for_view("quantidade vendida", "VW_PRODUTOS_MAIS_VENDIDOS") == "unidades_vendidas"
    assert resolve_metric_for_view("faturamento_realizado", "VW_PRODUTOS_MAIS_VENDIDOS") == "receita_total"
    assert resolve_metric_for_view("margem_lucro", "VW_PRODUTOS_MAIS_VENDIDOS") == "margem_media"

    errors = validate_metrics_and_sources(
        ["quantidade_pedidos", "quantidade vendida", "faturamento_realizado", "margem_lucro"],
        "VW_PRODUTOS_MAIS_VENDIDOS",
    )
    assert errors == []


def test_lm_sales_view_supports_core_sales_metrics():
    assert resolve_metric_for_view("faturamento_realizado", "VW_VENDAS_LM") == "receita_total"
    assert resolve_metric_for_view("valor vendido", "VW_VENDAS_LM") == "receita_total"
    assert resolve_metric_for_view("quantidade vendida", "VW_VENDAS_LM") == "unidades_vendidas"

    errors = validate_metrics_and_sources(
        ["receita_total", "faturamento_realizado", "quantidade_pedidos", "unidades_vendidas", "ticket_medio"],
        "VW_VENDAS_LM",
    )
    assert errors == []


def test_business_layer_uses_central_semantic_normalizer():
    layer = BusinessLayer()

    assert layer._resolve_synonym_local("pedidos_totais") == "quantidade_pedidos"
    assert layer._resolve_synonym_local("valor das vendas") == "receita_total"
    assert layer._resolve_synonym_local("totl vendas") == "receita_total"


def test_register_custom_metric_extensibility():
    # Registra nova métrica
    register_custom_metric(
        name="net_promoter_score",
        definition="Medida de satisfação do cliente baseada em pontuações de 0 a 10.",
        formula="promotores_pct - detratores_pct",
        validation_rules=["escore_valido_0_a_10"],
        data_sources=["VW_NPS_SATISFACAO", "VW_FEEDBACKS"],
        dependencies=[]
    )

    # Verifica registro
    nps = get_metric_info("net_promoter_score")
    assert nps is not None
    assert nps["formula"] == "promotores_pct - detratores_pct"

    # Valida compatibilidade
    errors = validate_metrics_and_sources(["net_promoter_score"], "VW_NPS_SATISFACAO")
    assert len(errors) == 0

    errors = validate_metrics_and_sources(["net_promoter_score"], "VW_VENDAS_MENSAIS")
    assert len(errors) > 0
    assert "incompatível" in errors[0]


def test_validator_integration_with_semantic_layer():
    # Caso 1: Métrica compatível com view
    plan_ok = StructuredPlanSchema(
        request_id="req-sem-1",
        intent="faturamento",
        query_type="SELECT",
        metrics=["receita_total"],
        group_by=[],
        filters=PlanFiltersSchema(date_range="2026-06-01 to 2026-06-30"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )
    res_ok = validate_and_normalize_plan(plan_ok, query_text="Receita em junho", view_name="VW_VENDAS_MENSAIS")
    assert res_ok.validated is True

    # Caso 2: Métrica incompatível com view
    plan_err = StructuredPlanSchema(
        request_id="req-sem-2",
        intent="churn rate",
        query_type="SELECT",
        metrics=["churn_rate"],
        group_by=[],
        filters=PlanFiltersSchema(date_range="2026-06-01 to 2026-06-30"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )
    res_err = validate_and_normalize_plan(plan_err, query_text="Taxa de churn em junho", view_name="VW_VENDAS_MENSAIS")
    assert res_err.validated is False
    assert res_err.error == "INVALID_METRIC"
    assert "incompatível" in res_err.suggested_refinement

    # Caso 3: Métrica desconhecida
    plan_unk = StructuredPlanSchema(
        request_id="req-sem-3",
        intent="metrica desconhecida",
        query_type="SELECT",
        metrics=["alguma_coisa_estranha"],
        group_by=[],
        filters=PlanFiltersSchema(date_range="2026-06-01 to 2026-06-30"),
        visualization=PlanVisualizationSchema(type="BAR", layout_priority="ALTA")
    )
    res_unk = validate_and_normalize_plan(plan_unk, query_text="alguma coisa estranha", view_name="VW_VENDAS_MENSAIS")
    assert res_unk.validated is False
    assert res_unk.error == "INVALID_METRIC"
    assert "não está cadastrada" in res_unk.suggested_refinement
