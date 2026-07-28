from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import UUID

import pytest

from contracts.analytical_v2 import (
    ComparisonCalculation,
    ComparisonKind,
    ExecutionReadiness,
)
from services.comparison_execution import (
    ComparisonExecutionRejected,
    ComparisonExecutionStatus,
    FailurePolicy,
    TransientComparisonQueryError,
    UniversalComparisonExecutor,
    ZeroDenominatorPolicy,
    execution_result_to_legacy,
    execution_result_to_v2,
)

from comparison_executor_fixtures import (
    execution_context,
    make_plan,
)


TENANT_A = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
TENANT_B = UUID("b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22")


class DeterministicRunner:
    source_kind = "ANALYTICAL_CLONE"
    tenant_isolation_verified = True
    isolation_evidence = "synthetic tenant-scoped runner"

    def __init__(self, values=None):
        self.values = values or {6: Decimal("300"), 7: Decimal("400")}
        self.calls = []

    async def execute(self, query):
        self.calls.append(query)
        month = query.binds["window_start_0"].month
        return [
            {
                **{dimension: "1" for dimension in query.dimension_ids},
                **{
                    metric: self.values.get(month, Decimal("0"))
                    for metric in query.metric_ids
                },
            }
        ]


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_original_question_june_300_vs_july_400():
    plan = make_plan(TENANT_A)
    result = await UniversalComparisonExecutor(DeterministicRunner()).execute(
        plan, execution_context(TENANT_A)
    )

    assert result.status == ComparisonExecutionStatus.READY
    absolute = next(
        item
        for item in result.calculations
        if item.calculation == ComparisonCalculation.ABSOLUTE_DIFFERENCE
    )
    percentage = next(
        item
        for item in result.calculations
        if item.calculation == ComparisonCalculation.PERCENTAGE_DIFFERENCE
    )
    direction = next(
        item
        for item in result.calculations
        if item.calculation == ComparisonCalculation.DIRECTION
    )
    assert absolute.baseline_value == Decimal("300")
    assert absolute.target_value == Decimal("400")
    assert absolute.result_value == Decimal("100.00")
    assert percentage.raw_result_value == Decimal("100") / Decimal("3")
    assert percentage.result_value == Decimal("33.33")
    assert direction.direction.value == "INCREASE"


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("baseline", "target", "expected_delta", "expected_direction"),
    [
        ("100", "150", "50.00", "INCREASE"),
        ("150", "100", "-50.00", "DECREASE"),
        ("100", "100", "0.00", "STABLE"),
        ("-100", "-50", "50.00", "INCREASE"),
        ("-50", "-100", "-50.00", "DECREASE"),
        ("0.01", "0.02", "0.01", "INCREASE"),
        ("999999999.99", "1000000000.00", "0.01", "INCREASE"),
    ],
)
async def test_decimal_math_matrix(
    baseline, target, expected_delta, expected_direction
):
    runner = DeterministicRunner(
        {6: Decimal(baseline), 7: Decimal(target)}
    )
    result = await UniversalComparisonExecutor(runner).execute(
        make_plan(TENANT_A), execution_context(TENANT_A)
    )
    absolute = next(
        item
        for item in result.calculations
        if item.calculation == ComparisonCalculation.ABSOLUTE_DIFFERENCE
    )
    assert absolute.result_value == Decimal(expected_delta)
    assert absolute.direction.value == expected_direction
    assert isinstance(absolute.raw_result_value, Decimal)


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("policy", "target", "expected", "status"),
    [
        (ZeroDenominatorPolicy.NOT_APPLICABLE, "10", None, "NOT_APPLICABLE"),
        (ZeroDenominatorPolicy.ZERO_WHEN_BOTH_ZERO, "0", Decimal("0"), "READY"),
        (
            ZeroDenominatorPolicy.EXPLICIT_INFINITY_UNSUPPORTED,
            "10",
            None,
            "NOT_APPLICABLE",
        ),
    ],
)
async def test_zero_denominator_policies(policy, target, expected, status):
    runner = DeterministicRunner({6: Decimal("0"), 7: Decimal(target)})
    result = await UniversalComparisonExecutor(runner).execute(
        make_plan(TENANT_A),
        execution_context(TENANT_A, zero_denominator_policy=policy),
    )
    percentage = next(
        item
        for item in result.calculations
        if item.calculation == ComparisonCalculation.PERCENTAGE_DIFFERENCE
    )
    assert percentage.result_value == expected
    assert percentage.status == status
    assert percentage.zero_denominator


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_zero_denominator_error_policy_rejects_result():
    runner = DeterministicRunner({6: Decimal("0"), 7: Decimal("10")})
    with pytest.raises(ComparisonExecutionRejected, match="Zero denominator"):
        await UniversalComparisonExecutor(runner).execute(
            make_plan(TENANT_A),
            execution_context(
                TENANT_A,
                zero_denominator_policy=ZeroDenominatorPolicy.ERROR,
            ),
        )


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "readiness",
    [
        ExecutionReadiness.BLOCKED,
        ExecutionReadiness.CLARIFICATION_REQUIRED,
        ExecutionReadiness.UNSUPPORTED,
    ],
)
async def test_non_ready_plan_never_executes(readiness):
    runner = DeterministicRunner()
    with pytest.raises(ComparisonExecutionRejected):
        await UniversalComparisonExecutor(runner).execute(
            make_plan(TENANT_A, readiness=readiness),
            execution_context(TENANT_A),
        )
    assert runner.calls == []


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_tenant_and_permission_mismatch_never_execute():
    runner = DeterministicRunner()
    executor = UniversalComparisonExecutor(runner)
    with pytest.raises(ComparisonExecutionRejected, match="tenant"):
        await executor.execute(make_plan(TENANT_A), execution_context(TENANT_B))
    with pytest.raises(ComparisonExecutionRejected, match="Permission"):
        await executor.execute(
            make_plan(TENANT_A),
            execution_context(TENANT_A, permission_fingerprint="permission:other"),
        )
    assert not runner.calls


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_id",
    ["oracle", "oracle_erp", "unknown_source", "vw_vendas_lm_shadow"],
)
async def test_untrusted_or_oracle_sources_are_blocked(source_id):
    runner = DeterministicRunner()
    plan = make_plan(TENANT_A, source_ids=(source_id,))
    context = execution_context(
        TENANT_A,
        allowed_source_ids=(source_id,),
    )
    with pytest.raises(ComparisonExecutionRejected):
        await UniversalComparisonExecutor(runner).execute(plan, context)
    assert not runner.calls


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metric_id",
    ["lucro", "vendas_nao_faturadas", "unknown_metric"],
)
async def test_unsupported_metrics_fail_closed(metric_id):
    runner = DeterministicRunner()
    plan = make_plan(TENANT_A, metric_ids=(metric_id,))
    context = execution_context(TENANT_A, metric_ids=(metric_id,))
    with pytest.raises(ComparisonExecutionRejected):
        await UniversalComparisonExecutor(runner).execute(plan, context)
    assert not runner.calls


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize("dimension", ["filial", "produto", "vendedor", "cliente", "mes", "dia", "ano"])
async def test_grouped_alignment_preserves_canonical_dimension(dimension):
    result = await UniversalComparisonExecutor(DeterministicRunner()).execute(
        make_plan(TENANT_A, dimensions=(dimension,)),
        execution_context(TENANT_A),
    )
    assert result.aligned_datasets[0].alignment_keys == (dimension,)
    assert result.aligned_datasets[0].rows[0].alignment_key == ("1",)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_rank_and_share_are_deterministic():
    plan = make_plan(
        TENANT_A,
        periods=(("june", 2026, 6), ("july", 2026, 7), ("august", 2026, 8)),
        kind=ComparisonKind.MULTI_PERIOD,
        baseline=None,
        calculations=(ComparisonCalculation.RANK, ComparisonCalculation.SHARE),
    )
    runner = DeterministicRunner(
        {6: Decimal("300"), 7: Decimal("400"), 8: Decimal("300")}
    )
    result = await UniversalComparisonExecutor(runner).execute(
        plan, execution_context(TENANT_A)
    )
    ranks = {
        item.target_operand_id: item.result_value
        for item in result.calculations
        if item.calculation == ComparisonCalculation.RANK
    }
    shares = [
        item.result_value
        for item in result.calculations
        if item.calculation == ComparisonCalculation.SHARE
    ]
    assert ranks == {
        "june": Decimal("2"),
        "july": Decimal("1"),
        "august": Decimal("2"),
    }
    assert shares == [Decimal("30.00"), Decimal("40.00"), Decimal("30.00")]


