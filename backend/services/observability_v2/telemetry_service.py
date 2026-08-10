"""Operational telemetry service for recording events, metric points, rollups, and health."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock
from typing import Mapping

from contracts.observability_v2 import (
    ObservabilityHealthV2,
    ObservabilityReadinessV2,
    OperationalEventV2,
    OperationalEventTypeV2,
    OperationalMetricPointV2,
    OperationalMetricRollupV2,
    FeatureModeV2,
)
from services.observability_v2.cardinality import OperationalMetricCardinalityGuard
from services.observability_v2.event_registry import OperationalEventRegistryV2
from services.observability_v2.metric_registry import OperationalMetricRegistryV2
from services.observability_v2.redaction import ObservabilityRedactionService

_MAX_BUFFER_SIZE = 1000


class OperationalTelemetryService:
    def __init__(
        self,
        redaction_service: ObservabilityRedactionService | None = None,
        cardinality_guard: OperationalMetricCardinalityGuard | None = None,
    ) -> None:
        self.redaction = redaction_service or ObservabilityRedactionService()
        self.cardinality = cardinality_guard or OperationalMetricCardinalityGuard()
        self._events: list[OperationalEventV2] = []
        self._metric_points: list[OperationalMetricPointV2] = []
        self._start_time = datetime.now(timezone.utc)
        self._lock = Lock()

    def record_event(
        self,
        event_type: OperationalEventTypeV2,
        *,
        trace_id: str,
        span_id: str,
        service: str = "backend",
        attributes: Mapping[str, Any] | tuple[tuple[str, str], ...] = (),
    ) -> OperationalEventV2 | None:
        if not OperationalEventRegistryV2.is_allowlisted(event_type):
            return None
        cls = OperationalEventRegistryV2.get_classification(event_type)
        sanitized_attrs = self.redaction.sanitize_attributes(attributes)
        event = OperationalEventV2(
            event_id=f"evt_{uuid.uuid4().hex}",
            event_type=event_type,
            classification=cls,
            trace_id=trace_id,
            span_id=span_id,
            timestamp=datetime.now(timezone.utc),
            service=service,
            attributes=sanitized_attrs,
        )
        with self._lock:
            self._events.append(event)
            if len(self._events) > _MAX_BUFFER_SIZE:
                self._events.pop(0)
        return event

    def record_metric(
        self,
        metric_id: str,
        value: int | float | Decimal,
        *,
        labels: Mapping[str, str] | tuple[tuple[str, str], ...] = (),
    ) -> OperationalMetricPointV2 | None:
        defn = OperationalMetricRegistryV2.get_definition(metric_id)
        if defn is None:
            return None

        val_dec = Decimal(str(value))
        clean_labels = self.cardinality.validate_and_normalize_labels(labels, allowed_keys=defn.allowed_labels)
        point = OperationalMetricPointV2(
            metric_id=metric_id,
            value=val_dec,
            timestamp=datetime.now(timezone.utc),
            labels=clean_labels,
        )
        with self._lock:
            self._metric_points.append(point)
            if len(self._metric_points) > _MAX_BUFFER_SIZE:
                self._metric_points.pop(0)
        return point

    def get_events(self, limit: int = 100) -> tuple[OperationalEventV2, ...]:
        with self._lock:
            return tuple(self._events[-limit:])

    def get_metric_points(self, limit: int = 100) -> tuple[OperationalMetricPointV2, ...]:
        with self._lock:
            return tuple(self._metric_points[-limit:])

    def compute_rollups(self) -> tuple[OperationalMetricRollupV2, ...]:
        with self._lock:
            points = list(self._metric_points)
        if not points:
            return ()

        grouped: dict[tuple[str, tuple[tuple[str, str], ...]], list[OperationalMetricPointV2]] = defaultdict(list)
        for pt in points:
            grouped[(pt.metric_id, pt.labels)].append(pt)

        rollups: list[OperationalMetricRollupV2] = []
        for (metric_id, labels), pts in grouped.items():
            vals = [p.value for p in pts]
            min_ts = min(p.timestamp for p in pts)
            max_ts = max(p.timestamp for p in pts)
            cnt = len(vals)
            s = sum(vals)
            mn = min(vals)
            mx = max(vals)
            avg = s / Decimal(cnt)
            rollups.append(
                OperationalMetricRollupV2(
                    metric_id=metric_id,
                    window_start=min_ts,
                    window_end=max_ts,
                    count=cnt,
                    sum_value=s,
                    min_value=mn,
                    max_value=mx,
                    avg_value=avg,
                    labels=labels,
                )
            )
        return tuple(rollups)

    def get_health(self) -> ObservabilityHealthV2:
        now = datetime.now(timezone.utc)
        uptime = Decimal(str(max(0.0, (now - self._start_time).total_seconds())))
        with self._lock:
            evt_cnt = len(self._events)
        return ObservabilityHealthV2(
            status="healthy",
            uptime_seconds=uptime,
            events_recorded=evt_cnt,
            dropped_telemetry_count=self.cardinality.dropped_count,
        )

    def get_readiness(self, mode: FeatureModeV2 = FeatureModeV2.LEGACY_ONLY) -> ObservabilityReadinessV2:
        return ObservabilityReadinessV2(
            ready=True,
            mode=mode,
            database_allowed=True,
            registries_loaded=True,
            reasons=(),
        )
