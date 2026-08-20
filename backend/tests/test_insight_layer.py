from decimal import Decimal
from datetime import datetime

from services.data_platform.insight_layer import InsightLayer


def test_insight_layer_uses_backend_deterministic_total_for_sales_value():
    rows = [
        {
            "data_referencia": datetime(2026, 6, 5),
            "receita_total": Decimal("100.10"),
        },
        {
            "data_referencia": datetime(2026, 6, 5),
            "receita_total": Decimal("200.20"),
        },
    ]
    bi_intelligence = {
        "kpis": {
            "receita_total": 300.30,
            "total_registros": 2,
        }
    }

    report = InsightLayer()._build_deterministic_report(
        pergunta="Qual foi o valor das vendas em 05/06/2026?",
        principal_view_name="VW_VENDAS_CONTEXTO_GERAL",
        raw_rows=rows,
        bi_intelligence=bi_intelligence,
    )

    assert report is not None
    assert "R$ 300,30" in report
    assert "05/06/2026" in report
    assert "2 registros" in report


def test_insight_layer_reports_product_lowest_margin_from_backend_rows():
    rows = [
        {
            "PRODUTO_NOME": "Calcario Premium",
            "MARGEM_LUCRO": Decimal("4.25"),
            "LUCRO_BRUTO": Decimal("120.50"),
            "RECEITA_TOTAL": Decimal("2835.00"),
        }
    ]

    report = InsightLayer()._build_deterministic_report(
        pergunta="Qual o produto com menor margem de lucro?",
        principal_view_name="VW_VENDAS_LM",
        raw_rows=rows,
        bi_intelligence={},
    )

    assert report is not None
    assert "Calcario Premium" in report
    assert "menor margem de lucro" in report
    assert "4.25%" in report
    assert "R$ 2.835,00" in report
