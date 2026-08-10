"""Unit tests for Observability V2 strict contracts and Pydantic v2 validation."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from pydantic import ValidationError

from contracts.observability_v2 import (
    EvaluationOutcomeV2,
    EvaluationSuiteKindV2,
    FeatureModeV2,
    ObservabilityContextV2,
    OperationalEventV2,
    OperationalEventTypeV2,
    OperationalMetricPointV2,
    RedactionPolicyV2,
    SloStatusV2,
    SpanCategoryV2,
    SpanStatusV2,
    SpanSummaryV2,
    TelemetryClassificationV2,
)

pytestmark = pytest.mark.no_database


def test_observability_context_strict_validation():
    now = datetime.now(timezone.utc)
    ctx = ObservabilityContextV2(
        request_id="req_001",
        trace_id="trc_001",
        root_span_id="spn_001",
        route_template="/api/v1/query",
        method="POST",
        started_at=now,
    )
    assert ctx.request_id == "req_001"
    assert ctx.contract_version == "lumina.observability-metrics-evaluations/1.0"

    with pytest.raises(ValidationError):
        ObservabilityContextV2(
            request_id="req_001",
            trace_id="trc_001",
            root_span_id="spn_001",
            route_template="/api/v1/query",
            method="POST",
            started_at=now,
            extra_field="forbidden",
        )


def test_operational_event_enums():
    evt = OperationalEventV2(
        event_id="evt_001",
        event_type=OperationalEventTypeV2.REQUEST_STARTED,
        classification=TelemetryClassificationV2.PUBLIC_OPERATIONAL,
        trace_id="trc_001",
        span_id="spn_001",
        timestamp=datetime.now(timezone.utc),
        service="backend",
        attributes=(("route", "/health"),),
    )
    assert evt.event_type == OperationalEventTypeV2.REQUEST_STARTED
    assert evt.attributes == (("route", "/health"),)


def test_span_summary_strict():
    span = SpanSummaryV2(
        span_id="spn_001",
        name="QUERY_EXECUTION",
        category=SpanCategoryV2.QUERY_EXECUTION,
        status=SpanStatusV2.OK,
        start_time=datetime.now(timezone.utc),
        duration_ms=Decimal("12.50"),
    )
    assert span.status == SpanStatusV2.OK
    assert span.duration_ms == Decimal("12.50")
