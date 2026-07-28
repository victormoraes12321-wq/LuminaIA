from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.analytical_v2 import (
    ComparisonCalculation,
    ComparisonKind,
    ExecutionReadiness,
)
from services.comparison_planning import (
    ComparisonPlanner,
    plan_to_legacy_comparison_input,
)

from comparison_planner_fixtures import (
    catalog,
    comparison,
    context,
    dimension,
    entity,
    filter_spec,
    intent,
    metric,
    operand,
    window,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database, pytest.mark.baseline]
GOLDEN = Path(__file__).resolve().parent / "golden" / "comparison_plans_v2.json"


def _snapshot(result) -> dict[str, object]:
    plan = result.plan
    comparison_spec = plan.comparison if plan is not None else None
    definition = result.definition
    return {
        "planner_version": result.planner_version,
        "tenant_id": str(plan.scope.tenant_id)
        if plan is not None and plan.scope is not None
        else None,
        "readiness": result.readiness.value,
        "kind": comparison_spec.kind.value if comparison_spec else None,
        "operand_ids": [
            item.operand_id for item in comparison_spec.operands
        ] if comparison_spec else [],
        "metric_ids_by_operand": [
            [metric_ref.metric_id for metric_ref in item.metric_refs]
            for item in comparison_spec.operands
        ] if comparison_spec else [],
        "periods_by_operand": [
            [
                [period.start.isoformat(), period.end.isoformat()]
                for period in item.time_windows
            ]
            for item in comparison_spec.operands
        ] if comparison_spec else [],
        "entity_ids_by_operand": [
            [entity_ref.entity_id for entity_ref in item.entity_refs]
            for item in comparison_spec.operands
        ] if comparison_spec else [],
        "filter_ids_by_operand": [
            [filter_ref.filter_id for filter_ref in item.filters]
            for item in comparison_spec.operands
        ] if comparison_spec else [],
        "shared_filter_ids": [
            item.filter_id for item in plan.filters
        ]
        if plan
        else [],
        "dimension_ids": [
            item.dimension_id for item in plan.dimension_refs
        ]
        if plan
        else [],
        "source_ids": [
            item.source_id for item in plan.source_refs
        ]
        if plan
        else [],
        "baseline_operand_id": (
            comparison_spec.baseline_operand_id if comparison_spec else None
        ),
        "calculations": [
            item.value for item in comparison_spec.calculations
        ]
        if comparison_spec
        else [],
        "alignment_dimensions": [
            item.dimension_id
            for item in definition.alignment.alignment_dimensions
        ]
        if definition
        else [],
        "strategy_hint": result.strategy_hint.value,
        "complexity": result.complexity.classification.value,
        "confidence": result.confidence.level.value,
        "issue_codes": [item.code for item in result.issues],
        "cache_identity": result.cache_identity,
    }


