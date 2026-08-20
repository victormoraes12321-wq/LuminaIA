from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from contracts.analytical_v2 import ComparisonCalculation
from services.comparison_execution import (
    UniversalComparisonExecutor,
    build_execution_graph,
    select_execution_strategy,
)
from services.comparison_planning import MissingBucketPolicy, NullValuePolicy

from comparison_executor_fixtures import execution_context, make_plan


TENANT_A = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")


class PropertyRunner:
    source_kind = "ANALYTICAL_CLONE"
    tenant_isolation_verified = True
    isolation_evidence = "property runner tenant scope"

    def __init__(self, baseline: Decimal, target: Decimal):
        self.baseline = baseline
        self.target = target

    async def execute(self, query):
        value = self.baseline if query.operand_id == "june" else self.target
        return [
            {
                **{item: "1" for item in query.dimension_ids},
                **{item: value for item in query.metric_ids},
            }
        ]


IDEMPOTENCE_CASES = [
    (Decimal(index), Decimal(index * 3 + 1))
    for index in range(1, 21)
]


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(("baseline", "target"), IDEMPOTENCE_CASES)
async def test_repeated_execution_is_mathematically_idempotent(baseline, target):
    plan = make_plan(TENANT_A)
    plan_snapshot = plan.model_dump(mode="json")
    context = execution_context(TENANT_A)
    executor = UniversalComparisonExecutor(PropertyRunner(baseline, target))
    first = await executor.execute(plan, context)
    second = await executor.execute(plan, context)
    first_math = [
        item.model_dump(mode="json") for item in first.calculations
    ]
    second_math = [
        item.model_dump(mode="json") for item in second.calculations
    ]
    assert first_math == second_math
    assert first.plan_id == second.plan_id
    assert plan.model_dump(mode="json") == plan_snapshot


@pytest.mark.no_database
@pytest.mark.parametrize("maximum_concurrency", range(1, 9))
def test_execution_graph_respects_bounded_concurrency(maximum_concurrency):
    plan = make_plan(TENANT_A)
    context = execution_context(
        TENANT_A,
        maximum_concurrency=maximum_concurrency,
    )
    graph = build_execution_graph(
        plan,
        context,
        select_execution_strategy(plan),
    )
    assert graph.maximum_concurrency == min(maximum_concurrency, 2)
    assert len(graph.parallel_groups[0]) == 2
    assert graph.graph_fingerprint == build_execution_graph(
        plan,
        context,
        select_execution_strategy(plan),
    ).graph_fingerprint


class DifferentBucketRunner(PropertyRunner):
    async def execute(self, query):
        key = "1" if query.operand_id == "june" else "2"
        value = self.baseline if query.operand_id == "june" else self.target
        return [
            {
                "filial": key,
                **{item: value for item in query.metric_ids},
            }
        ]


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("missing_policy", "null_policy", "expected_rows", "expected_zero"),
    [
        (MissingBucketPolicy.PRESERVE_NULL, NullValuePolicy.PRESERVE, 2, False),
        (MissingBucketPolicy.ZERO_FILL, NullValuePolicy.PRESERVE, 2, True),
        (MissingBucketPolicy.OMIT, NullValuePolicy.PRESERVE, 0, False),
        (MissingBucketPolicy.PRESERVE_NULL, NullValuePolicy.ZERO_IF_ADDITIVE, 2, True),
        (MissingBucketPolicy.ZERO_FILL, NullValuePolicy.ZERO_IF_ADDITIVE, 2, True),
        (MissingBucketPolicy.OMIT, NullValuePolicy.OMIT, 0, False),
    ],
)
async def test_missing_bucket_policy_matrix(
    missing_policy,
    null_policy,
    expected_rows,
    expected_zero,
):
    result = await UniversalComparisonExecutor(
        DifferentBucketRunner(Decimal("300"), Decimal("400"))
    ).execute(
        make_plan(TENANT_A, dimensions=("filial",)),
        execution_context(
            TENANT_A,
            missing_bucket_policy=missing_policy,
            null_policy=null_policy,
        ),
    )
    dataset = result.aligned_datasets[0]
    assert dataset.row_count == expected_rows
    assert len(dataset.missing_buckets) == 2
    if expected_zero:
        assert any(
            value == Decimal("0")
            for row in dataset.rows
            for value in row.values.values()
        )


ORDER_CASES = [
    (("june", 2026, 6), ("july", 2026, 7)),
    (("first", 2025, 1), ("second", 2025, 2)),
    (("before", 2024, 12), ("after", 2025, 1)),
    (("a", 2026, 1), ("b", 2026, 12)),
    (("left", 2026, 3), ("right", 2026, 4)),
    (("base", 2026, 5), ("target", 2026, 6)),
    (("old", 2025, 7), ("new", 2026, 7)),
    (("p01", 2026, 1), ("p02", 2026, 2)),
    (("p03", 2026, 3), ("p04", 2026, 4)),
    (("p05", 2026, 5), ("p06", 2026, 6)),
    (("p07", 2026, 7), ("p08", 2026, 8)),
    (("p09", 2026, 9), ("p10", 2026, 10)),
    (("p11", 2026, 11), ("p12", 2026, 12)),
    (("x", 2027, 1), ("y", 2027, 2)),
    (("m1", 2027, 3), ("m2", 2027, 4)),
    (("m3", 2027, 5), ("m4", 2027, 6)),
    (("m5", 2027, 7), ("m6", 2027, 8)),
]


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize("periods", ORDER_CASES)
async def test_operand_order_property_is_never_reordered(periods):
    plan_periods = tuple(periods)
    result = await UniversalComparisonExecutor(
        PropertyRunner(Decimal("10"), Decimal("20"))
    ).execute(
        make_plan(
            TENANT_A,
            periods=plan_periods,
            baseline=plan_periods[0][0],
            calculations=(ComparisonCalculation.VALUE,),
        ),
        execution_context(TENANT_A),
    )
    assert tuple(item.operand_id for item in result.operands) == tuple(
        item[0] for item in plan_periods
    )
    assert result.calculations[0].target_operand_id == plan_periods[1][0]
