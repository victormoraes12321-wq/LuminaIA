"""Unit tests for fail-closed redaction service and metric cardinality guard."""
from __future__ import annotations

import pytest
from services.observability_v2.cardinality import OperationalMetricCardinalityGuard
from services.observability_v2.redaction import ObservabilityRedactionService

pytestmark = pytest.mark.no_database


def test_redaction_service_strips_secrets_and_sql():
    redaction = ObservabilityRedactionService()

    assert redaction.redact_string("Bearer sk-proj-123456789") == "[REDACTED]"
    assert redaction.redact_string("user@example.com") == "[REDACTED]"
    assert redaction.redact_string("SELECT * FROM users") == "[REDACTED]"

    data = {
        "authorization": "Bearer secret-token",
        "cookie": "session=123",
        "normal_key": "safe_value",
        "db_password": "super-secret-pass",
    }
    redacted = redaction.redact_dict(data)
    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["cookie"] == "[REDACTED]"
    assert redacted["db_password"] == "[REDACTED]"
    assert redacted["normal_key"] == "safe_value"


def test_cardinality_guard_drops_forbidden_keys():
    guard = OperationalMetricCardinalityGuard()

    labels = {
        "service": "backend",
        "user_id": "11111111-1111-4111-8111-111111111111",
        "request_id": "req_12345",
        "question": "quanto vendemos hoje?",
    }
    cleaned = guard.validate_and_normalize_labels(labels, allowed_keys=("service", "user_id"))

    # user_id, request_id, question are in FORBIDDEN_LABEL_KEYS so they are dropped
    assert cleaned == (("service", "backend"),)
    assert guard.dropped_count > 0


def test_cardinality_guard_clamps_long_or_uuid_values():
    guard = OperationalMetricCardinalityGuard()

    labels = {
        "status": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "method": "GET",
    }
    cleaned = guard.validate_and_normalize_labels(labels, allowed_keys=("status", "method"))
    assert cleaned == (("method", "GET"), ("status", "OTHER"))