def _cases() -> dict[str, dict[str, object]]:
    planner = ComparisonPlanner(catalog=catalog())
    revenue = metric("faturamento_comercial")
    gross = metric("faturamento_bruto")
    target = metric("meta_faturamento")
    june = window(2026, 6)
    july = window(2026, 7)
    august = window(2026, 8)
    period = intent(
        comparison(
            ComparisonKind.PERIOD_VS_PERIOD,
            [
                operand("june", "Junho", windows=[june]),
                operand("july", "Julho", windows=[july]),
            ],
            baseline="june",
        ),
        metrics=[revenue],
        windows=[june, july],
    )
    multi_period = intent(
        comparison(
            ComparisonKind.MULTI_PERIOD,
            [
                operand("june", "Junho", windows=[june]),
                operand("july", "Julho", windows=[july]),
                operand("august", "Agosto", windows=[august]),
            ],
            calculations=[ComparisonCalculation.VALUE],
            baseline=None,
        ),
        metrics=[revenue],
        windows=[june, july, august],
    )
    entity_comparison = intent(
        comparison(
            ComparisonKind.ENTITY_VS_ENTITY,
            [
                operand("center", "Centro", entities=[entity("filial:centro", "Centro")]),
                operand("south", "Sul", entities=[entity("filial:sul", "Sul")]),
            ],
            baseline="center",
        ),
        metrics=[revenue],
        windows=[july],
    )
    multi_entity = intent(
        comparison(
            ComparisonKind.MULTI_ENTITY,
            [
                operand("center", "Centro", entities=[entity("filial:centro", "Centro")]),
                operand("south", "Sul", entities=[entity("filial:sul", "Sul")]),
                operand("north", "Norte", entities=[entity("filial:norte", "Norte")]),
            ],
            calculations=[ComparisonCalculation.VALUE, ComparisonCalculation.RANK],
            baseline=None,
        ),
        metrics=[revenue],
        windows=[july],
    )
    metric_comparison = intent(
        comparison(
            ComparisonKind.METRIC_VS_METRIC,
            [
                operand("net", "Líquido", metrics=[revenue]),
                operand("gross", "Bruto", metrics=[gross]),
            ],
            baseline="net",
        ),
        metrics=[revenue, gross],
        windows=[july],
    )
    target_comparison = intent(
        comparison(
            ComparisonKind.ACTUAL_VS_TARGET,
            [
                operand("actual", "Realizado", metrics=[revenue]),
                operand("target", "Meta", metrics=[target]),
            ],
            baseline="target",
        ),
        metrics=[revenue, target],
        windows=[july],
    )
    composed = intent(
        comparison(
            ComparisonKind.PERIOD_VS_PERIOD,
            [
                operand(
                    "center_june",
                    "Centro junho",
                    windows=[june],
                    entities=[entity("filial:centro", "Centro")],
                ),
                operand(
                    "south_july",
                    "Sul julho",
                    windows=[july],
                    entities=[entity("filial:sul", "Sul")],
                ),
            ],
            baseline="center_june",
            alignment_dimensions=["produto"],
        ),
        metrics=[revenue],
        windows=[june, july],
        dimensions=[dimension("produto")],
        filters=[filter_spec("category", "categoria", "Bebidas")],
    )
    duplicate = intent(
        comparison(
            ComparisonKind.ENTITY_VS_ENTITY,
            [
                operand("first", "Centro", entities=[entity("filial:centro", "Centro")]),
                operand("second", "Centro", entities=[entity("filial:centro", "Centro")]),
            ],
        ),
        metrics=[revenue],
        windows=[july],
    )
    unsupported_target = target_comparison
    high_complexity = multi_period
    blocked = period
    results = {
        "period_vs_period": planner.plan(period, context()),
        "multi_period": planner.plan(multi_period, context()),
        "entity_vs_entity": planner.plan(entity_comparison, context()),
        "multi_entity": planner.plan(multi_entity, context()),
        "metric_vs_metric": planner.plan(metric_comparison, context()),
        "actual_vs_target": planner.plan(target_comparison, context()),
        "composed": planner.plan(composed, context()),
        "clarification": planner.plan(duplicate, context()),
        "unsupported": ComparisonPlanner(
            catalog=catalog(include_target=False)
        ).plan(unsupported_target, context()),
        "blocked": planner.plan(blocked, context(tenant_id=None)),
        "high_complexity": planner.plan(
            high_complexity,
            context(maximum_plan_complexity=10),
        ),
    }
    snapshots = {
        name: _snapshot(result)
        for name, result in results.items()
    }
    legacy_plan = results["period_vs_period"].plan
    snapshots["legacy_adapter"] = plan_to_legacy_comparison_input(legacy_plan)
    return snapshots


def test_comparison_plans_match_reviewed_goldens() -> None:
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert _cases() == expected


def test_every_required_golden_case_is_present() -> None:
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert set(expected) == {
        "period_vs_period",
        "multi_period",
        "entity_vs_entity",
        "multi_entity",
        "metric_vs_metric",
        "actual_vs_target",
        "composed",
        "clarification",
        "unsupported",
        "blocked",
        "high_complexity",
        "legacy_adapter",
    }
