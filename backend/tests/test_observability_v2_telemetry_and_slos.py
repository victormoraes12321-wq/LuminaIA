"""Unit tests for operational telemetry, metric rollups, SLIs, and SLO evaluations."""
from __future__ import annotations

from decimal import Decimal
import pytest
from contracts.observability_v2 import OperationalEventTypeV2, SloStatusV2
from services.observability_v2.slo_service import SloEvaluationService
from services.observability_v2.telemetry_service import OperationalTelemetryService

pytestmark = pytest.mark.no_database


def test_telemetry_service_records_events_and_rollups():
    telemetry = OperationalTelemetryService()

    evt = telemetry.record_event(
        OperationalEventTypeV2.REQUEST_STARTED,
        trace_id="trc_123",
        span_id="spn_123",
        attributes={"method": "GET"},
    )
    assert evt is not None
    assert len(telemetry.get_events()) == 1

    pt1 = telemetry.record_metric("http_requests_total", 1, labels={"method": "GET", "status_code": "200"})
    pt2 = telemetry.record_metric("http_requests_total", 1, labels={"method": "GET", "status_code": "200"})
    assert pt1 is not None and pt2 is not None

    rollups = telemetry.compute_rollups()
    assert len(rollups) == 1
    assert rollups[0].metric_id == "http_requests_total"
    assert rollups[0].count == 2
    assert rollups[0].sum_value == Decimal("2")


def test_slo_evaluation_service():
    telemetry = OperationalTelemetryService()
    slo_service = SloEvaluationService(telemetry)

    # Initially no data -> INSUFFICIENT_DATA status
    evals = slo_service.evaluate_all_slos()
    assert len(evals) == 7
    req_slo = next(e for e in evals if e.slo_id == "slo_request_success")
    assert req_slo.status == SloStatusV2.INSUFFICIENT_DATA

    # Add 100 requests
    for _ in range(100):
        telemetry.record_metric("http_requests_total", 1, labels={"method": "POST", "status_code": "200"})

    req_slo_active = slo_service.evaluate_slo("slo_request_success")
    assert req_slo_active is not None
    assert req_slo_active.status == SloStatusV2.HEALTHY
    assert req_slo_active.current_percentage == Decimal("100.00")
