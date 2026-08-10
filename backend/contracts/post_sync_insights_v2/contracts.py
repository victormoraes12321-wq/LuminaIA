"""Strict public contracts for certified post-sync insights v1.0."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

POST_SYNC_INSIGHTS_CONTRACT_VERSION = "lumina.post-sync-insights/1.0"
ID_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{2,127}$"
CHECKSUM_PATTERN = r"^[a-f0-9]{64}$"


class StrictPostSyncInsightModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class PostSyncInsightTypeV2(str, Enum):
    METRIC_INCREASE = "METRIC_INCREASE"
    METRIC_DECREASE = "METRIC_DECREASE"
    TARGET_REACHED = "TARGET_REACHED"
    TARGET_MISSED = "TARGET_MISSED"
    THRESHOLD_BREACH_HIGH = "THRESHOLD_BREACH_HIGH"
    THRESHOLD_BREACH_LOW = "THRESHOLD_BREACH_LOW"
    RANKING_ENTRY = "RANKING_ENTRY"
    RANKING_EXIT = "RANKING_EXIT"
    RANKING_MOVE_UP = "RANKING_MOVE_UP"
    RANKING_MOVE_DOWN = "RANKING_MOVE_DOWN"
    ANOMALY_HIGH = "ANOMALY_HIGH"
    ANOMALY_LOW = "ANOMALY_LOW"
    FRESHNESS_DEGRADED = "FRESHNESS_DEGRADED"
    COMPLETENESS_DEGRADED = "COMPLETENESS_DEGRADED"
    RECONCILIATION_VARIANCE = "RECONCILIATION_VARIANCE"
    SOURCE_VOLUME_CHANGE = "SOURCE_VOLUME_CHANGE"
    NEW_DATA_AVAILABLE = "NEW_DATA_AVAILABLE"
    INSUFFICIENT_BASELINE = "INSUFFICIENT_BASELINE"
    INSIGHT_RUN_BLOCKED = "INSIGHT_RUN_BLOCKED"


class PostSyncInsightCategoryV2(str, Enum):
    BUSINESS_PERFORMANCE = "BUSINESS_PERFORMANCE"
    FINANCIAL = "FINANCIAL"
    SALES = "SALES"
    RECEIVABLES = "RECEIVABLES"
    INVENTORY = "INVENTORY"
    DATA_QUALITY = "DATA_QUALITY"
    FRESHNESS = "FRESHNESS"
    RECONCILIATION = "RECONCILIATION"
    OPERATIONAL_METADATA = "OPERATIONAL_METADATA"


class PostSyncInsightSeverityV2(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PostSyncInsightLifecycleV2(str, Enum):
    REQUESTED = "REQUESTED"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    DETECTED = "DETECTED"
    CERTIFIED = "CERTIFIED"
    PUBLISHED = "PUBLISHED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class PostSyncInsightBaselineTypeV2(str, Enum):
    PREVIOUS_SUCCESSFUL_SYNC = "PREVIOUS_SUCCESSFUL_SYNC"
    PREVIOUS_CLOSED_PERIOD = "PREVIOUS_CLOSED_PERIOD"
    SAME_PERIOD_PREVIOUS_CYCLE = "SAME_PERIOD_PREVIOUS_CYCLE"
    ROLLING_BASELINE = "ROLLING_BASELINE"
    PUBLISHED_TARGET = "PUBLISHED_TARGET"
    PREVIOUS_RANKING_SNAPSHOT = "PREVIOUS_RANKING_SNAPSHOT"


class PostSyncInsightScopeV2(StrictPostSyncInsightModel):
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    sync_run_id: str = Field(..., pattern=ID_PATTERN)
    source_id: str = Field(default="VW_VENDAS_LM", pattern=ID_PATTERN)
    source_version: str = Field(default="1.0.0", pattern=r"^[a-zA-Z0-9._:-]{1,64}$")
    watermark: str = Field(..., description="Timestamp or version identifier of sync watermark")


class PostSyncInsightBaselinePolicyV2(StrictPostSyncInsightModel):
    baseline_type: PostSyncInsightBaselineTypeV2
    lookback_window_days: int = Field(default=30, ge=1, le=365)
    minimum_observations: int = Field(default=5, ge=1, le=100)
    allow_zero_baseline_percentage: bool = Field(default=False)


class PostSyncInsightThresholdPolicyV2(StrictPostSyncInsightModel):
    metric_key: str = Field(..., pattern=ID_PATTERN)
    operator: Literal["GT", "GTE", "LT", "LTE", "OUTSIDE_RANGE", "INSIDE_RANGE"]
    target_value: Decimal
    high_threshold: Decimal | None = None
    low_threshold: Decimal | None = None
    unit: str = Field(default="BRL", max_length=16)


class PostSyncInsightSuppressionPolicyV2(StrictPostSyncInsightModel):
    suppression_window_hours: int = Field(default=24, ge=1, le=720)
    max_duplicate_occurrences: int = Field(default=1, ge=1, le=10)
    suppress_on_reconciliation_error: bool = Field(default=True)
    suppress_on_partial_sync: bool = Field(default=True)


class PostSyncInsightPriorityPolicyV2(StrictPostSyncInsightModel):
    max_insights_per_run: int = Field(default=5, ge=1, le=20)
    min_severity_to_publish: PostSyncInsightSeverityV2 = Field(default=PostSyncInsightSeverityV2.LOW)
    prioritize_target_breaches: bool = Field(default=True)


class PostSyncInsightPolicyV2(StrictPostSyncInsightModel):
    policy_id: str = Field(..., pattern=ID_PATTERN)
    policy_version: str = Field(default="1.0.0", pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    contract_version: Literal["lumina.post-sync-insights/1.0"] = POST_SYNC_INSIGHTS_CONTRACT_VERSION
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    enabled: bool = Field(default=True)
    enabled_detectors: tuple[str, ...] = Field(default_factory=tuple)
    baseline_policy: PostSyncInsightBaselinePolicyV2
    threshold_policies: tuple[PostSyncInsightThresholdPolicyV2, ...] = Field(default_factory=tuple)
    suppression_policy: PostSyncInsightSuppressionPolicyV2
    priority_policy: PostSyncInsightPriorityPolicyV2
    checksum: str = Field(..., pattern=CHECKSUM_PATTERN)


class PostSyncInsightDetectorPlanV2(StrictPostSyncInsightModel):
    detector_id: str = Field(..., pattern=ID_PATTERN)
    detector_version: str = Field(default="1.0.0", pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    supported_types: tuple[PostSyncInsightTypeV2, ...]
    target_metric_keys: tuple[str, ...] = Field(default_factory=tuple)
    target_dimensions: tuple[str, ...] = Field(default_factory=tuple)
    estimated_query_count: int = Field(default=1, ge=0, le=10)


class PostSyncInsightMetricPlanV2(StrictPostSyncInsightModel):
    metric_key: str = Field(..., pattern=ID_PATTERN)
    formula: str = Field(..., max_length=255)
    unit: str = Field(default="BRL", max_length=16)
    grain: str = Field(default="periodo", max_length=64)


class PostSyncInsightDimensionPlanV2(StrictPostSyncInsightModel):
    dimension_key: str = Field(..., pattern=ID_PATTERN)
    top_n: int = Field(default=5, ge=1, le=50)


class PostSyncInsightEvidenceRequestV2(StrictPostSyncInsightModel):
    sync_run_id: str = Field(..., pattern=ID_PATTERN)
    source_watermark: str = Field(..., max_length=64)
    require_reconciliation_proof: bool = Field(default=True)


class PostSyncInsightRunRequestV2(StrictPostSyncInsightModel):
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    sync_run_id: str = Field(..., pattern=ID_PATTERN)
    source_id: str = Field(default="VW_VENDAS_LM", pattern=ID_PATTERN)
    source_version: str = Field(default="1.0.0", pattern=r"^[a-zA-Z0-9._:-]{1,64}$")
    watermark: str = Field(..., max_length=64)
    reconciliation_status: str = Field(default="SUCCESS", max_length=32)
    force_replay: bool = Field(default=False)
    policy_id: str | None = Field(default=None, pattern=ID_PATTERN)


class PostSyncInsightCandidateScoreV2(StrictPostSyncInsightModel):
    severity_score: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    magnitude_score: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    confidence_score: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    final_score: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))


class PostSyncInsightFactV2(StrictPostSyncInsightModel):
    fact_key: str = Field(..., pattern=ID_PATTERN)
    fact_label: str = Field(..., max_length=128)
    numeric_value: Decimal
    formatted_value: str = Field(..., max_length=64)
    unit: str = Field(default="BRL", max_length=16)
    period_label: str = Field(..., max_length=64)


class PostSyncInsightComparisonV2(StrictPostSyncInsightModel):
    baseline_fact: PostSyncInsightFactV2
    current_fact: PostSyncInsightFactV2
    absolute_delta: Decimal
    percentage_delta: Decimal | None = None
    formatted_delta: str = Field(..., max_length=64)
    formatted_percentage: str | None = Field(default=None, max_length=32)
    direction: Literal["UP", "DOWN", "FLAT", "STABLE"]


class PostSyncInsightEvidenceV2(StrictPostSyncInsightModel):
    evidence_id: str = Field(..., pattern=ID_PATTERN)
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    sync_run_id: str = Field(..., pattern=ID_PATTERN)
    source_id: str = Field(..., pattern=ID_PATTERN)
    watermark: str = Field(..., max_length=64)
    metric_key: str = Field(..., pattern=ID_PATTERN)
    metric_label: str = Field(..., max_length=128)
    formula: str = Field(..., max_length=255)
    current_period: str = Field(..., max_length=64)
    baseline_period: str = Field(..., max_length=64)
    comparison: PostSyncInsightComparisonV2
    facts: tuple[PostSyncInsightFactV2, ...] = Field(default_factory=tuple)
    reconciliation_verified: bool = Field(default=True)
    checksum: str = Field(..., pattern=CHECKSUM_PATTERN)


class PostSyncInsightProvenanceV2(StrictPostSyncInsightModel):
    service_name: str = Field(default="post_sync_insights_v2", max_length=64)
    contract_version: Literal["lumina.post-sync-insights/1.0"] = POST_SYNC_INSIGHTS_CONTRACT_VERSION
    policy_id: str = Field(..., pattern=ID_PATTERN)
    policy_version: str = Field(..., pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    detector_id: str = Field(..., pattern=ID_PATTERN)
    detector_version: str = Field(..., pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    executed_at: datetime


class PostSyncInsightCertificationV2(StrictPostSyncInsightModel):
    status: Literal["VALID", "INVALID", "BLOCKED", "SUPERSEDED"]
    certified_at: datetime
    checksum: str = Field(..., pattern=CHECKSUM_PATTERN)
    verifier: str = Field(default="ValidationProvenanceV2", max_length=64)


class PostSyncInsightWarningV2(StrictPostSyncInsightModel):
    code: str = Field(..., pattern=r"^[A-Z0-9_]{3,64}$")
    message: str = Field(..., max_length=255)


class PostSyncInsightPublicSummaryV2(StrictPostSyncInsightModel):
    headline: str = Field(..., max_length=255)
    detail: str = Field(..., max_length=1024)
    template_key: str = Field(..., pattern=ID_PATTERN)


class PostSyncInsightCandidateV2(StrictPostSyncInsightModel):
    candidate_id: str = Field(..., pattern=ID_PATTERN)
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    sync_run_id: str = Field(..., pattern=ID_PATTERN)
    insight_type: PostSyncInsightTypeV2
    category: PostSyncInsightCategoryV2
    severity: PostSyncInsightSeverityV2
    summary: PostSyncInsightPublicSummaryV2
    evidence: PostSyncInsightEvidenceV2
    provenance: PostSyncInsightProvenanceV2
    score: PostSyncInsightCandidateScoreV2
    fingerprint: str = Field(..., pattern=CHECKSUM_PATTERN)
    created_at: datetime


class PostSyncInsightV2(StrictPostSyncInsightModel):
    insight_id: str = Field(..., pattern=ID_PATTERN)
    contract_version: Literal["lumina.post-sync-insights/1.0"] = POST_SYNC_INSIGHTS_CONTRACT_VERSION
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    sync_run_id: str = Field(..., pattern=ID_PATTERN)
    insight_type: PostSyncInsightTypeV2
    category: PostSyncInsightCategoryV2
    severity: PostSyncInsightSeverityV2
    lifecycle: PostSyncInsightLifecycleV2
    summary: PostSyncInsightPublicSummaryV2
    evidence: PostSyncInsightEvidenceV2
    provenance: PostSyncInsightProvenanceV2
    certification: PostSyncInsightCertificationV2
    score: PostSyncInsightCandidateScoreV2
    warnings: tuple[PostSyncInsightWarningV2, ...] = Field(default_factory=tuple)
    published_at: datetime
    expires_at: datetime | None = None
    fingerprint: str = Field(..., pattern=CHECKSUM_PATTERN)


class PostSyncInsightAcknowledgementV2(StrictPostSyncInsightModel):
    acknowledgement_id: str = Field(..., pattern=ID_PATTERN)
    insight_id: str = Field(..., pattern=ID_PATTERN)
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    user_id: str = Field(..., pattern=ID_PATTERN)
    acknowledged_at: datetime
    note: str | None = Field(default=None, max_length=255)


class PostSyncInsightDismissalV2(StrictPostSyncInsightModel):
    dismissal_id: str = Field(..., pattern=ID_PATTERN)
    insight_id: str = Field(..., pattern=ID_PATTERN)
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    user_id: str = Field(..., pattern=ID_PATTERN)
    dismissed_at: datetime
    reason: Literal["NOT_RELEVANT", "ALREADY_KNOWN", "INACCURATE", "DUPLICATE", "OTHER"] = "NOT_RELEVANT"


class PostSyncInsightListRequestV2(StrictPostSyncInsightModel):
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    severity: PostSyncInsightSeverityV2 | None = None
    category: PostSyncInsightCategoryV2 | None = None
    lifecycle: PostSyncInsightLifecycleV2 | None = None
    metric_key: str | None = Field(default=None, pattern=ID_PATTERN)
    include_dismissed: bool = Field(default=False)
    include_acknowledged: bool = Field(default=True)
    cursor: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=20, ge=1, le=100)


class PostSyncInsightListItemV2(StrictPostSyncInsightModel):
    insight_id: str = Field(..., pattern=ID_PATTERN)
    insight_type: PostSyncInsightTypeV2
    category: PostSyncInsightCategoryV2
    severity: PostSyncInsightSeverityV2
    lifecycle: PostSyncInsightLifecycleV2
    headline: str = Field(..., max_length=255)
    metric_key: str = Field(..., pattern=ID_PATTERN)
    metric_label: str = Field(..., max_length=128)
    formatted_delta: str = Field(..., max_length=64)
    published_at: datetime
    is_acknowledged: bool = Field(default=False)
    is_dismissed: bool = Field(default=False)


class PostSyncInsightDetailV2(StrictPostSyncInsightModel):
    insight: PostSyncInsightV2
    user_acknowledgement: PostSyncInsightAcknowledgementV2 | None = None
    user_dismissal: PostSyncInsightDismissalV2 | None = None


class PostSyncInsightRunV2(StrictPostSyncInsightModel):
    run_id: str = Field(..., pattern=ID_PATTERN)
    contract_version: Literal["lumina.post-sync-insights/1.0"] = POST_SYNC_INSIGHTS_CONTRACT_VERSION
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    sync_run_id: str = Field(..., pattern=ID_PATTERN)
    policy_id: str = Field(..., pattern=ID_PATTERN)
    policy_version: str = Field(..., pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    status: PostSyncInsightLifecycleV2
    candidates_count: int = Field(default=0, ge=0)
    published_count: int = Field(default=0, ge=0)
    suppressed_count: int = Field(default=0, ge=0)
    started_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = Field(default=None, max_length=255)


class PostSyncInsightRunResultV2(StrictPostSyncInsightModel):
    run: PostSyncInsightRunV2
    published_insights: tuple[PostSyncInsightV2, ...] = Field(default_factory=tuple)
    warnings: tuple[PostSyncInsightWarningV2, ...] = Field(default_factory=tuple)


class PostSyncInsightTriggerV2(StrictPostSyncInsightModel):
    trigger_id: str = Field(..., pattern=ID_PATTERN)
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    sync_run_id: str = Field(..., pattern=ID_PATTERN)
    triggered_at: datetime
    status: Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]


class PostSyncInsightReplayRequestV2(StrictPostSyncInsightModel):
    tenant_id: str = Field(..., pattern=ID_PATTERN)
    run_id: str = Field(..., pattern=ID_PATTERN)
    reason: str = Field(..., max_length=255)


class PostSyncInsightEvaluationCaseV2(StrictPostSyncInsightModel):
    case_id: str = Field(..., pattern=ID_PATTERN)
    description: str = Field(..., max_length=255)
    input_run_request: PostSyncInsightRunRequestV2
    expected_insight_types: tuple[PostSyncInsightTypeV2, ...] = Field(default_factory=tuple)
    expected_min_insights: int = Field(default=0, ge=0)
    expected_max_insights: int = Field(default=5, ge=0)


class PostSyncInsightEvaluationResultV2(StrictPostSyncInsightModel):
    case_id: str = Field(..., pattern=ID_PATTERN)
    passed: bool
    actual_insights_count: int
    matched_types: tuple[PostSyncInsightTypeV2, ...] = Field(default_factory=tuple)
    missing_types: tuple[PostSyncInsightTypeV2, ...] = Field(default_factory=tuple)
    details: str = Field(..., max_length=512)
