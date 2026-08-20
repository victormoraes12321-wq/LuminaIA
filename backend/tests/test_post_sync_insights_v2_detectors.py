"""Unit tests for the 10 deterministic post-sync insight detectors.

These tests are purely in-process and do not require a database connection.
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from contracts.post_sync_insights_v2 import (
    PostSyncInsightRunRequestV2,
    PostSyncInsightTypeV2,
)
from services.post_sync_insights_v2.policy import get_default_post_sync_policy
from services.post_sync_insights_v2 import detector_registry


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
@pytest.mark.asyncio
async def test_metric_change_detector_increase(run_request, default_policy):
    det = detector_registry.get_detector("MetricChangeDetector")
    assert det is not None
    ctx = {"current_value": "400.00", "baseline_value": "300.00"}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.METRIC_INCREASE
    assert cands[0].evidence.comparison.formatted_percentage == "+33.33%"


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_metric_change_detector_zero_baseline(run_request, default_policy):
    det = detector_registry.get_detector("MetricChangeDetector")
    ctx = {"current_value": "400.00", "baseline_value": "0.00"}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.INSUFFICIENT_BASELINE


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_target_attainment_detector_reached(run_request, default_policy):
    det = detector_registry.get_detector("TargetAttainmentDetector")
    ctx = {"target_value": "100000.00", "actual_value": "105000.00"}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.TARGET_REACHED


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_target_attainment_detector_missed(run_request, default_policy):
    det = detector_registry.get_detector("TargetAttainmentDetector")
    ctx = {"target_value": "100000.00", "actual_value": "85000.00"}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.TARGET_MISSED


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_threshold_breach_detector_high(run_request, default_policy):
    det = detector_registry.get_detector("ThresholdBreachDetector")
    ctx = {"threshold_value": "50000.00", "actual_value": "65000.00", "is_high": True}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.THRESHOLD_BREACH_HIGH


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_threshold_breach_detector_low(run_request, default_policy):
    det = detector_registry.get_detector("ThresholdBreachDetector")
    ctx = {"threshold_value": "50000.00", "actual_value": "30000.00", "is_high": False}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.THRESHOLD_BREACH_LOW


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_ranking_movement_detector(run_request, default_policy):
    det = detector_registry.get_detector("RankingMovementDetector")
    ctx = {"entity_name": "Produto A", "old_rank": 5, "new_rank": 2}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.RANKING_MOVE_UP


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_ranking_movement_detector_down(run_request, default_policy):
    det = detector_registry.get_detector("RankingMovementDetector")
    ctx = {"entity_name": "Produto B", "old_rank": 2, "new_rank": 5}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.RANKING_MOVE_DOWN


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_robust_anomaly_detector_insufficient_sample(run_request, default_policy):
    det = detector_registry.get_detector("RobustAnomalyDetector")
    ctx = {"observations": [100, 102], "current_value": "500.00"}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.INSUFFICIENT_BASELINE


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_robust_anomaly_detector_mad_zero(run_request, default_policy):
    det = detector_registry.get_detector("RobustAnomalyDetector")
    # MAD = 0 when all observations are identical
    ctx = {"observations": [100, 100, 100, 100, 100, 100], "current_value": "500.00"}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.INSUFFICIENT_BASELINE


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_robust_anomaly_detector_sufficient_sample(run_request, default_policy):
    det = detector_registry.get_detector("RobustAnomalyDetector")
    # Current value far from median → anomaly
    ctx = {"observations": [100, 102, 98, 101, 105, 99], "current_value": "500.00"}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.ANOMALY_HIGH


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_freshness_degradation_detector(run_request, default_policy):
    det = detector_registry.get_detector("FreshnessDegradationDetector")
    ctx = {"delay_hours": 36}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.FRESHNESS_DEGRADED


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_freshness_degradation_detector_no_issue(run_request, default_policy):
    det = detector_registry.get_detector("FreshnessDegradationDetector")
    ctx = {"delay_hours": 12}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 0


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_reconciliation_variance_detector(run_request, default_policy):
    det = detector_registry.get_detector("ReconciliationVarianceDetector")
    ctx = {"variance_amount": "1500.00"}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.RECONCILIATION_VARIANCE
    # Evidence must reference reconciliation — not Oracle
    assert cands[0].evidence.reconciliation_verified is False


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_source_volume_change_detector(run_request, default_policy):
    det = detector_registry.get_detector("SourceVolumeChangeDetector")
    ctx = {"old_rows": 10000, "new_rows": 15000}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.SOURCE_VOLUME_CHANGE


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_source_volume_change_no_trigger_small(run_request, default_policy):
    det = detector_registry.get_detector("SourceVolumeChangeDetector")
    ctx = {"old_rows": 10000, "new_rows": 10500}  # 5% change, below 20% threshold
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 0


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_new_data_available_detector(run_request, default_policy):
    det = detector_registry.get_detector("NewDataAvailableDetector")
    ctx = {"new_data_certified": True}
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    assert cands[0].insight_type == PostSyncInsightTypeV2.NEW_DATA_AVAILABLE


@pytest.mark.no_database
def test_detector_registry_has_all_10():
    dets = detector_registry.list_detectors()
    assert len(dets) == 10
    detector_ids = {d.detector_id for d in dets}
    expected_ids = {
        "MetricChangeDetector", "TargetAttainmentDetector", "ThresholdBreachDetector",
        "RankingMovementDetector", "RobustAnomalyDetector", "FreshnessDegradationDetector",
        "CompletenessDegradationDetector", "ReconciliationVarianceDetector",
        "SourceVolumeChangeDetector", "NewDataAvailableDetector",
    }
    assert detector_ids == expected_ids


@pytest.mark.no_database
def test_all_detectors_deterministic():
    for det in detector_registry.list_detectors():
        assert det.is_deterministic is True


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_metric_increase_june_july_scenario(run_request, default_policy):
    """Scenario 7: Faturamento junho=300 julho=400 → delta=100 pct=33.33%"""
    det = detector_registry.get_detector("MetricChangeDetector")
    ctx = {
        "current_value": "400.00",
        "baseline_value": "300.00",
        "current_period": "julho-2026",
        "baseline_period": "junho-2026",
        "metric_key": "faturamento_comercial",
        "metric_label": "Faturamento Comercial",
    }
    cands = await det.detect(run_request, default_policy, ctx)
    assert len(cands) == 1
    cand = cands[0]
    assert cand.insight_type == PostSyncInsightTypeV2.METRIC_INCREASE
    comp = cand.evidence.comparison
    assert comp.absolute_delta == Decimal("100.00")
    # 33.33...% — check via formatted string
    assert "33.33" in (comp.formatted_percentage or "")


@pytest.mark.no_database
def test_no_causal_claim_in_summary(run_request, default_policy):
    """Insight summaries must not use causal language without evidence."""
    for det in detector_registry.list_detectors():
        det_id = det.detector_id

    # Check MetricChangeDetector summary doesn't use causal language
    import asyncio
    async def _check():
        det = detector_registry.get_detector("MetricChangeDetector")
        ctx = {"current_value": "400.00", "baseline_value": "300.00"}
        cands = await det.detect(run_request, default_policy, ctx)
        for cand in cands:
            for forbidden in ("porque", "causado por", "devido a", "provavelmente"):
                assert forbidden not in cand.summary.headline.lower(), \
                    f"Causal claim detected in headline: {cand.summary.headline}"

    asyncio.get_event_loop().run_until_complete(_check())
