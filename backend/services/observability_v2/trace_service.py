"""Structural trace and span service for observing V2 execution steps."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from contracts.observability_v2 import SpanCategoryV2, SpanStatusV2, SpanSummaryV2, TraceSummaryV2
from services.observability_v2.redaction import ObservabilityRedactionService


class SpanService:
    def __init__(
        self,
        name: str,
        category: SpanCategoryV2,
        *,
        trace_id: str,
        parent_span_id: str | None = None,
        redaction_service: ObservabilityRedactionService | None = None,
    ) -> None:
        self.name = name
        self.category = category
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        self.span_id = f"spn_{uuid.uuid4().hex}"
        self.redaction = redaction_service or ObservabilityRedactionService()
        self.start_time = datetime.now(timezone.utc)
        self._perf_start = time.perf_counter()
        self.status = SpanStatusV2.OK
        self.attributes: dict[str, Any] = {}
        self.error_class: str | None = None

    def set_status(self, status: SpanStatusV2, error_class: str | None = None) -> None:
        self.status = status
        if error_class:
            self.error_class = error_class[:128]

    def add_attributes(self, attrs: Mapping[str, Any]) -> None:
        self.attributes.update(attrs)

    def finish(self) -> SpanSummaryV2:
        duration_ms = Decimal(str((time.perf_counter() - self._perf_start) * 1000.0))
        sanitized = self.redaction.sanitize_attributes(self.attributes)
        return SpanSummaryV2(
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            name=self.name,
            category=self.category,
            status=self.status,
            start_time=self.start_time,
            duration_ms=duration_ms,
            sanitized_attributes=sanitized,
            error_class=self.error_class,
        )


class TraceService:
    def __init__(
        self,
        trace_id: str,
        root_span_name: str = "HTTP_REQUEST",
        route_template: str = "/unknown",
        tenant_id: str | None = None,
    ) -> None:
        self.trace_id = trace_id
        self.route_template = route_template
        self.tenant_id = tenant_id
        self.started_at = datetime.now(timezone.utc)
        self._perf_start = time.perf_counter()
        self.root_span = SpanService(root_span_name, SpanCategoryV2.HTTP_REQUEST, trace_id=trace_id)
        self.spans: list[SpanService] = [self.root_span]

    def create_child_span(self, name: str, category: SpanCategoryV2) -> SpanService:
        parent_id = self.spans[-1].span_id if self.spans else self.root_span.span_id
        child = SpanService(name, category, trace_id=self.trace_id, parent_span_id=parent_id)
        self.spans.append(child)
        return child

    def finish_trace(self, overall_status: SpanStatusV2 = SpanStatusV2.OK) -> TraceSummaryV2:
        total_duration_ms = Decimal(str((time.perf_counter() - self._perf_start) * 1000.0))
        summaries = tuple(s.finish() for s in self.spans)
        return TraceSummaryV2(
            trace_id=self.trace_id,
            root_span_id=self.root_span.span_id,
            tenant_id=self.tenant_id,
            route_template=self.route_template,
            started_at=self.started_at,
            total_duration_ms=total_duration_ms,
            status=overall_status,
            span_count=len(summaries),
            spans=summaries,
        )
