from __future__ import annotations

from datetime import datetime, time, timezone
from uuid import UUID

from pydantic import JsonValue

from contracts.analytical_v2 import QueryIntentV2, QueryPlanV2

from .models import ComparisonPlanningContext
from .providers import (
    DEFAULT_COMPARISON_DIMENSIONS,
    DEFAULT_COMPARISON_ENTITY_TYPES,
    ComparisonCatalogProvider,
    default_comparison_catalog,
)


class ComparisonLegacyAdapterError(ValueError):
    pass


def build_trusted_planning_context(
    intent: QueryIntentV2,
    *,
    tenant_id: UUID | None,
    user_id: UUID | None,
    user_role: str,
    session_id: str | None,
    allowed_source_ids: list[str],
    permission_fingerprint: str,
    feature_flags: dict[str, bool],
    catalog: ComparisonCatalogProvider | None = None,
    reference_datetime: datetime | None = None,
) -> ComparisonPlanningContext:
    provider = catalog or default_comparison_catalog()
    resolved_reference = reference_datetime or _reference_from_intent(intent)
    timezone_name = (
        intent.time_windows[0].timezone
        if intent.time_windows
        else "America/Sao_Paulo"
    )
    return ComparisonPlanningContext(
        tenant_id=tenant_id,
        user_id=user_id,
        user_role=user_role,
        session_id=session_id,
        timezone=timezone_name,
        locale="pt-BR",
        allowed_metric_ids=provider.metric_ids(),
        allowed_dimension_ids=DEFAULT_COMPARISON_DIMENSIONS,
        allowed_entity_types=DEFAULT_COMPARISON_ENTITY_TYPES,
        allowed_source_ids=tuple(
            dict.fromkeys(source_id.lower() for source_id in allowed_source_ids)
        ),
        permission_fingerprint=permission_fingerprint,
        reference_datetime=resolved_reference,
        feature_flags=feature_flags,
        source="trusted_backend_adapter",
    )


def plan_to_legacy_comparison_input(
    plan: QueryPlanV2,
) -> dict[str, JsonValue]:
    comparison = plan.comparison
    if comparison is None:
        raise ComparisonLegacyAdapterError("comparison plan is required")
    if plan.intent.readiness.value != "READY":
        raise ComparisonLegacyAdapterError("blocked plan cannot be adapted for execution")
    if len(comparison.operands) != 2:
        raise ComparisonLegacyAdapterError(
            "legacy comparison engine supports exactly two operands"
        )
    if len(plan.metric_refs) != 1:
        raise ComparisonLegacyAdapterError(
            "legacy comparison engine supports exactly one shared metric"
        )
    operands: list[dict[str, JsonValue]] = []
    for operand in comparison.operands:
        if len(operand.time_windows) != 1:
            raise ComparisonLegacyAdapterError(
                "legacy comparison engine requires one period per operand"
            )
        window = operand.time_windows[0]
        operands.append(
            {
                "operand_id": operand.operand_id,
                "start": window.start.isoformat(),
                "end": window.end.isoformat(),
                "metric_id": plan.metric_refs[0].metric_id,
                "filters": [
                    item.model_dump(mode="json")
                    for item in [*plan.filters, *operand.filters]
                ],
            }
        )
    metadata = plan.contract.extensions.get("comparison_planner")
    planner_version = (
        str(metadata.get("planner_version", "legacy"))
        if isinstance(metadata, dict)
        else "legacy"
    )
    return {
        "planner_version": planner_version,
        "kind": comparison.kind.value,
        "baseline_operand_id": comparison.baseline_operand_id,
        "calculations": [item.value for item in comparison.calculations],
        "operands": operands,
    }


def _reference_from_intent(intent: QueryIntentV2) -> datetime:
    if intent.time_windows:
        return datetime.combine(
            max(window.end for window in intent.time_windows),
            time(hour=12),
            tzinfo=timezone.utc,
        )
    return datetime(1970, 1, 1, 12, tzinfo=timezone.utc)
