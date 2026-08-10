"""Unit tests for post-sync insights v2 strict contracts.

These tests are purely in-process and do not require a database connection.
"""
from __future__ import annotations

from decimal import Decimal
import pytest
from pydantic import ValidationError

from contracts.post_sync_insights_v2 import (
    POST_SYNC_INSIGHTS_CONTRACT_VERSION,
    PostSyncInsightBaselinePolicyV2,
    PostSyncInsightBaselineTypeV2,
    PostSyncInsightCategoryV2,
    PostSyncInsightLifecycleV2,
    PostSyncInsightPolicyV2,
    PostSyncInsightPriorityPolicyV2,
    PostSyncInsightRunRequestV2,
    PostSyncInsightSeverityV2,
    PostSyncInsightSuppressionPolicyV2,
    PostSyncInsightThresholdPolicyV2,
    PostSyncInsightTypeV2,
)
from services.post_sync_insights_v2.policy import get_default_post_sync_policy


@pytest.mark.no_database
def test_contract_version_constant():
    assert POST_SYNC_INSIGHTS_CONTRACT_VERSION == "lumina.post-sync-insights/1.0"


@pytest.mark.no_database
def test_get_default_policy():
    tenant_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    policy = get_default_post_sync_policy(tenant_id)
    assert policy.tenant_id == tenant_id
    assert policy.enabled is True
    assert len(policy.enabled_detectors) == 10
    assert policy.checksum is not None


@pytest.mark.no_database
def test_strict_policy_validation():
    with pytest.raises(ValidationError):
        # extra field forbidden
        PostSyncInsightBaselinePolicyV2(
            baseline_type=PostSyncInsightBaselineTypeV2.PREVIOUS_SUCCESSFUL_SYNC,
            unknown_field=123,  # type: ignore
        )


@pytest.mark.no_database
def test_run_request_validation():
    req = PostSyncInsightRunRequestV2(
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        sync_run_id="b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        watermark="2026-08-06T12:00:00Z",
    )
    assert req.source_id == "VW_VENDAS_LM"
    assert req.reconciliation_status == "SUCCESS"


@pytest.mark.no_database
def test_insight_types_enum_complete():
    expected_types = {
        "METRIC_INCREASE", "METRIC_DECREASE", "TARGET_REACHED", "TARGET_MISSED",
        "THRESHOLD_BREACH_HIGH", "THRESHOLD_BREACH_LOW",
        "RANKING_ENTRY", "RANKING_EXIT", "RANKING_MOVE_UP", "RANKING_MOVE_DOWN",
        "ANOMALY_HIGH", "ANOMALY_LOW",
        "FRESHNESS_DEGRADED", "COMPLETENESS_DEGRADED", "RECONCILIATION_VARIANCE",
        "SOURCE_VOLUME_CHANGE", "NEW_DATA_AVAILABLE",
        "INSUFFICIENT_BASELINE", "INSIGHT_RUN_BLOCKED",
    }
    actual_types = {t.value for t in PostSyncInsightTypeV2}
    assert actual_types == expected_types


@pytest.mark.no_database
def test_severity_enum_complete():
    assert {s.value for s in PostSyncInsightSeverityV2} == {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


@pytest.mark.no_database
def test_lifecycle_states_complete():
    expected = {
        "REQUESTED", "PLANNING", "EXECUTING", "VALIDATING", "DETECTED",
        "CERTIFIED", "PUBLISHED", "ACKNOWLEDGED", "DISMISSED", "EXPIRED",
        "BLOCKED", "FAILED", "CANCELLED", "SUPERSEDED",
    }
    assert {s.value for s in PostSyncInsightLifecycleV2} == expected


@pytest.mark.no_database
def test_category_enum_complete():
    expected = {
        "BUSINESS_PERFORMANCE", "FINANCIAL", "SALES", "RECEIVABLES", "INVENTORY",
        "DATA_QUALITY", "FRESHNESS", "RECONCILIATION", "OPERATIONAL_METADATA",
    }
    assert {c.value for c in PostSyncInsightCategoryV2} == expected


@pytest.mark.no_database
def test_threshold_policy_operators():
    """Threshold policy accepts only governed operators."""
    tp = PostSyncInsightThresholdPolicyV2(
        metric_key="faturamento_comercial",
        operator="GT",
        target_value=Decimal("100000.00"),
        unit="BRL",
    )
    assert tp.operator == "GT"


@pytest.mark.no_database
def test_suppression_policy_defaults():
    sp = PostSyncInsightSuppressionPolicyV2()
    assert sp.suppress_on_reconciliation_error is True
    assert sp.suppress_on_partial_sync is True
    assert sp.suppression_window_hours == 24


@pytest.mark.no_database
def test_priority_policy_limits():
    pp = PostSyncInsightPriorityPolicyV2(max_insights_per_run=3)
    assert pp.max_insights_per_run == 3
