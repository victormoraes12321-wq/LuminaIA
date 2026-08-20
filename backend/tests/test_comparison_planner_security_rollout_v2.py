from __future__ import annotations

import json
from dataclasses import replace
from uuid import UUID

import pytest

from contracts.analytical_v2 import (
    ComparisonCalculation,
    ComparisonKind,
    ExecutionReadiness,
    PipelineKind,
    build_intent_v2,
    build_plan_v2,
)
from services.comparison_planning import (
    COMPARISON_PLANNER_VERSION,
    ComparisonLegacyAdapterError,
    ComparisonPlanner,
    ComparisonPlannerFeaturePolicy,
    ComparisonPlannerGateway,
    StaticComparisonCatalog,
    plan_to_legacy_comparison_input,
)
from services.comparison_planning.legacy_adapter import (
    build_trusted_planning_context,
)

from comparison_planner_fixtures import (
    SOURCE_SALES,
    TENANT_A,
    TENANT_B,
    catalog,
    comparison,
    context,
    entity,
    filter_spec,
    intent,
    metric,
    operand,
    window,
)


pytestmark = [
    pytest.mark.unit,
    pytest.mark.no_database,
    pytest.mark.security,
]


def _period_intent():
    revenue = metric("faturamento_comercial")
    june = window(2026, 6)
    july = window(2026, 7)
    return intent(
        comparison(
            ComparisonKind.PERIOD_VS_PERIOD,
            [
                operand("june", "Junho", metrics=[revenue], windows=[june]),
                operand("july", "Julho", metrics=[revenue], windows=[july]),
            ],
            baseline="june",
        ),
        metrics=[revenue],
        windows=[june, july],
    )


def test_plan_without_tenant_is_never_ready() -> None:
    result = ComparisonPlanner(catalog=catalog()).plan(
        _period_intent(),
        context(tenant_id=None),
    )
    assert result.readiness == ExecutionReadiness.BLOCKED
    assert result.plan is not None and result.plan.scope is None
    assert "MISSING_TRUSTED_TENANT" in {item.code for item in result.issues}


def test_oracle_source_is_blocked() -> None:
    result = ComparisonPlanner(catalog=catalog()).plan(
        _period_intent(),
        context(allowed_sources=("oracle", SOURCE_SALES)),
    )
    assert result.readiness == ExecutionReadiness.BLOCKED
    assert "ORACLE_SOURCE_BLOCKED" in {item.code for item in result.issues}


def test_unknown_metric_is_not_replaced_by_revenue() -> None:
    unknown = metric("metrica_inexistente")
    source = intent(
        comparison(
            ComparisonKind.METRIC_VS_METRIC,
            [
                operand("one", "Desconhecida", metrics=[unknown]),
                operand("two", "Também desconhecida", metrics=[unknown]),
            ],
            calculations=[ComparisonCalculation.VALUE],
        ),
        metrics=[unknown],
        windows=[window(2026, 7)],
    )
    expanded_context = context().model_copy(
        update={
            "allowed_metric_ids": (
                *context().allowed_metric_ids,
                "metrica_inexistente",
            )
        }
    )
    result = ComparisonPlanner(catalog=catalog()).plan(source, expanded_context)
    assert result.readiness == ExecutionReadiness.UNSUPPORTED
    assert "UNKNOWN_METRIC" in {item.code for item in result.issues}
    assert result.plan is not None
    assert all(
        item.metric_id != "faturamento_comercial"
        for item in result.plan.metric_refs
    )


def test_metric_without_permission_is_blocked() -> None:
    restricted = context().model_copy(
        update={"allowed_metric_ids": ("quantidade_vendida",)}
    )
    result = ComparisonPlanner(catalog=catalog()).plan(
        _period_intent(),
        restricted,
    )
    assert result.readiness == ExecutionReadiness.BLOCKED
    assert "METRIC_NOT_PERMITTED" in {item.code for item in result.issues}


def test_metric_contract_version_mismatch_is_unsupported() -> None:
    revenue = metric("faturamento_comercial").model_copy(
        update={"metric_version": "untrusted/9"}
    )
    june = window(2026, 6)
    july = window(2026, 7)
    source = intent(
        comparison(
            ComparisonKind.PERIOD_VS_PERIOD,
            [
                operand("one", "Junho", metrics=[revenue], windows=[june]),
                operand("two", "Julho", metrics=[revenue], windows=[july]),
            ],
        ),
        metrics=[revenue],
        windows=[june, july],
    )
    result = ComparisonPlanner(catalog=catalog()).plan(source, context())
    assert result.readiness == ExecutionReadiness.UNSUPPORTED
    assert "METRIC_CONTRACT_MISMATCH" in {
        item.code for item in result.issues
    }


