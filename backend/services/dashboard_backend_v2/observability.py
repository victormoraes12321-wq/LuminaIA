"""Structural-only observability for the governed dashboard backend."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from threading import Lock


DASHBOARD_STRUCTURAL_METRICS = frozenset({
    "dashboards_by_lifecycle", "drafts", "revisions", "visual_revisions",
    "semantic_revisions", "review_duration_ms", "approval_count", "publications",
    "rollbacks", "cas_conflicts", "idempotency_conflicts", "access_denied",
    "runtime_requests", "runtime_complete", "runtime_partial", "runtime_blocked",
    "widgets_executed", "widget_failures", "cache_hits", "cache_misses",
    "materialization_hits", "execution_latency_ms", "blueprint_validation_failures",
    "classification_blocks", "tenant_isolation_blocks", "rollout_mode",
})

ALLOWED_DIMENSIONS = frozenset({"lifecycle", "status", "cache_indicator", "rollout_mode"})


@dataclass(frozen=True, slots=True)
class DashboardMetricPointV2:
    metric: str
    value: float
    dimensions: tuple[tuple[str, str], ...]


class DashboardObservabilityV2:
    """Small dependency-free sink; it cannot accept payloads or business values."""

    def __init__(self) -> None:
        self._values: Counter[tuple[str, tuple[tuple[str, str], ...]]] = Counter()
        self._lock = Lock()

    def record(
        self,
        metric: str,
        *,
        value: int | float = 1,
        dimensions: dict[str, str] | None = None,
    ) -> None:
        if metric not in DASHBOARD_STRUCTURAL_METRICS:
            raise ValueError("dashboard metric is not structurally allowlisted")
        if isinstance(value, bool) or value < 0:
            raise ValueError("dashboard metric value must be a non-negative number")
        safe_dimensions = dimensions or {}
        if set(safe_dimensions) - ALLOWED_DIMENSIONS:
            raise ValueError("dashboard metric dimension is not allowlisted")
        normalized = tuple(sorted((key, str(item)[:64]) for key, item in safe_dimensions.items()))
        with self._lock:
            self._values[(metric, normalized)] += value

    def snapshot(self) -> tuple[DashboardMetricPointV2, ...]:
        with self._lock:
            return tuple(
                DashboardMetricPointV2(metric=metric, value=float(value), dimensions=dimensions)
                for (metric, dimensions), value in sorted(self._values.items())
            )

