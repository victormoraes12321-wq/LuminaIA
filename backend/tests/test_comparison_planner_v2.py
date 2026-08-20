from __future__ import annotations

import inspect
import json
import time
from uuid import UUID

import pytest

from contracts.analytical_v2 import (
    ComparisonCalculation,
    ComparisonKind,
    ExecutionReadiness,
    FieldOrigin,
    PipelineKind,
    QueryPlanV2,
    build_intent_v2,
    build_plan_v2,
)
from services.comparison_planning import (
    COMPARISON_PLANNER_VERSION,
    ComparisonPlanner,
    ComparisonStrategyHint,
)

from comparison_planner_fixtures import (
    SOURCE_SALES,
    TENANT_A,
    catalog,
    comparison,
    context,
    entity,
    intent,
    metric,
    operand,
    window,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database]


def _planner() -> ComparisonPlanner:
    return ComparisonPlanner(catalog=catalog())


def _period_intent(months: list[int]):
    revenue = metric("faturamento_comercial")
    windows = [window(2026, month) for month in months]
    operands = [
        operand(
            f"operand_{index}",
            period.label,
            metrics=[revenue],
            windows=[period],
        )
        for index, period in enumerate(windows, start=1)
    ]
    return intent(
        comparison(
            ComparisonKind.PERIOD_VS_PERIOD
            if len(operands) == 2
            else ComparisonKind.MULTI_PERIOD,
            operands,
            baseline=operands[0].operand_id,
        ),
        metrics=[revenue],
        windows=windows,
    )


def test_original_june_july_question_generates_ready_plan() -> None:
    normalized = build_intent_v2(
        "Compare o faturamento do Mes 06/2026 e 07/2026",
        pipeline=PipelineKind.NEW,
    )
    plan = build_plan_v2(
        normalized,
        tenant_id=TENANT_A,
        user_id=None,
        user_role="CONSULTA",
        session_id="comparison-session",
        allowed_source_ids=[SOURCE_SALES],
        pipeline=PipelineKind.NEW,
    )
    assert plan.intent.readiness == ExecutionReadiness.READY
    assert plan.comparison is not None
    assert plan.comparison.kind == ComparisonKind.PERIOD_VS_PERIOD
    assert [item.time_windows[0].start.month for item in plan.comparison.operands] == [6, 7]
    assert plan.comparison.baseline_operand_id == "operand_1"
    assert plan.comparison.calculations == [
        ComparisonCalculation.VALUE,
        ComparisonCalculation.ABSOLUTE_DIFFERENCE,
        ComparisonCalculation.PERCENTAGE_DIFFERENCE,
        ComparisonCalculation.DIRECTION,
    ]
    assert plan.contract.extensions["comparison_planner"]["planner_version"] == (
        COMPARISON_PLANNER_VERSION
    )
    assert plan.cache_identity and plan.cache_identity.startswith("cmp:")


@pytest.mark.parametrize(
    ("months", "kind"),
    [
        ([6, 7], ComparisonKind.PERIOD_VS_PERIOD),
        ([1, 2, 3], ComparisonKind.MULTI_PERIOD),
        ([4, 1, 3], ComparisonKind.MULTI_PERIOD),
        ([1, 2, 3, 4], ComparisonKind.MULTI_PERIOD),
    ],
)
def test_period_plans_preserve_every_operand_and_order(
    months: list[int],
    kind: ComparisonKind,
) -> None:
    result = _planner().plan(_period_intent(months), context())
    assert result.readiness == ExecutionReadiness.READY
    assert result.plan is not None and result.plan.comparison is not None
    assert result.plan.comparison.kind == kind
    assert [
        item.time_windows[0].start.month
        for item in result.plan.comparison.operands
    ] == months