@pytest.mark.multitenant
def test_entity_with_same_alias_is_resolved_only_inside_tenant() -> None:
    revenue = metric("faturamento_comercial")
    source = intent(
        comparison(
            ComparisonKind.ENTITY_VS_ENTITY,
            [
                operand(
                    "center",
                    "Centro",
                    entities=[entity("filial:centro", "Centro")],
                ),
                operand(
                    "south",
                    "Sul",
                    entities=[entity("filial:sul", "Sul")],
                ),
            ],
        ),
        metrics=[revenue],
        windows=[window(2026, 7)],
    )
    tenant_a = ComparisonPlanner(catalog=catalog()).plan(source, context())
    tenant_b = ComparisonPlanner(catalog=catalog()).plan(
        source,
        context(tenant_id=TENANT_B),
    )
    assert tenant_a.readiness == ExecutionReadiness.READY
    assert tenant_b.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED


def test_entity_role_permission_is_enforced() -> None:
    base = catalog()
    restricted_entity = replace(
        base.entities[(TENANT_A, "filial:sul")],
        permitted_roles=("ADMIN",),
    )
    restricted_catalog = StaticComparisonCatalog(
        metrics=base.metrics,
        dimensions=base.dimensions,
        entities={
            **base.entities,
            (TENANT_A, "filial:sul"): restricted_entity,
        },
        targets=base.targets,
    )
    revenue = metric("faturamento_comercial")
    source = intent(
        comparison(
            ComparisonKind.ENTITY_VS_ENTITY,
            [
                operand(
                    "center",
                    "Centro",
                    entities=[entity("filial:centro", "Centro")],
                ),
                operand(
                    "south",
                    "Sul",
                    entities=[entity("filial:sul", "Sul")],
                ),
            ],
        ),
        metrics=[revenue],
        windows=[window(2026, 7)],
    )
    result = ComparisonPlanner(catalog=restricted_catalog).plan(source, context())
    assert result.readiness == ExecutionReadiness.BLOCKED
    assert "ENTITY_NOT_PERMITTED" in {item.code for item in result.issues}


@pytest.mark.multitenant
def test_permission_fingerprint_changes_cache_identity() -> None:
    planner = ComparisonPlanner(catalog=catalog())
    first = planner.plan(
        _period_intent(),
        context(permission_fingerprint="permission:test:a"),
    )
    second = planner.plan(
        _period_intent(),
        context(permission_fingerprint="permission:test:b"),
    )
    assert first.cache_identity != second.cache_identity


def test_human_labels_do_not_change_cache_identity() -> None:
    source = _period_intent()
    changed_operands = [
        item.model_copy(update={"label": f"Outro nome {index}"})
        for index, item in enumerate(source.comparison.operands, start=1)
    ]
    changed_comparison = source.comparison.model_copy(
        update={"operands": changed_operands}
    )
    changed = source.model_copy(update={"comparison": changed_comparison})
    planner = ComparisonPlanner(catalog=catalog())
    assert planner.plan(source, context()).cache_identity == planner.plan(
        changed,
        context(),
    ).cache_identity


def test_filter_technical_id_does_not_change_cache_identity() -> None:
    shared = filter_spec("filial_first", "filial", "1")
    source = _period_intent().model_copy(update={"filters": [shared]})
    changed = source.model_copy(
        update={
            "filters": [
                shared.model_copy(update={"filter_id": "filial_second"})
            ]
        }
    )
    planner = ComparisonPlanner(catalog=catalog())
    assert planner.plan(source, context()).cache_identity == planner.plan(
        changed,
        context(),
    ).cache_identity


def test_feature_flag_disabled_returns_legacy_plan() -> None:
    normalized = build_intent_v2(
        "Compare o faturamento de 06/2026 e 07/2026",
        pipeline=PipelineKind.NEW,
    )
    plan = build_plan_v2(
        normalized,
        tenant_id=TENANT_A,
        user_id=None,
        user_role="CONSULTA",
        session_id="s",
        allowed_source_ids=[SOURCE_SALES],
        pipeline=PipelineKind.NEW,
        comparison_planner_enabled=False,
        comparison_planner_shadow_mode=False,
    )
    assert plan.contract.adapter_used == "build_plan_v2"
    assert "comparison_planner" not in plan.contract.extensions
    assert plan.cache_identity is None


