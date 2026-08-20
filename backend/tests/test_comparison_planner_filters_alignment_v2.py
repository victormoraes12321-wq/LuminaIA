from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic import ValidationError

from contracts.analytical_v2 import (
    ComparisonCalculation,
    ComparisonKind,
    DimensionRole,
    ExecutionReadiness,
    FieldOrigin,
    TemporalGranularity,
)
from services.comparison_planning import (
    AlignmentCompatibility,
    ComparisonPlanner,
    PlanComplexityClassification,
    StaticComparisonCatalog,
)

from comparison_planner_fixtures import (
    SOURCE_SALES,
    TENANT_A,
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


pytestmark = [pytest.mark.unit, pytest.mark.no_database]


def _entity_comparison(
    *,
    shared_filters=None,
    left_filters=None,
    right_filters=None,
    dimensions=None,
    alignment_dimensions=None,
):
    revenue = metric("faturamento_comercial")
    july = window(2026, 7)
    return intent(
        comparison(
            ComparisonKind.ENTITY_VS_ENTITY,
            [
                operand(
                    "center",
                    "Centro",
                    entities=[entity("filial:centro", "Centro")],
                    filters=left_filters,
                ),
                operand(
                    "south",
                    "Sul",
                    entities=[entity("filial:sul", "Sul")],
                    filters=right_filters,
                ),
            ],
            baseline="center",
            alignment_dimensions=alignment_dimensions,
        ),
        metrics=[revenue],
        windows=[july],
        dimensions=dimensions,
        filters=shared_filters,
    )


def test_shared_filter_stays_shared() -> None:
    category = filter_spec("category", "categoria", "Bebidas")
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(shared_filters=[category]),
        context(),
    )
    assert result.readiness == ExecutionReadiness.READY
    assert result.definition is not None
    assert result.definition.shared_filters == (category,)
    assert all(
        category not in operand.specific_filters
        for operand in result.definition.operand_plans
    )


def test_specific_filters_never_become_global() -> None:
    left = filter_spec("left_category", "categoria", "Bebidas")
    right = filter_spec("right_category", "categoria", "Alimentos")
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(left_filters=[left], right_filters=[right]),
        context(),
    )
    assert result.readiness == ExecutionReadiness.READY
    assert result.definition is not None
    assert result.definition.shared_filters == ()
    assert result.definition.operand_plans[0].specific_filters == (left,)
    assert result.definition.operand_plans[1].specific_filters == (right,)


def test_conflicting_explicit_filters_require_clarification() -> None:
    shared = filter_spec("shared_category", "categoria", "Bebidas")
    specific = filter_spec("specific_category", "categoria", "Alimentos")
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(
            shared_filters=[shared],
            left_filters=[specific],
        ),
        context(),
    )
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert result.clarification is not None
    assert "CONFLICTING_FILTERS" in {item.code for item in result.issues}


def test_explicit_filter_can_override_inherited_filter_without_blocking() -> None:
    inherited = filter_spec(
        "shared_category",
        "categoria",
        "Bebidas",
        origin=FieldOrigin.INHERITED_CONVERSATION,
    )
    explicit = filter_spec("specific_category", "categoria", "Alimentos")
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(
            shared_filters=[inherited],
            left_filters=[explicit],
        ),
        context(),
    )
    assert result.readiness == ExecutionReadiness.READY
    assert result.definition is not None
    assert result.definition.filter_partition.conflicting_filters == (
        "center:categoria",
    )


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "x'; DROP TABLE vendas;--",
        "UNION SELECT secret",
        "DELETE FROM x",
    ],
)
def test_contract_rejects_sql_like_filter_values_before_planning(
    unsafe_value: str,
) -> None:
    with pytest.raises(ValidationError):
        filter_spec("unsafe", "categoria", unsafe_value)


def test_planner_blocks_comment_style_filter_payload() -> None:
    unsafe = filter_spec("unsafe", "categoria", "/* comment */")
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(shared_filters=[unsafe]),
        context(),
    )
    assert result.readiness == ExecutionReadiness.BLOCKED
    assert "UNSAFE_FILTER_VALUE" in {item.code for item in result.issues}


def test_tenant_is_not_a_free_filter() -> None:
    tenant_filter = filter_spec("tenant", "tenant_id", str(TENANT_A))
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(shared_filters=[tenant_filter]),
        context(),
    )
    assert result.readiness == ExecutionReadiness.BLOCKED
    assert "TENANT_AS_FREE_FILTER" in {item.code for item in result.issues}


def test_unknown_filter_identifier_is_blocked() -> None:
    unknown = filter_spec("unknown", "campo_desconhecido", "x")
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(shared_filters=[unknown]),
        context(),
    )
    assert result.readiness == ExecutionReadiness.BLOCKED
    assert "FILTER_FIELD_NOT_PERMITTED" in {
        item.code for item in result.issues
    }


def test_alignment_uses_canonical_dimension_id() -> None:
    product = dimension("produto", DimensionRole.GROUPING)
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(
            dimensions=[product],
            alignment_dimensions=["produto"],
        ),
        context(),
    )
    assert result.readiness == ExecutionReadiness.READY
    assert result.definition is not None
    assert [
        item.dimension_id
        for item in result.definition.alignment.alignment_dimensions
    ] == ["produto"]
    assert result.definition.alignment.compatibility_status == (
        AlignmentCompatibility.COMPATIBLE
    )


def test_unresolved_alignment_dimension_requires_clarification() -> None:
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(alignment_dimensions=["produto"]),
        context(),
    )
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert "UNRESOLVED_ALIGNMENT_DIMENSION" in {
        item.code for item in result.issues
    }


