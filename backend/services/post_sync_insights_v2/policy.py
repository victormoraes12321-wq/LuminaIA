"""Policy engine and default policy provider for post-sync insights v1.0."""
from __future__ import annotations

import hashlib
from decimal import Decimal

from contracts.post_sync_insights_v2 import (
    POST_SYNC_INSIGHTS_CONTRACT_VERSION,
    PostSyncInsightBaselinePolicyV2,
    PostSyncInsightBaselineTypeV2,
    PostSyncInsightPolicyV2,
    PostSyncInsightPriorityPolicyV2,
    PostSyncInsightSeverityV2,
    PostSyncInsightSuppressionPolicyV2,
    PostSyncInsightThresholdPolicyV2,
)


def get_default_post_sync_policy(tenant_id: str) -> PostSyncInsightPolicyV2:
    policy_id = f"policy-{tenant_id[:8]}-default"
    baseline = PostSyncInsightBaselinePolicyV2(
        baseline_type=PostSyncInsightBaselineTypeV2.PREVIOUS_SUCCESSFUL_SYNC,
        lookback_window_days=30,
        minimum_observations=5,
        allow_zero_baseline_percentage=False,
    )
    thresholds = (
        PostSyncInsightThresholdPolicyV2(
            metric_key="desconto_total",
            operator="GT",
            target_value=Decimal("50000.00"),
            high_threshold=Decimal("50000.00"),
            unit="BRL",
        ),
    )
    suppression = PostSyncInsightSuppressionPolicyV2(
        suppression_window_hours=24,
        max_duplicate_occurrences=1,
        suppress_on_reconciliation_error=True,
        suppress_on_partial_sync=True,
    )
    priority = PostSyncInsightPriorityPolicyV2(
        max_insights_per_run=5,
        min_severity_to_publish=PostSyncInsightSeverityV2.LOW,
        prioritize_target_breaches=True,
    )
    detectors = (
        "MetricChangeDetector",
        "TargetAttainmentDetector",
        "ThresholdBreachDetector",
        "RankingMovementDetector",
        "RobustAnomalyDetector",
        "FreshnessDegradationDetector",
        "CompletenessDegradationDetector",
        "ReconciliationVarianceDetector",
        "SourceVolumeChangeDetector",
        "NewDataAvailableDetector",
    )
    raw_sig = f"{tenant_id}:default_v1:1.0.0"
    checksum = hashlib.sha256(raw_sig.encode()).hexdigest()

    return PostSyncInsightPolicyV2(
        policy_id=policy_id,
        policy_version="1.0.0",
        contract_version=POST_SYNC_INSIGHTS_CONTRACT_VERSION,
        tenant_id=tenant_id,
        enabled=True,
        enabled_detectors=detectors,
        baseline_policy=baseline,
        threshold_policies=thresholds,
        suppression_policy=suppression,
        priority_policy=priority,
        checksum=checksum,
    )