def test_shadow_mode_does_not_change_legacy_selection_when_disabled() -> None:
    normalized = build_intent_v2(
        "Compare o faturamento de 06/2026 e 07/2026",
        pipeline=PipelineKind.NEW,
    )
    plan = build_plan_v2(
        normalized,
        tenant_id=TENANT_A,
        user_id=None,
        user_role="CONSULTA",
        session_id="s",
        allowed_source_ids=[SOURCE_SALES],
        pipeline=PipelineKind.NEW,
        comparison_planner_enabled=False,
        comparison_planner_shadow_mode=True,
    )
    assert plan.contract.adapter_used == "build_plan_v2"
    assert plan.cache_identity is None


def test_gateway_records_structural_shadow_divergence() -> None:
    normalized = build_intent_v2(
        "Compare o faturamento de 06/2026 e 07/2026",
        pipeline=PipelineKind.NEW,
    )
    legacy = build_plan_v2(
        normalized,
        tenant_id=TENANT_A,
        user_id=None,
        user_role="CONSULTA",
        session_id="s",
        allowed_source_ids=[SOURCE_SALES],
        pipeline=PipelineKind.NEW,
        comparison_planner_enabled=False,
        comparison_planner_shadow_mode=False,
    )
    planning_context = build_trusted_planning_context(
        normalized,
        tenant_id=TENANT_A,
        user_id=None,
        user_role="CONSULTA",
        session_id="s",
        allowed_source_ids=[SOURCE_SALES],
        permission_fingerprint=legacy.scope.permission_fingerprint,
        feature_flags={"enabled": True, "shadow_mode": True},
    )
    result = ComparisonPlannerGateway(
        policy=ComparisonPlannerFeaturePolicy(enabled=True, shadow_mode=True)
    ).plan(normalized, planning_context, legacy_plan=legacy)
    assert result is not None
    assert result.shadow_divergence is not None
    assert "strategy_hint" in result.shadow_divergence


def test_shadow_mode_compares_operand_specific_filter_counts() -> None:
    normalized = _period_intent()
    legacy = ComparisonPlanner(catalog=catalog()).plan(
        normalized,
        context(),
    ).plan
    assert legacy is not None
    changed_operands = list(normalized.comparison.operands)
    changed_operands[0] = changed_operands[0].model_copy(
        update={"filters": [filter_spec("branch", "filial", "1")]}
    )
    changed = normalized.model_copy(
        update={
            "comparison": normalized.comparison.model_copy(
                update={"operands": changed_operands}
            )
        }
    )
    result = ComparisonPlannerGateway(
        policy=ComparisonPlannerFeaturePolicy(enabled=True, shadow_mode=True),
        planner=ComparisonPlanner(catalog=catalog()),
    ).plan(changed, context(), legacy_plan=legacy)
    assert result is not None
    assert result.shadow_divergence is not None
    assert result.shadow_divergence["specific_filter_counts"] == {
        "legacy": [0, 0],
        "modern": [1, 0],
    }


def test_legacy_adapter_accepts_only_lossless_two_operand_plan() -> None:
    normalized = build_intent_v2(
        "Compare o faturamento de 06/2026 e 07/2026",
        pipeline=PipelineKind.NEW,
    )
    plan = build_plan_v2(
        normalized,
        tenant_id=TENANT_A,
        user_id=None,
        user_role="CONSULTA",
        session_id="s",
        allowed_source_ids=[SOURCE_SALES],
        pipeline=PipelineKind.NEW,
    )
    adapted = plan_to_legacy_comparison_input(plan)
    assert adapted["kind"] == "PERIOD_VS_PERIOD"
    assert len(adapted["operands"]) == 2
    assert "sql" not in json.dumps(adapted).lower()


def test_legacy_adapter_rejects_multi_period_without_truncating() -> None:
    source = build_intent_v2(
        "Compare o faturamento de 05/2026, 06/2026 e 07/2026",
        pipeline=PipelineKind.NEW,
    )
    plan = build_plan_v2(
        source,
        tenant_id=TENANT_A,
        user_id=None,
        user_role="CONSULTA",
        session_id="s",
        allowed_source_ids=[SOURCE_SALES],
        pipeline=PipelineKind.NEW,
    )
    with pytest.raises(ComparisonLegacyAdapterError, match="exactly two"):
        plan_to_legacy_comparison_input(plan)


def test_plan_contains_no_credentials_or_sql() -> None:
    result = ComparisonPlanner(catalog=catalog()).plan(
        _period_intent(),
        context(),
    )
    serialized = result.model_dump_json().lower()
    for forbidden in (
        "password",
        "secret_key",
        "api_key",
        "authorization",
        "select ",
        " from ",
        " where ",
    ):
        assert forbidden not in serialized