def test_dimension_without_permission_is_unsupported() -> None:
    product = dimension("produto")
    restricted = context().model_copy(
        update={"allowed_dimension_ids": ("filial",)}
    )
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(dimensions=[product]),
        restricted,
    )
    assert result.readiness == ExecutionReadiness.UNSUPPORTED
    assert "DIMENSION_NOT_PERMITTED" in {item.code for item in result.issues}


def test_incompatible_temporal_series_granularity_requires_clarification() -> None:
    revenue = metric("faturamento_comercial")
    monthly = window(2026, 6, granularity=TemporalGranularity.MONTH)
    daily = monthly.model_copy(
        update={
            "window_id": "daily",
            "label": "Dia",
            "start": monthly.start,
            "end": monthly.start,
            "granularity": TemporalGranularity.DAY,
        }
    )
    source = intent(
        comparison(
            ComparisonKind.PERIOD_VS_PERIOD,
            [
                operand("month", "Mês", windows=[monthly]),
                operand("day", "Dia", windows=[daily]),
            ],
            alignment_dimensions=["mes"],
        ),
        metrics=[revenue],
        windows=[monthly, daily],
        dimensions=[dimension("mes")],
    )
    result = ComparisonPlanner(catalog=catalog()).plan(source, context())
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert result.definition is not None
    assert result.definition.alignment.compatibility_status == (
        AlignmentCompatibility.INCOMPATIBLE
    )


def test_different_granularities_as_totals_only_generate_warning() -> None:
    revenue = metric("faturamento_comercial")
    monthly = window(2026, 6, granularity=TemporalGranularity.MONTH)
    daily = monthly.model_copy(
        update={
            "window_id": "daily",
            "label": "Dia",
            "start": monthly.start,
            "end": monthly.start,
            "granularity": TemporalGranularity.DAY,
        }
    )
    source = intent(
        comparison(
            ComparisonKind.PERIOD_VS_PERIOD,
            [
                operand("month", "Mês", windows=[monthly]),
                operand("day", "Dia", windows=[daily]),
            ],
        ),
        metrics=[revenue],
        windows=[monthly, daily],
    )
    result = ComparisonPlanner(catalog=catalog()).plan(source, context())
    assert result.readiness == ExecutionReadiness.READY
    assert result.definition is not None
    assert result.definition.alignment.compatibility_status == (
        AlignmentCompatibility.COMPATIBLE_WITH_WARNINGS
    )


@pytest.mark.parametrize(
    ("months", "expected"),
    [
        ([6, 7], PlanComplexityClassification.LOW),
        (
            list(range(1, 9)),
            PlanComplexityClassification.MEDIUM,
        ),
    ],
)
def test_complexity_classification(
    months: list[int],
    expected: PlanComplexityClassification,
) -> None:
    revenue = metric("faturamento_comercial")
    windows = [window(2026, month) for month in months]
    operands = [
        operand(f"o{index}", item.label, windows=[item])
        for index, item in enumerate(windows, start=1)
    ]
    source = intent(
        comparison(
            ComparisonKind.MULTI_PERIOD
            if len(operands) > 2
            else ComparisonKind.PERIOD_VS_PERIOD,
            operands,
            calculations=[ComparisonCalculation.VALUE],
        ),
        metrics=[revenue],
        windows=windows,
    )
    result = ComparisonPlanner(catalog=catalog()).plan(source, context())
    assert result.complexity.classification == expected


@pytest.mark.parametrize(
    "limited_context",
    [
        context(maximum_operands=2),
        context(maximum_plan_complexity=10),
        context(maximum_series=1),
    ],
)
def test_complexity_limits_reject_without_silent_removal(
    limited_context,
) -> None:
    revenue = metric("faturamento_comercial")
    windows = [window(2026, month) for month in (1, 2, 3)]
    source = intent(
        comparison(
            ComparisonKind.MULTI_PERIOD,
            [
                operand(f"o{index}", item.label, windows=[item])
                for index, item in enumerate(windows, start=1)
            ],
            calculations=[ComparisonCalculation.VALUE],
        ),
        metrics=[revenue],
        windows=windows,
    )
    result = ComparisonPlanner(catalog=catalog()).plan(source, limited_context)
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert result.complexity.classification == PlanComplexityClassification.REJECTED
    assert result.plan is not None and result.plan.comparison is not None
    assert len(result.plan.comparison.operands) == 3


@pytest.mark.multitenant
def test_unknown_or_cross_tenant_entity_is_not_resolved() -> None:
    revenue = metric("faturamento_comercial")
    source = intent(
        comparison(
            ComparisonKind.ENTITY_VS_ENTITY,
            [
                operand("known", "Sul", entities=[entity("filial:sul", "Sul")]),
                operand(
                    "unknown",
                    "Tenant B",
                    entities=[entity("filial:exclusiva-b", "Filial B")],
                ),
            ],
        ),
        metrics=[revenue],
        windows=[window(2026, 7)],
    )
    result = ComparisonPlanner(catalog=catalog()).plan(source, context())
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert "UNKNOWN_OR_CROSS_TENANT_ENTITY" in {
        item.code for item in result.issues
    }


def test_source_not_permitted_blocks_plan() -> None:
    result = ComparisonPlanner(catalog=catalog()).plan(
        _entity_comparison(),
        context(allowed_sources=("outra_fonte",)),
    )
    assert result.readiness == ExecutionReadiness.BLOCKED
    assert "SOURCE_NOT_PERMITTED" in {item.code for item in result.issues}
