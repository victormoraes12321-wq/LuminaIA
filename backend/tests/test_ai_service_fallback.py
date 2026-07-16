import uuid

from models.view_catalog import ChartType
from schemas.view_catalog import ViewCatalogSummary
from services.ai_service import _build_deterministic_fallback_intention


def test_deterministic_intent_fallback_handles_top_sellers_multi_month_query():
    seller_view_id = uuid.uuid4()
    catalog = [
        ViewCatalogSummary(
            id=seller_view_id,
            nome_view_oracle="VW_PERFORMANCE_VENDEDORES",
            descricao_para_ia="Performance de vendedores por faturamento e metas.",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={"vendedor": {"type": "string"}, "valor_vendido": {"type": "number"}},
        )
    ]

    intention = _build_deterministic_fallback_intention(
        pergunta="Qual o top 3 de vendedores que mais venderam juntando os meses 2, 3 e 4 de 2026?",
        catalog=catalog,
        request_id="req-fallback-seller-ranking",
        reason="AuthenticationError",
    )

    assert intention.view_catalog_id == seller_view_id
    assert intention.entidade_alvo == "VENDEDOR"
    assert intention.operacao == "RANKING"
    assert intention.quantidade_limite == 3
    assert intention.plano_estruturado is not None
    assert intention.plano_estruturado.filters.date_range == "2026-02-01 to 2026-04-30"
    assert intention.plano_estruturado.group_by == ["vendedor_nome"]


def test_deterministic_intent_fallback_handles_brazilian_single_day_date():
    catalog = [
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_VENDAS_CONTEXTO_GERAL",
            descricao_para_ia="Vendas diarias detalhadas por data_ref.",
            tipo_grafico_padrao=ChartType.TABLE,
            parametros_schema={},
        )
    ]

    intention = _build_deterministic_fallback_intention(
        pergunta="Qual foi o valor das vendas em 05/06/2026?",
        catalog=catalog,
        request_id="req-fallback-single-day",
        reason="AuthenticationError",
    )

    assert intention.view_catalog_id == catalog[0].id
    assert intention.plano_estruturado is not None
    assert intention.plano_estruturado.filters.date_range == "2026-06-05 to 2026-06-05"
    assert intention.parametros["date_range"] == "2026-06-05 to 2026-06-05"


def test_deterministic_intent_fallback_handles_lowest_product_margin():
    sales_view_id = uuid.uuid4()
    catalog = [
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_PRODUTOS_CAD_LM",
            descricao_para_ia="Cadastro mestre de produtos.",
            tipo_grafico_padrao=ChartType.TABLE,
            parametros_schema={},
        ),
        ViewCatalogSummary(
            id=sales_view_id,
            nome_view_oracle="VW_VENDAS_LM",
            descricao_para_ia="Vendas por produto com receita, lucro e margem.",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={},
        ),
    ]

    intention = _build_deterministic_fallback_intention(
        pergunta="Qual o produto com menor margem de lucro?",
        catalog=catalog,
        request_id="req-lowest-margin",
        reason="AuthenticationError",
    )

    assert intention.view_catalog_id == sales_view_id
    assert intention.entidade_alvo == "PRODUTO"
    assert intention.operacao == "RANKING"
    assert intention.quantidade_limite == 1
    assert intention.parametros["_order_metric"] == "margem_lucro"
    assert intention.parametros["_order_direction"] == "ASC"
    assert "codigo_produto" not in intention.parametros
    assert intention.plano_estruturado is not None
    assert intention.plano_estruturado.metrics == ["margem_lucro", "lucro_bruto", "receita_total"]
    assert intention.plano_estruturado.group_by == ["produto_nome"]


def test_deterministic_intent_fallback_treats_sku_margin_as_analysis_not_lookup():
    sales_view_id = uuid.uuid4()
    catalog = [
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_PRODUTOS_CAD_LM",
            descricao_para_ia="Cadastro mestre de produtos e SKUs.",
            tipo_grafico_padrao=ChartType.TABLE,
            parametros_schema={},
        ),
        ViewCatalogSummary(
            id=sales_view_id,
            nome_view_oracle="VW_VENDAS_LM",
            descricao_para_ia="Vendas por SKU/produto com margem e lucro.",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={},
        ),
    ]

    intention = _build_deterministic_fallback_intention(
        pergunta="Qual o sku com mais baixa margem?",
        catalog=catalog,
        request_id="req-sku-margin",
        reason="AuthenticationError",
    )

    assert intention.view_catalog_id == sales_view_id
    assert intention.entidade_alvo == "PRODUTO"
    assert intention.chart_type_sobrescrever == "BAR"
    assert intention.parametros["_order_metric"] == "margem_lucro"
    assert intention.parametros["_order_direction"] == "ASC"
    assert "codigo_produto" not in intention.parametros
    assert intention.plano_estruturado is not None
    assert "margem_lucro" in intention.plano_estruturado.metrics
    assert "produto_nome" in intention.plano_estruturado.group_by