class SlowRunner(DeterministicRunner):
    async def execute(self, query):
        await asyncio.sleep(0.05)
        return await super().execute(query)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_operand_timeout_is_explicit_and_not_success():
    result = await UniversalComparisonExecutor(SlowRunner()).execute(
        make_plan(TENANT_A),
        execution_context(
            TENANT_A,
            query_timeout_seconds=Decimal("0.001"),
            total_timeout_seconds=Decimal("1"),
        ),
    )
    assert result.status == ComparisonExecutionStatus.FAILED
    assert all(item.status.value == "TIMED_OUT" for item in result.operands)
    assert result.validation.status.value == "FAILED"


class PartiallyFailingRunner(DeterministicRunner):
    async def execute(self, query):
        if query.operand_id == "july":
            raise RuntimeError("controlled")
        return await super().execute(query)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_partial_policy_is_explicit():
    result = await UniversalComparisonExecutor(PartiallyFailingRunner()).execute(
        make_plan(TENANT_A),
        execution_context(TENANT_A, failure_policy=FailurePolicy.ALLOW_PARTIAL),
    )
    assert result.status == ComparisonExecutionStatus.PARTIAL
    assert result.partial
    assert result.errors[0].code == "OPERAND_EXECUTION_FAILED"


class RetryOnceRunner(DeterministicRunner):
    def __init__(self):
        super().__init__()
        self.attempts = {}

    async def execute(self, query):
        attempts = self.attempts.get(query.operand_id, 0)
        self.attempts[query.operand_id] = attempts + 1
        if attempts == 0:
            raise TransientComparisonQueryError("retry")
        return await super().execute(query)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_transient_failure_retries_once():
    runner = RetryOnceRunner()
    result = await UniversalComparisonExecutor(runner).execute(
        make_plan(TENANT_A), execution_context(TENANT_A)
    )
    assert result.status == ComparisonExecutionStatus.READY
    assert runner.attempts == {"june": 2, "july": 2}


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_cache_is_scoped_by_permission_fingerprint():
    runner = DeterministicRunner()
    executor = UniversalComparisonExecutor(runner)
    plan = make_plan(TENANT_A)
    context = execution_context(
        TENANT_A,
        feature_flags={"comparison_executor_local_cache": True},
    )
    first = await executor.execute(plan, context)
    second = await executor.execute(plan, context)
    assert first.cache_status == "MISS"
    assert second.cache_status == "HIT"
    assert len(runner.calls) == 2

    other_plan = make_plan(TENANT_A, permission_fingerprint="permission:second")
    await executor.execute(
        other_plan,
        execution_context(
            TENANT_A,
            permission_fingerprint="permission:second",
            feature_flags={"comparison_executor_local_cache": True},
        ),
    )
    assert len(runner.calls) == 4


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_v2_and_v1_adapters_preserve_numbers_and_sidecar():
    plan = make_plan(TENANT_A)
    result = await UniversalComparisonExecutor(DeterministicRunner()).execute(
        plan, execution_context(TENANT_A)
    )
    response = execution_result_to_v2(result, plan)
    legacy = execution_result_to_legacy(result, plan)
    assert response.contract.extensions["comparison_executor"]["executor_version"] == result.executor_version
    assert response.datasets[0].rows
    assert legacy["analytical_contract"]["datasets"][0]["rows"]
    assert legacy["chart_data"]["rows"] == response.model_dump(mode="json")["datasets"][0]["rows"]
