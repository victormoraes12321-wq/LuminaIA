from decimal import Decimal

from services.erp_reconciliation import OFFICIAL_ERP_FILTERS, erp_reconciliation


def test_reconciliation_contract_documents_exact_filters():
    assert "tp_ IN (2, 61)" in OFFICIAL_ERP_FILTERS["commercial_revenue"]
    assert "tp_ = 9" in OFFICIAL_ERP_FILTERS["saida_rb"]
    assert "DEVOL" in OFFICIAL_ERP_FILTERS["devolucao"]
    assert "transferencias" in OFFICIAL_ERP_FILTERS["total_bruto"]
    assert "PADRAO" in OFFICIAL_ERP_FILTERS["vendedor_ranking_exclusion"]
    assert "LAGES E LOPES LTDA" in OFFICIAL_ERP_FILTERS["cliente_ranking_exclusion"]
    assert "cfop_" in OFFICIAL_ERP_FILTERS["cfop"]


def test_reconciliation_period_parser_uses_inclusive_month_and_exclusive_upper_bound():
    period = erp_reconciliation.parse_period("2026-07")

    assert period.start_date.isoformat() == "2026-07-01"
    assert period.end_date.isoformat() == "2026-07-31"
    assert period.end_exclusive.isoformat() == "2026-08-01"


def test_compare_period_reports_detects_value_mismatch():
    clone = {
        "faturamento_total": {"faturamento_comercial": 100.00, "total_bruto": 120.00},
        "saida_rb": {"valor": 10.00},
        "devolucao": {"valor": 0.00},
        "ticket_medio": {"valor": 50.00},
        "faturamento_por_filial": [{"filial": "1", "faturamento_comercial": 100.00, "saida_rb": 10.00, "devolucao": 0.00}],
        "ranking_vendedores": [{"vendedor": "A", "valor_ranking": 100.00}],
        "ranking_vendedores_rb": [{"vendedor": "A", "valor_ranking": 10.00}],
        "ranking_vendedores_devolucao": [],
        "top_clientes": [{"cliente": "C", "valor_ranking": 100.00}],
    }
    erp = {
        "status": "ok",
        "faturamento_total": {"faturamento_comercial": 99.00, "total_bruto": 120.00},
        "saida_rb": {"valor": 10.00},
        "devolucao": {"valor": 0.00},
        "ticket_medio": {"valor": 50.00},
        "faturamento_por_filial": [{"filial": "1", "faturamento_comercial": 99.00, "saida_rb": 10.00, "devolucao": 0.00}],
        "ranking_vendedores": [{"vendedor": "A", "valor_ranking": 99.00}],
        "ranking_vendedores_rb": [{"vendedor": "A", "valor_ranking": 10.00}],
        "ranking_vendedores_devolucao": [],
        "top_clientes": [{"cliente": "C", "valor_ranking": 99.00}],
    }

    comparison = erp_reconciliation.compare_period_reports(clone, erp)

    assert comparison["status"] == "mismatch"
    assert any(check["name"] == "faturamento_total" for check in comparison["failed_checks"])


def test_dimension_aggregation_keeps_one_row_per_vendor_with_filial_details():
    rows = erp_reconciliation._aggregate_dimension_rows(
        [
            {"vendedor": "A", "filial": "1", "faturamento_comercial": Decimal("10"), "saida_rb": 1, "devolucao": 0, "total_bruto": 11, "pedidos_comerciais": 1, "pedidos_total": 2},
            {"vendedor": "A", "filial": "2", "faturamento_comercial": Decimal("20"), "saida_rb": 2, "devolucao": 0, "total_bruto": 22, "pedidos_comerciais": 1, "pedidos_total": 2},
        ],
        "vendedor",
        "faturamento_comercial",
    )

    assert len(rows) == 1
    assert rows[0]["vendedor"] == "A"
    assert rows[0]["valor_ranking"] == Decimal("30.00")
    assert len(rows[0]["por_filial"]) == 2
