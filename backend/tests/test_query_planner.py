import uuid

from models.view_catalog import ChartType
from schemas.view_catalog import ViewCatalogSummary
from services.ai_service import IntentionResponse, StructuredPlanSchema
from services.query_planner import create_query_plan


def _view(name: str, description: str, chart: ChartType = ChartType.BAR) -> ViewCatalogSummary:
    return ViewCatalogSummary(
        id=uuid.uuid4(),
        nome_view_oracle=name,
        descricao_para_ia=description,
        tipo_grafico_padrao=chart,
        parametros_schema={},
    )


def test_query_planner_guard_corrects_seller_intent_from_generic_sales_view():
    sales_view = _view("VW_VENDAS_MENSAIS", "Faturamento mensal consolidado por periodo.")
    seller_view = _view("VW_PERFORMANCE_VENDEDORES", "Ranking e performance de vendedores por faturamento.")

    intention = IntentionResponse(
        view_catalog_id=sales_view.id,
        confianca=0.72,
        parametros={},
        operacao="RANKING",
        entidade_alvo="VENDEDOR",
        plano_estruturado=StructuredPlanSchema(
            request_id="req-planner-guard-seller",
            intent="ranking_vendedores",
            query_type="ranking",
            metrics=["receita_total"],
            group_by=["vendedor"],
        ),
    )

    plan = create_query_plan([intention], [sales_view, seller_view])

    assert plan.consulta_principal.view_catalog_id == seller_view.id
    assert plan.consulta_principal.view_name == "VW_PERFORMANCE_VENDEDORES"
    assert intention.view_catalog_id == seller_view.id


def test_query_planner_guard_corrects_product_intent_from_generic_sales_view():
    sales_view = _view("VW_VENDAS_MENSAIS", "Faturamento mensal consolidado por periodo.")
    product_view = _view("VW_PRODUTOS_MAIS_VENDIDOS", "Produtos mais vendidos, ranking de itens e quantidade vendida.")

    intention = IntentionResponse(
        view_catalog_id=sales_view.id,
        confianca=0.72,
        parametros={},
        operacao="RANKING",
        entidade_alvo="PRODUTO",
        plano_estruturado=StructuredPlanSchema(
            request_id="req-planner-guard-product",
            intent="ranking_produtos",
            query_type="ranking",
            metrics=["quantidade_vendida"],
            group_by=["produto_nome"],
        ),
    )

    plan = create_query_plan([intention], [sales_view, product_view])

    assert plan.consulta_principal.view_catalog_id == product_view.id
    assert plan.consulta_principal.view_name == "VW_PRODUTOS_MAIS_VENDIDOS"
    assert intention.view_catalog_id == product_view.id

from services.query_intelligence_engine import _extract_explicit_row_limit, _apply_explicit_row_limit


def test_query_planner_carries_quantity_limit_into_physical_parameters():
    sales_view = _view("VW_VENDAS_MENSAIS", "Faturamento mensal consolidado por periodo.")
    seller_view = _view("VW_PERFORMANCE_VENDEDORES", "Ranking e performance de vendedores por faturamento.")

    intention = IntentionResponse(
        view_catalog_id=seller_view.id,
        confianca=0.72,
        parametros={},
        operacao="RANKING",
        entidade_alvo="VENDEDOR",
        quantidade_limite=3,
        plano_estruturado=StructuredPlanSchema(
            request_id="req-planner-limit-seller",
            intent="ranking_vendedores",
            query_type="ranking",
            metrics=["receita_total"],
            group_by=["vendedor"],
        ),
    )

    plan = create_query_plan([intention], [sales_view, seller_view])

    assert plan.consulta_principal.parametros["limite"] == "3"


def test_qie_extracts_and_applies_explicit_top_limit_to_reused_intent():
    limit = _extract_explicit_row_limit("Qual o top 3 de vendedores nos meses 2, 3 e 4 de 2026?")
    intention = IntentionResponse(
        view_catalog_id=uuid.uuid4(),
        confianca=0.99,
        parametros={"data_inicio": "2026-02-01"},
        operacao="RANKING",
        entidade_alvo="VENDEDOR",
    )

    _apply_explicit_row_limit([intention], limit)

    assert limit == 3
    assert intention.quantidade_limite == 3
    assert intention.parametros["limite"] == "3"


def test_query_planner_guard_routes_single_day_sales_to_daily_context_view():
    monthly_view = _view("VW_VENDAS_MENSAIS", "Faturamento mensal consolidado por periodo.")
    daily_view = _view("VW_VENDAS_CONTEXTO_GERAL", "Vendas diarias detalhadas por data_ref e contexto geral.")

    intention = IntentionResponse(
        view_catalog_id=monthly_view.id,
        confianca=0.99,
        parametros={"data_inicio": "2026-06-05", "data_fim": "2026-06-05"},
        operacao="SOMA",
        entidade_alvo="VENDA",
        plano_estruturado=StructuredPlanSchema(
            request_id="req-planner-guard-daily-sales",
            intent="valor_vendas_dia",
            query_type="aggregation",
            metrics=["receita_total"],
            group_by=[],
        ),
    )

    plan = create_query_plan([intention], [monthly_view, daily_view])

    assert plan.consulta_principal.view_catalog_id == daily_view.id
    assert plan.consulta_principal.view_name == "VW_VENDAS_CONTEXTO_GERAL"
