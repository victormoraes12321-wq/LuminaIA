from __future__ import annotations

from decimal import Decimal

import pytest

from contracts.analytical_v2 import ComparisonCalculation
from database import AsyncSessionLocal
from services.comparison_execution import (
    SQLAlchemyComparisonQueryRunner,
    UniversalComparisonExecutor,
)
from testing.test_database import TENANT_A

from comparison_executor_fixtures import execution_context, make_plan


@pytest.mark.asyncio
async def test_original_question_executes_against_disposable_postgresql():
    result = await UniversalComparisonExecutor(
        SQLAlchemyComparisonQueryRunner(
            AsyncSessionLocal,
            tenant_isolation_evidence=(
                "test schema vw_vendas_lm exposes mandatory tenant_id"
            ),
        )
    ).execute(make_plan(TENANT_A), execution_context(TENANT_A))

    values = {
        item.calculation: item
        for item in result.calculations
    }
    assert values[ComparisonCalculation.ABSOLUTE_DIFFERENCE].baseline_value == Decimal("300.00")
    assert values[ComparisonCalculation.ABSOLUTE_DIFFERENCE].target_value == Decimal("400.00")
    assert values[ComparisonCalculation.ABSOLUTE_DIFFERENCE].result_value == Decimal("100.00")
    assert values[ComparisonCalculation.PERCENTAGE_DIFFERENCE].result_value == Decimal("33.33")
    assert values[ComparisonCalculation.DIRECTION].direction.value == "INCREASE"
    assert all(item.public.tenant_id == TENANT_A for item in result.provenance)
    assert all(item.public.tenant_isolation_verified for item in result.provenance)


@pytest.mark.asyncio
async def test_postgresql_comparison_excludes_transfer_and_other_tenant():
    result = await UniversalComparisonExecutor(
        SQLAlchemyComparisonQueryRunner(
            AsyncSessionLocal,
            tenant_isolation_evidence=(
                "test schema vw_vendas_lm exposes mandatory tenant_id"
            ),
        )
    ).execute(make_plan(TENANT_A), execution_context(TENANT_A))

    operand_values = {
        item.operand_id: item.dataset[0]["faturamento_comercial"]
        for item in result.operands
    }
    assert operand_values == {
        "june": Decimal("300.00"),
        "july": Decimal("400.00"),
    }
    assert Decimal("500.00") not in operand_values.values()
    assert Decimal("600.00") not in operand_values.values()
    assert Decimal("900.00") not in operand_values.values()
    assert Decimal("1200.00") not in operand_values.values()
