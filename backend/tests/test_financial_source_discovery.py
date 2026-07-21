from services.financial_source_discovery import (
    ColumnProfile,
    SourceProfile,
    financial_source_discovery,
)


def source(name: str, columns: list[str]) -> SourceProfile:
    return SourceProfile(
        schema="public",
        name=name,
        table_type="BASE TABLE",
        columns=tuple(ColumnProfile(column, "numeric") for column in columns),
    )


def test_vw_vendas_lm_is_not_enough_for_profit_or_unbilled_sales():
    profile = source(
        "vw_vendas_lm",
        ["filial_", "tp_", "pedido_", "nota_", "dtemissao_", "ptotal_", "rca_", "numero_nfe"],
    )

    profit = financial_source_discovery.assess_profit_source(profile)
    unbilled = financial_source_discovery.assess_unbilled_sales_source(profile)

    assert profit.status in {"partial", "missing"}
    assert not profit.capabilities["lucro_bruto"]
    assert not profit.capabilities["lucro_liquido"]
    assert unbilled.status == "partial"
    assert not unbilled.capabilities["vendas_nao_faturadas"]
    assert "status de pendencia" in " ".join(unbilled.notes)


def test_profit_source_requires_cost_for_gross_and_tax_or_expense_for_net():
    profile = source(
        "vw_lucro_produtos",
        ["data_emissao", "filial", "receita_total", "custo_total", "icms_valor", "despesa_rateada"],
    )

    assessment = financial_source_discovery.assess_profit_source(profile)

    assert assessment.status == "ready"
    assert assessment.capabilities["lucro_bruto"]
    assert assessment.capabilities["lucro_liquido"]
    assert assessment.matched_columns["revenue"] == ["receita_total"]
    assert assessment.matched_columns["cost"] == ["custo_total"]


def test_unbilled_source_requires_order_context_and_operational_status():
    profile = source(
        "vw_pedidos_pendentes",
        ["pedido_id", "status_pedido", "valor_total", "data_pedido", "filial", "vendedor", "cliente"],
    )

    assessment = financial_source_discovery.assess_unbilled_sales_source(profile)

    assert assessment.status == "ready"
    assert assessment.capabilities["vendas_nao_faturadas"]
    assert assessment.capabilities["filial"]
    assert assessment.capabilities["vendedor"]


def test_financial_payment_status_is_not_operational_unbilled_status():
    profile = source(
        "vw_financeiro_lm",
        ["financeiro_id", "cliente_id", "valor_parcela", "status_pagamento", "data_vencimento"],
    )

    assessment = financial_source_discovery.assess_unbilled_sales_source(profile)

    assert assessment.status == "partial"
    assert not assessment.capabilities["vendas_nao_faturadas"]
    assert "Status financeiro de pagamento" in " ".join(assessment.notes)
