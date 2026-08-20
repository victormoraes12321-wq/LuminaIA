from services.sales_value_breakdown import sales_value_breakdown
from models.view_catalog import ChartType
from services.data_transformer import transform_data


def test_sales_value_breakdown_exposes_all_value_categories():
    assert sales_value_breakdown.CATEGORY_VALUE_KEYS == (
        "faturamento_comercial",
        "saida_rb",
        "devolucao",
        "venda_bonificada",
        "transferencias",
        "outras_vendas",
        "remessa_uso_consumo",
        "outros_movimentos",
    )


def test_sales_value_breakdown_keeps_erp_commercial_filter_compatible():
    assert sales_value_breakdown.commercial_filter_sql("lm") == "lm.tp_ IN (2, 61)"
    assert sales_value_breakdown.default_binds() == {}


def test_sales_value_breakdown_can_scope_commercial_filter_by_filial():
    assert sales_value_breakdown.commercial_filter_sql("lm", filial="05") == "lm.tp_ IN (2, 61) AND lm.filial_ = :sales_filial"
    assert sales_value_breakdown.default_binds("05") == {"sales_filial": "5"}


def test_sales_value_breakdown_uses_explicit_discount_column_when_available():
    assert sales_value_breakdown.discount_expr_sql("lm", "vldesc") == 'COALESCE(lm."vldesc", 0)'


def test_sales_value_breakdown_classifies_hidden_value_types():
    category_sql = sales_value_breakdown.category_case_sql("lm")

    assert "faturamento_comercial" in category_sql
    assert "venda_bonificada" in category_sql
    assert "saida_rb" in category_sql
    assert "devolucao" in category_sql
    assert "transferencias" in category_sql
    assert "outras_vendas" in category_sql
    assert "remessa_uso_consumo" in category_sql


def test_breakdown_value_columns_are_rendered_as_currency():
    chart_data = transform_data(
        [
            {
                "vendedor": "VENDEDOR TESTE",
                "filial": "1",
                "faturamento_comercial": 100.0,
                "saida_rb": 5.0,
                "devolucao": 1.0,
                "venda_bonificada": 2.0,
                "transferencias": 3.0,
                "outras_vendas": 4.0,
                "remessa_uso_consumo": 6.0,
                "outros_movimentos": 0.0,
                "total_bruto": 140.0,
                "total_movimentos_view": 143.0,
                "valor_filial": 100.0,
                "faturamento_comercial_total": 100.0,
                "total_bruto_total": 140.0,
                "total_movimentos_view_total": 143.0,
                "ticket_medio_comercial": 50.0,
                "ticket_medio_bruto": 46.67,
                "desconto_medio_comercial": 1.0,
                "desconto_medio_total": 2.33,
                "desconto_total_periodo": 7.0,
                "pedidos_total": 3,
            }
        ],
        ChartType.TABLE,
    )

    column_types = {column["key"]: column["type"] for column in chart_data["columns"]}
    for key in sales_value_breakdown.CATEGORY_VALUE_KEYS + ("total_bruto",):
        assert column_types[key] == "currency"
    assert column_types["pedidos_total"] == "number"


def test_table_transformer_keeps_columns_that_appear_after_first_row():
    chart_data = transform_data(
        [
            {"filial": "Todas", "faturamento_comercial": 100.0},
            {"indicador": "Ticket medio comercial", "valor": 50.0, "valor_formatado": "R$ 50,00"},
        ],
        ChartType.TABLE,
    )

    column_keys = [column["key"] for column in chart_data["columns"]]
    assert "filial" in column_keys
    assert "indicador" in column_keys
    assert "valor" in column_keys
    assert chart_data["rows"][0]["indicador"] is None


def test_prefixed_filial_breakdown_columns_are_rendered_as_currency():
    chart_data = transform_data(
        [
            {
                "vendedor": "VENDEDOR TESTE",
                "filial_1_saida_rb": 10.0,
                "filial_1_venda_bonificada": 5.0,
                "filial_1_faturamento_comercial": 100.0,
                "valor_total": 100.0,
            }
        ],
        ChartType.TABLE,
    )

    column_types = {column["key"]: column["type"] for column in chart_data["columns"]}
    assert column_types["filial_1_saida_rb"] == "currency"
    assert column_types["filial_1_venda_bonificada"] == "currency"
    assert column_types["filial_1_faturamento_comercial"] == "currency"


def test_prefixed_order_count_columns_are_not_rendered_as_currency():
    chart_data = transform_data(
        [
            {
                "vendedor": "VENDEDOR TESTE",
                "filial_1_pedidos_saida_rb": 5,
                "pedidos_saida_rb_total": 8,
                "filial_1_saida_rb": 100.0,
            }
        ],
        ChartType.TABLE,
    )

    column_types = {column["key"]: column["type"] for column in chart_data["columns"]}
    assert column_types["filial_1_pedidos_saida_rb"] == "number"
    assert column_types["pedidos_saida_rb_total"] == "number"
    assert column_types["filial_1_saida_rb"] == "currency"
