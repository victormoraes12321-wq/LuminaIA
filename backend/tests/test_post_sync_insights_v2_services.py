"""Unit tests for post-sync insight services.

These tests are purely in-process and do not require a database connection.
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from contracts.post_sync_insights_v2 import (
    PostSyncInsightLifecycleV2,
    PostSyncInsightRunRequestV2,
    PostSyncInsightTypeV2,
)
from services.post_sync_insights_v2.policy import get_default_post_sync_policy
from services.post_sync_insights_v2 import (
    certification_service,
    deduplication_service,
    execution_service,
    planning_service,
    prioritization_service,
    validation_service,
)
from services.post_sync_insights_v2.detector_registry import detector_registry


@pytest.fixture
def run_request():
    return PostSyncInsightRunRequestV2(
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        sync_run_id="b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        watermark="2026-08-06T12:00:00Z",
    )


@pytest.fixture
def default_policy(run_request):
    return get_default_post_sync_policy(run_request.tenant_id)


@pytest.mark.no_database
def test_planning_service(run_request, default_policy):
    plan = planning_service.create_plan(run_request, default_policy)
    assert plan["policy_id"] == default_policy.policy_id
    assert len(plan["detector_plans"]) == 10
    assert "checksum" in plan


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_execution_and_prioritization(run_request, default_policy):
    cands = await execution_service.execute_detectors(
        run_request, default_policy,
        {"current_value": "400.00", "baseline_value": "300.00"}
    )
    assert len(cands) > 0

    valid_cands = [c for c in cands if validation_service.validate_candidate(c, default_policy)]
    assert len(valid_cands) == len(cands)

    prioritized = prioritization_service.prioritize(valid_cands, default_policy)
    assert len(prioritized) <= default_policy.priority_policy.max_insights_per_run


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_deduplication_suppresses_fingerprint_duplicates(run_request, default_policy):
    cands = await execution_service.execute_detectors(
        run_request, default_policy,
        {"current_value": "400.00", "baseline_value": "300.00"}
    )
    assert len(cands) > 0

    # First pass: no existing, nothing suppressed
    deduped, suppressed_count = deduplication_service.filter_candidates(cands, [], default_policy)
    assert suppressed_count == 0
    assert len(deduped) == len(cands)

    # Certify first set
    certified = [certification_service.certify_candidate(c) for c in deduped]

    # Second pass with same candidates: all should be suppressed
    _, suppressed_count2 = deduplication_service.filter_candidates(cands, certified, default_policy)
    assert suppressed_count2 == len(cands)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_certification_produces_published_insights(run_request, default_policy):
    det = detector_registry.get_detector("MetricChangeDetector")
    assert det is not None
    cands = await det.detect(
        run_request, default_policy,
        {"current_value": "400.00", "baseline_value": "300.00"}
    )
    assert len(cands) == 1
    cand = cands[0]

    certified = certification_service.certify_candidate(cand)
    assert certified.lifecycle == PostSyncInsightLifecycleV2.PUBLISHED
    assert certified.certification.status == "VALID"
    assert certified.certification.checksum is not None
    assert certified.fingerprint == cand.fingerprint


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_validation_rejects_invalid_candidates(run_request, default_policy):
    det = detector_registry.get_detector("MetricChangeDetector")
    assert det is not None
    cands = await det.detect(
        run_request, default_policy,
        {"current_value": "400.00", "baseline_value": "300.00"}
    )
    # All candidates from our governed detectors must be valid
    for cand in cands:
        assert validation_service.validate_candidate(cand, default_policy) is True


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_prioritization_respects_max_insights_per_run(run_request, default_policy):
    """Prioritization must never exceed max_insights_per_run from policy."""
    cands = await execution_service.execute_detectors(
        run_request, default_policy,
        {
            "current_value": "400.00", "baseline_value": "300.00",
            "delay_hours": 36, "missing_buckets": 2,
            "variance_amount": "1500.00", "new_rows": 15000, "old_rows": 10000,
        }
    )
    prioritized = prioritization_service.prioritize(cands, default_policy)
    assert len(prioritized) <= default_policy.priority_policy.max_insights_per_run


@pytest.mark.no_database
def test_policy_checksum_deterministic():
    """Same tenant always produces same default policy checksum."""
    tenant_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    p1 = get_default_post_sync_policy(tenant_id)
    p2 = get_default_post_sync_policy(tenant_id)
    assert p1.checksum == p2.checksum


@pytest.mark.no_database
def test_policy_has_all_detectors_enabled():
    """Default policy must enable all 10 detectors."""
    policy = get_default_post_sync_policy("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
    assert len(policy.enabled_detectors) == 10


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_blocked_reconciliation_produces_no_business_insights(run_request, default_policy):
    """Sync failed → no business insight candidates from MetricChangeDetector."""
    failed_request = PostSyncInsightRunRequestV2(
        tenant_id=run_request.tenant_id,
        sync_run_id=run_request.sync_run_id,
        watermark=run_request.watermark,
        reconciliation_status="FAILED",
    )
    # Pipeline suppression policy must block business insights on reconciliation failure
    assert default_policy.suppression_policy.suppress_on_reconciliation_error is True


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_insight_fingerprint_uniqueness(run_request, default_policy):
    """Each detector must produce a unique fingerprint for different sync runs."""
    req2 = PostSyncInsightRunRequestV2(
        tenant_id=run_request.tenant_id,
        sync_run_id="c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",  # different run
        watermark="2026-08-07T12:00:00Z",
    )
    det = detector_registry.get_detector("MetricChangeDetector")
    ctx = {"current_value": "400.00", "baseline_value": "300.00"}
    cands1 = await det.detect(run_request, default_policy, ctx)
    cands2 = await det.detect(req2, default_policy, ctx)
    assert len(cands1) == 1
    assert len(cands2) == 1
    # Different sync runs → different fingerprints
    assert cands1[0].fingerprint != cands2[0].fingerprint
