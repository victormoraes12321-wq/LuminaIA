from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text

from database import AsyncSessionLocal
from services.sales_value_breakdown import sales_value_breakdown
from testing.test_database import TENANT_A, TENANT_B


pytestmark = [
    pytest.mark.integration,
    pytest.mark.database,
    pytest.mark.baseline,
    pytest.mark.multitenant,
]


async def _tenant_month_totals(tenant_id, year: int, month: int) -> dict:
    start = date(year, month, 1)
    end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(ptotal_) FILTER (WHERE tp_ IN (2, 61)), 0)
                        AS faturamento_comercial,
                    COUNT(DISTINCT pedido_) FILTER (WHERE tp_ IN (2, 61))
                        AS pedidos_comerciais,
                    COALESCE(SUM(desconto_total) FILTER (WHERE tp_ IN (2, 61)), 0)
                        AS desconto_comercial,
                    COALESCE(SUM(ptotal_) FILTER (WHERE tp_ = 9), 0) AS saida_rb,
                    COALESCE(SUM(ptotal_) FILTER (
                        WHERE UPPER(COALESCE(tpdescricao_, '')) LIKE '%DEVOL%'
                    ), 0) AS devolucao,
                    COALESCE(SUM(ptotal_) FILTER (WHERE tp_ = 22), 0)
                        AS venda_bonificada,
                    COALESCE(SUM(ptotal_) FILTER (WHERE tp_ IN (3, 31, 96)), 0)
                        AS transferencias
                FROM vw_vendas_lm
                WHERE tenant_id = :tenant_id
                  AND dtemissao_ >= :start
                  AND dtemissao_ < :end
                """
            ),
            {"tenant_id": tenant_id, "start": start, "end": end},
        )
        return dict(result.mappings().one())


@pytest.mark.asyncio
async def test_tenant_a_june_baseline_matches_documented_totals(
    expected_baseline,
) -> None:
    actual = await _tenant_month_totals(TENANT_A, 2026, 6)
    expected = expected_baseline["tenant_a"]["june_2026"]
    assert float(actual["faturamento_comercial"]) == expected["faturamento_comercial"]
    assert actual["pedidos_comerciais"] == expected["pedidos_comerciais"]
    assert float(actual["desconto_comercial"]) == expected["desconto_comercial"]
    assert float(actual["saida_rb"]) == expected["saida_rb"]
    assert float(actual["devolucao"]) == expected["devolucao"]
    assert float(actual["venda_bonificada"]) == expected["venda_bonificada"]
    assert float(actual["transferencias"]) == expected["transferencias"]
    assert (
        float(actual["faturamento_comercial"]) / actual["pedidos_comerciais"]
        == expected["ticket_medio"]
    )


@pytest.mark.asyncio
async def test_tenant_a_july_and_comparison_baseline(expected_baseline) -> None:
    june = await _tenant_month_totals(TENANT_A, 2026, 6)
    july = await _tenant_month_totals(TENANT_A, 2026, 7)
    expected_july = expected_baseline["tenant_a"]["july_2026"]
    expected_comparison = expected_baseline["tenant_a"]["comparison_june_july_2026"]
    june_value = Decimal(june["faturamento_comercial"])
    july_value = Decimal(july["faturamento_comercial"])
    difference = july_value - june_value
    percentage = difference / june_value * Decimal("100")

    assert float(july_value) == expected_july["faturamento_comercial"]
    assert float(difference) == expected_comparison["absolute_difference"]
    assert round(float(percentage), 6) == expected_comparison["percentage_difference"]
    assert difference > 0


@pytest.mark.asyncio
async def test_branch_filter_and_transfer_exclusion(expected_baseline) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT filial_, SUM(ptotal_) AS value
                FROM vw_vendas_lm
                WHERE tenant_id = :tenant_id
                  AND tp_ IN (2, 61)
                  AND dtemissao_ >= '2026-06-01'
                  AND dtemissao_ < '2026-07-01'
                GROUP BY filial_
                ORDER BY filial_
                """
            ),
            {"tenant_id": TENANT_A},
        )
        rows = [dict(row) for row in result.mappings().all()]
    assert rows == [{"filial_": "1", "value": Decimal("100.00")}, {"filial_": "2", "value": Decimal("200.00")}]
    assert sum(row["value"] for row in rows) == Decimal(
        str(expected_baseline["tenant_a"]["june_2026"]["faturamento_comercial"])
    )


@pytest.mark.asyncio
async def test_tenants_have_same_names_but_different_values(expected_baseline) -> None:
    tenant_a = await _tenant_month_totals(TENANT_A, 2026, 6)
    tenant_b = await _tenant_month_totals(TENANT_B, 2026, 6)
    assert float(tenant_a["faturamento_comercial"]) == 300.0
    assert float(tenant_b["faturamento_comercial"]) == 900.0
    assert tenant_a["faturamento_comercial"] != tenant_b["faturamento_comercial"]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "LUMINA-GAP-TENANT-001: core summaries query vw_vendas_lm through "
        "get_db_context without tenant_id; fix belongs to the analytical gateway prompt."
    ),
)
@pytest.mark.known_gap
@pytest.mark.asyncio
async def test_core_summary_breakdown_does_not_mix_tenants() -> None:
    binds = {
        "start_date": date(2026, 6, 1),
        "end_exclusive": date(2026, 7, 1),
    }
    async with AsyncSessionLocal() as session:
        totals = await sales_value_breakdown.fetch_period_totals(session, binds)
    assert Decimal(totals["faturamento_comercial"]) == Decimal("300.00")