@pytest.mark.parametrize("count", [2, 3, 4, 5, 8, 12])
def test_n_input_operands_produce_n_output_operands(count: int) -> None:
    revenue = metric("faturamento_comercial")
    windows = [
        window(2025 + (index // 12), (index % 12) + 1, window_id=f"p{index}")
        for index in range(count)
    ]
    operands = [
        operand(
            f"operand_{index}",
            period.label,
            metrics=[revenue],
            windows=[period],
        )
        for index, period in enumerate(windows, start=1)
    ]
    source = intent(
        comparison(
            ComparisonKind.MULTI_PERIOD,
            operands,
            calculations=[ComparisonCalculation.VALUE],
            baseline=None,
        ),
        metrics=[revenue],
        windows=windows,
    )
    result = _planner().plan(source, context())
    assert result.plan is not None and result.plan.comparison is not None
    assert len(result.plan.comparison.operands) == count


def test_entity_vs_entity_keeps_specific_entities_separate() -> None:
    revenue = metric("faturamento_comercial")
    july = window(2026, 7)
    source = intent(
        comparison(
            ComparisonKind.ENTITY_VS_ENTITY,
            [
                operand(
                    "operand_1",
                    "Centro",
                    entities=[entity("filial:centro", "Centro")],
                ),
                operand(
                    "operand_2",
                    "Sul",
                    entities=[entity("filial:sul", "Sul")],
                ),
            ],
            baseline="operand_1",
        ),
        metrics=[revenue],
        windows=[july],
    )
    result = _planner().plan(source, context())
    assert result.readiness == ExecutionReadiness.READY
    assert result.plan is not None and result.plan.comparison is not None
    assert result.plan.comparison.kind == ComparisonKind.ENTITY_VS_ENTITY
    assert [
        item.entity_refs[0].entity_id
        for item in result.plan.comparison.operands
    ] == ["filial:centro", "filial:sul"]
    assert result.strategy_hint == ComparisonStrategyHint.CONDITIONAL_AGGREGATION


def test_multi_entity_preserves_three_entities() -> None:
    revenue = metric("faturamento_comercial")
    source = intent(
        comparison(
            ComparisonKind.MULTI_ENTITY,
            [
                operand("o1", "Centro", entities=[entity("filial:centro", "Centro")]),
                operand("o2", "Sul", entities=[entity("filial:sul", "Sul")]),
                operand("o3", "Norte", entities=[entity("filial:norte", "Norte")]),
            ],
            calculations=[ComparisonCalculation.VALUE, ComparisonCalculation.RANK],
            baseline=None,
        ),
        metrics=[revenue],
        windows=[window(2026, 7)],
    )
    result = _planner().plan(source, context())
    assert result.readiness == ExecutionReadiness.READY
    assert result.plan is not None and result.plan.comparison is not None
    assert result.plan.comparison.kind == ComparisonKind.MULTI_ENTITY
    assert len(result.plan.comparison.operands) == 3
    assert result.plan.comparison.baseline_operand_id is None


def test_metric_vs_metric_with_same_unit_keeps_differences() -> None:
    net = metric("faturamento_comercial")
    gross = metric("faturamento_bruto")
    source = intent(
        comparison(
            ComparisonKind.METRIC_VS_METRIC,
            [
                operand("net", "Líquido", metrics=[net]),
                operand("gross", "Bruto", metrics=[gross]),
            ],
            baseline="net",
        ),
        metrics=[net, gross],
        windows=[window(2026, 7)],
    )
    result = _planner().plan(source, context())
    assert result.readiness == ExecutionReadiness.READY
    assert result.plan is not None and result.plan.comparison is not None
    assert result.plan.comparison.kind == ComparisonKind.METRIC_VS_METRIC
    assert ComparisonCalculation.PERCENTAGE_DIFFERENCE in (
        result.plan.comparison.calculations
    )


def test_metric_vs_metric_with_different_units_is_value_only() -> None:
    revenue = metric("faturamento_comercial")
    quantity = metric("quantidade_vendida", unit="UNITS")
    source = intent(
        comparison(
            ComparisonKind.METRIC_VS_METRIC,
            [
                operand("money", "Faturamento", metrics=[revenue]),
                operand("units", "Quantidade", metrics=[quantity]),
            ],
            baseline="money",
        ),
        metrics=[revenue, quantity],
        windows=[window(2026, 7)],
    )
    result = _planner().plan(source, context())
    assert result.readiness == ExecutionReadiness.READY
    assert result.plan is not None and result.plan.comparison is not None
    assert result.plan.comparison.calculations == [ComparisonCalculation.VALUE]
    assert "INCOMPATIBLE_METRIC_UNITS" in {
        issue.code for issue in result.issues
    }


def test_actual_vs_target_requires_official_target() -> None:
    actual = metric("faturamento_comercial")
    target = metric("meta_faturamento")
    source = intent(
        comparison(
            ComparisonKind.ACTUAL_VS_TARGET,
            [
                operand("actual", "Realizado", metrics=[actual]),
                operand("target", "Meta", metrics=[target]),
            ],
            baseline="target",
        ),
        metrics=[actual, target],
        windows=[window(2026, 7)],
    )
    ready = ComparisonPlanner(catalog=catalog()).plan(source, context())
    unsupported = ComparisonPlanner(catalog=catalog(include_target=False)).plan(
        source,
        context(),
    )
    assert ready.readiness == ExecutionReadiness.READY
    assert ready.strategy_hint == ComparisonStrategyHint.TARGET_JOIN
    assert unsupported.readiness == ExecutionReadiness.UNSUPPORTED
    assert "OFFICIAL_TARGET_NOT_AVAILABLE" in {
        issue.code for issue in unsupported.issues
    }


@pytest.mark.multitenant
def test_target_from_other_tenant_is_not_used() -> None:
    actual = metric("faturamento_comercial")
    target = metric("meta_faturamento")
    source = intent(
        comparison(
            ComparisonKind.ACTUAL_VS_TARGET,
            [
                operand("actual", "Realizado", metrics=[actual]),
                operand("target", "Meta", metrics=[target]),
            ],
        ),
        metrics=[actual, target],
        windows=[window(2026, 7)],
    )
    result = ComparisonPlanner(
        catalog=catalog(target_tenant=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
    ).plan(source, context())
    assert result.readiness == ExecutionReadiness.UNSUPPORTED


def test_composed_center_june_vs_south_july_preserves_both_scopes() -> None:
    revenue = metric("faturamento_comercial")
    june = window(2026, 6)
    july = window(2026, 7)
    source = intent(
        comparison(
            ComparisonKind.PERIOD_VS_PERIOD,
            [
                operand(
                    "center_june",
                    "Centro em junho",
                    windows=[june],
                    entities=[entity("filial:centro", "Centro")],
                ),
                operand(
                    "south_july",
                    "Sul em julho",
                    windows=[july],
                    entities=[entity("filial:sul", "Sul")],
                ),
            ],
            baseline="center_june",
        ),
        metrics=[revenue],
        windows=[june, july],
    )
    result = _planner().plan(source, context())
    assert result.readiness == ExecutionReadiness.READY
    assert result.plan is not None and result.plan.comparison is not None
    left, right = result.plan.comparison.operands
    assert left.time_windows[0] == june
    assert left.entity_refs[0].entity_id == "filial:centro"
    assert right.time_windows[0] == july
    assert right.entity_refs[0].entity_id == "filial:sul"


def test_planning_is_idempotent_and_does_not_modify_input() -> None:
    source = _period_intent([6, 7])
    before = source.model_dump_json()
    planner = _planner()
    first = planner.plan(source, context())
    second = planner.plan(source, context())
    assert first.plan == second.plan
    assert first.cache_identity == second.cache_identity
    assert source.model_dump_json() == before


def test_plan_round_trip_is_deterministic() -> None:
    result = _planner().plan(_period_intent([6, 7]), context())
    assert result.plan is not None
    encoded = result.plan.model_dump_json()
    assert QueryPlanV2.model_validate_json(encoded) == result.plan
    assert json.loads(encoded) == json.loads(result.plan.model_dump_json())


def test_explicit_field_origin_is_preserved() -> None:
    result = _planner().plan(_period_intent([6, 7]), context())
    assert result.plan is not None and result.plan.comparison is not None
    assert all(
        operand.origin == FieldOrigin.EXPLICIT_USER
        for operand in result.plan.comparison.operands
    )


def test_duplicate_semantic_entity_operand_requires_clarification() -> None:
    revenue = metric("faturamento_comercial")
    source = intent(
        comparison(
            ComparisonKind.ENTITY_VS_ENTITY,
            [
                operand("one", "Centro", entities=[entity("filial:centro", "Centro")]),
                operand("two", "Centro", entities=[entity("filial:centro", "Centro")]),
            ],
        ),
        metrics=[revenue],
        windows=[window(2026, 7)],
    )
    result = _planner().plan(source, context())
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert result.clarification is not None
    assert len(result.plan.comparison.operands) == 2


def test_requested_sort_is_structured_without_sql() -> None:
    revenue = metric("faturamento_comercial")
    source = intent(
        comparison(
            ComparisonKind.MULTI_ENTITY,
            [
                operand("one", "Centro", entities=[entity("filial:centro", "Centro")]),
                operand("two", "Sul", entities=[entity("filial:sul", "Sul")]),
            ],
            calculations=[ComparisonCalculation.VALUE, ComparisonCalculation.RANK],
            requested_sort="faturamento_comercial:DESC",
        ),
        metrics=[revenue],
        windows=[window(2026, 7)],
    )
    result = _planner().plan(source, context())
    assert result.plan is not None
    assert result.plan.ordering[0].field_id == "faturamento_comercial"
    assert result.plan.ordering[0].direction == "DESC"
    assert "select " not in result.plan.model_dump_json().lower()


def test_planner_source_has_no_external_or_database_dependency() -> None:
    import services.comparison_planning.feature_flags as feature_flags
    import services.comparison_planning.legacy_adapter as legacy_adapter
    import services.comparison_planning.planner as planner_module
    import services.comparison_planning.providers as providers

    source = "\n".join(
        inspect.getsource(module)
        for module in (
            planner_module,
            providers,
            feature_flags,
            legacy_adapter,
        )
    ).lower()
    assert "openai" not in source
    assert "sqlalchemy" not in source
    assert "get_db" not in source
    assert "oracle_service" not in source


def test_common_planning_performance_has_generous_bound() -> None:
    planner = _planner()
    source = _period_intent([6, 7])
    planning_context = context()
    started = time.perf_counter()
    for _ in range(50):
        result = planner.plan(source, planning_context)
        assert result.readiness == ExecutionReadiness.READY
    assert time.perf_counter() - started < 30
