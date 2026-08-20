from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from contracts.analytical_v2 import QueryIntentV2, QueryPlanV2

from .models import (
    ComparisonPlanningContext,
    ComparisonPlanningResult,
)
from .planner import ComparisonPlanner


logger = logging.getLogger("luminaai.services.comparison_planning.rollout")


@dataclass(frozen=True)
class ComparisonPlannerFeaturePolicy:
    enabled: bool = False
    shadow_mode: bool = True

    @classmethod
    def from_settings(cls, settings: object) -> "ComparisonPlannerFeaturePolicy":
        return cls(
            enabled=bool(
                getattr(settings, "COMPARISON_PLANNER_V2_ENABLED", False)
            ),
            shadow_mode=bool(
                getattr(settings, "COMPARISON_PLANNER_V2_SHADOW_MODE", True)
            ),
        )


class ComparisonPlannerGateway:
    def __init__(
        self,
        *,
        policy: ComparisonPlannerFeaturePolicy,
        planner: ComparisonPlanner | None = None,
    ) -> None:
        self._policy = policy
        self._planner = planner or ComparisonPlanner()

    def plan(
        self,
        intent: QueryIntentV2,
        context: ComparisonPlanningContext,
        *,
        legacy_plan: QueryPlanV2,
    ) -> ComparisonPlanningResult | None:
        modern = (
            self._planner.plan(intent, context)
            if self._policy.enabled or self._policy.shadow_mode
            else None
        )
        divergence = (
            self._shadow_divergence(legacy_plan, modern)
            if self._policy.shadow_mode and modern is not None
            else None
        )
        if divergence:
            fingerprint = hashlib.sha256(
                (
                    f"{context.tenant_id}:{intent.intent_kind.value}:"
                    f"{len(intent.time_windows)}"
                ).encode("utf-8")
            ).hexdigest()[:16]
            logger.info(
                "comparison_planner_shadow_divergence fingerprint=%s fields=%s",
                fingerprint,
                ",".join(sorted(divergence)),
            )
        if not self._policy.enabled:
            return None
        if modern is None:
            return None
        if divergence is not None:
            modern = modern.model_copy(update={"shadow_divergence": divergence})
        return modern

    def _shadow_divergence(
        self,
        legacy: QueryPlanV2,
        modern: ComparisonPlanningResult,
    ) -> dict[str, object] | None:
        modern_plan = modern.plan
        if modern_plan is None:
            return {"modern_plan": False, "readiness": modern.readiness.value}
        legacy_comparison = legacy.comparison
        modern_comparison = modern_plan.comparison
        fields: dict[str, object] = {}
        comparisons = {
            "kind": (
                legacy_comparison.kind.value if legacy_comparison else None,
                modern_comparison.kind.value if modern_comparison else None,
            ),
            "operand_count": (
                len(legacy_comparison.operands) if legacy_comparison else 0,
                len(modern_comparison.operands) if modern_comparison else 0,
            ),
            "metric_ids": (
                [item.metric_id for item in legacy.metric_refs],
                [item.metric_id for item in modern_plan.metric_refs],
            ),
            "period_count": (
                len(legacy.time_windows),
                len(modern_plan.time_windows),
            ),
            "shared_filter_count": (
                len(legacy.filters),
                len(modern_plan.filters),
            ),
            "specific_filter_counts": (
                [
                    len(operand.filters)
                    for operand in legacy_comparison.operands
                ] if legacy_comparison else [],
                [
                    len(operand.specific_filters)
                    for operand in modern.definition.operand_plans
                ] if modern.definition else [],
            ),
            "baseline": (
                legacy_comparison.baseline_operand_id if legacy_comparison else None,
                modern_comparison.baseline_operand_id if modern_comparison else None,
            ),
            "dimensions": (
                [item.dimension_id for item in legacy.dimension_refs],
                [item.dimension_id for item in modern_plan.dimension_refs],
            ),
            "calculations": (
                [
                    item.value
                    for item in legacy_comparison.calculations
                ] if legacy_comparison else [],
                [
                    item.value
                    for item in modern_comparison.calculations
                ] if modern_comparison else [],
            ),
            "readiness": (
                legacy.intent.readiness.value,
                modern.readiness.value,
            ),
            "confidence": (
                str(legacy.confidence.score),
                str(modern.confidence.score),
            ),
            "strategy_hint": (
                "LEGACY_COMPATIBILITY",
                modern.strategy_hint.value,
            ),
        }
        for name, (legacy_value, modern_value) in comparisons.items():
            if legacy_value != modern_value:
                fields[name] = {
                    "legacy": legacy_value,
                    "modern": modern_value,
                }
        return fields or None

    @property
    def enabled(self) -> bool:
        return self._policy.enabled
