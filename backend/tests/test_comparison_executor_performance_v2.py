from __future__ import annotations

import statistics
import time
from decimal import Decimal
from uuid import UUID

import pytest

from services.comparison_execution import (
    ComparisonExecutorFeaturePolicy,
    GovernedComparisonQueryCompiler,
    UniversalComparisonExecutor,
    build_execution_graph,
    default_comparison_execution_catalog,
    select_execution_strategy,
)

from comparison_executor_fixtures import execution_context, make_plan


TENANT_A = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")


class PerformanceRunner:
    source_kind = "ANALYTICAL_CLONE"
    tenant_isolation_verified = True
    isolation_evidence = "performance fixture tenant scope"

    async def execute(self, query):
        value = Decimal("300") if query.operand_id == "june" else Decimal("400")
        return [{metric_id: value for metric_id in query.metric_ids}]


@pytest.mark.no_database
def test_compilation_p95_stays_bounded():
    plan = make_plan(TENANT_A)
    context = execution_context(TENANT_A)
    compiler = GovernedComparisonQueryCompiler(
        default_comparison_execution_catalog()
    )
    strategy = select_execution_strategy(plan)
    samples = []
    for _ in range(100):
        started = time.perf_counter()
        compiler.compile(plan, context, strategy)
        samples.append((time.perf_counter() - started) * 1000)
    p95 = statistics.quantiles(samples, n=20)[18]
    assert p95 < 50


@pytest.mark.no_database
def test_graph_compilation_is_deterministic_and_bounded():
    plan = make_plan(TENANT_A)
    context = execution_context(TENANT_A)
    strategy = select_execution_strategy(plan)
    started = time.perf_counter()
    graphs = [
        build_execution_graph(plan, context, strategy)
        for _ in range(100)
    ]
    duration_ms = (time.perf_counter() - started) * 1000
    assert len({item.graph_fingerprint for item in graphs}) == 1
    assert duration_ms < 1000


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_end_to_end_in_memory_p95_stays_bounded():
    plan = make_plan(TENANT_A)
    context = execution_context(TENANT_A)
    samples = []
    for _ in range(30):
        started = time.perf_counter()
        await UniversalComparisonExecutor(PerformanceRunner()).execute(
            plan, context
        )
        samples.append((time.perf_counter() - started) * 1000)
    p95 = statistics.quantiles(samples, n=20)[18]
    assert p95 < 100


@pytest.mark.no_database
def test_feature_policy_defaults_fail_closed():
    class Settings:
        pass

    policy = ComparisonExecutorFeaturePolicy.from_settings(Settings())
    assert not policy.enabled
    assert not policy.shadow_mode


@pytest.mark.no_database
def test_feature_policy_reads_explicit_rollout_flags():
    class Settings:
        COMPARISON_EXECUTOR_V2_ENABLED = True
        COMPARISON_EXECUTOR_V2_SHADOW_MODE = True

    policy = ComparisonExecutorFeaturePolicy.from_settings(Settings())
    assert policy.enabled
    assert policy.shadow_mode
