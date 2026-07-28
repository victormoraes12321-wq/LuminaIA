from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from contracts.analytical_v2 import ComparisonCalculation
from services.comparison_execution import UniversalComparisonExecutor

from comparison_executor_fixtures import execution_context, make_plan


TENANT_A = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
GOLDEN_PATH = Path(__file__).parent / "golden" / "comparison_execution_v2.json"


class GoldenRunner:
    source_kind = "ANALYTICAL_CLONE"
    tenant_isolation_verified = True
    isolation_evidence = "golden tenant fixture"

    def __init__(self, baseline, target):
        self.values = {
            "june": Decimal(baseline),
            "july": Decimal(target),
        }

    async def execute(self, query):
        return [
            {
                metric_id: self.values[query.operand_id]
                for metric_id in query.metric_ids
            }
        ]


def _goldens():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.mark.no_database
def test_golden_inventory_has_all_required_scenarios():
    expected = {
        "june_vs_july",
        "multi_period",
        "entity_vs_entity",
        "multi_entity",
        "metric_vs_metric_compatible",
        "metric_vs_metric_incompatible",
        "actual_vs_target",
        "negative_values",
        "equal_values",
        "zero_denominator",
        "missing_bucket",
        "partial_result",
        "timeout",
        "blocked",
        "legacy_compatibility",
    }
    assert set(_goldens()) == expected


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        "june_vs_july",
        "entity_vs_entity",
        "metric_vs_metric_compatible",
        "negative_values",
        "equal_values",
    ],
)
async def test_pairwise_golden_results(scenario):
    golden = _goldens()[scenario]
    result = await UniversalComparisonExecutor(
        GoldenRunner(golden["baseline"], golden["target"])
    ).execute(make_plan(TENANT_A), execution_context(TENANT_A))
    delta = next(
        item
        for item in result.calculations
        if item.calculation == ComparisonCalculation.ABSOLUTE_DIFFERENCE
    )
    assert result.status.value == golden["status"]
    assert str(delta.result_value) == golden["delta"]
    if "direction" in golden:
        assert delta.direction.value == golden["direction"]
    if "percentage" in golden:
        percentage = next(
            item
            for item in result.calculations
            if item.calculation == ComparisonCalculation.PERCENTAGE_DIFFERENCE
        )
        assert str(percentage.result_value) == golden["percentage"]


@pytest.mark.no_database
@pytest.mark.parametrize("scenario", sorted(_goldens()))
def test_golden_payloads_contain_no_volatile_or_sensitive_fields(scenario):
    payload = _goldens()[scenario]
    serialized = json.dumps(payload, sort_keys=True).lower()
    assert "execution_id" not in serialized
    assert "duration_ms" not in serialized
    assert "statement" not in serialized
    assert "binds" not in serialized
    assert "password" not in serialized
