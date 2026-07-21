from services.metric_registry import core_sales_metric_audit


def test_metric_registry_documents_core_sales_formula_and_filters():
    audit = core_sales_metric_audit(
        topics={"faturamento"},
        value_basis="liquido",
        ranking_kind=None,
        primary_metric="faturamento_comercial",
        period_label="2026-07-01 a 2026-07-31",
        filial=None,
    )

    metrics = {item["key"]: item for item in audit["metric_definitions"]}

    assert audit["registry_version"] == "2026-07-20-rb-devolucao-transferencias"
    assert metrics["faturamento_comercial"]["source"] == "VW_VENDAS_LM"
    assert "tp_ IN (2, 61)" in metrics["faturamento_comercial"]["formula"]
    assert "Mantem todas as filiais" in audit["calculation_steps"][1]["detail"]


def test_metric_registry_marks_discount_runtime_source_confidence():
    audit = core_sales_metric_audit(
        topics={"desconto"},
        value_basis="liquido",
        ranking_kind=None,
        primary_metric="faturamento_comercial",
        period_label="2026-07-01 a 2026-07-31",
        filial="3",
        discount_source={
            "desconto_fonte_tipo": "coluna_explicita",
            "desconto_fonte_coluna": "vldesc",
            "desconto_fonte_confianca": "alta",
        },
    )

    metrics = {item["key"]: item for item in audit["metric_definitions"]}

    assert metrics["desconto_total"]["confidence"] == "alta"
    assert metrics["desconto_total"]["runtime_source"]["column"] == "vldesc"
    assert "filial 3" in audit["calculation_steps"][1]["detail"]


def test_metric_registry_never_treats_unsupported_metrics_as_supported():
    audit = core_sales_metric_audit(
        topics={"lucro", "vendas_nao_faturadas"},
        value_basis="liquido",
        ranking_kind=None,
        primary_metric="faturamento_comercial",
        period_label="2026-07-01 a 2026-07-31",
        filial=None,
    )

    unsupported = {item["key"] for item in audit["unsupported_metrics"]}

    assert unsupported == {"lucro", "vendas_nao_faturadas"}


def test_metric_registry_attaches_financial_source_discovery_to_unsupported_metrics():
    audit = core_sales_metric_audit(
        topics={"lucro", "vendas_nao_faturadas"},
        value_basis="liquido",
        ranking_kind=None,
        primary_metric="faturamento_comercial",
        period_label="2026-07-01 a 2026-07-31",
        filial=None,
        financial_source_discovery={
            "profit": {
                "lucro_bruto": {"status": "partial", "best_source": "public.vw_vendas_lm"},
                "lucro_liquido": {"status": "missing", "best_source": None},
                "candidates": [{"source": "public.vw_vendas_lm"}],
            },
            "unbilled_sales": {
                "vendas_nao_faturadas": {"status": "missing", "best_source": None},
                "candidates": [],
            },
        },
    )

    metrics = {item["key"]: item for item in audit["metric_definitions"]}

    assert metrics["lucro"]["runtime_source"]["lucro_bruto"]["status"] == "partial"
    assert metrics["vendas_nao_faturadas"]["runtime_source"]["vendas_nao_faturadas"]["status"] == "missing"
