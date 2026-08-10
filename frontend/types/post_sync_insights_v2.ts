export type PostSyncInsightTypeV2 =
  | "METRIC_INCREASE"
  | "METRIC_DECREASE"
  | "TARGET_REACHED"
  | "TARGET_MISSED"
  | "THRESHOLD_BREACH_HIGH"
  | "THRESHOLD_BREACH_LOW"
  | "RANKING_ENTRY"
  | "RANKING_EXIT"
  | "RANKING_MOVE_UP"
  | "RANKING_MOVE_DOWN"
  | "ANOMALY_HIGH"
  | "ANOMALY_LOW"
  | "FRESHNESS_DEGRADED"
  | "COMPLETENESS_DEGRADED"
  | "RECONCILIATION_VARIANCE"
  | "SOURCE_VOLUME_CHANGE"
  | "NEW_DATA_AVAILABLE"
  | "INSUFFICIENT_BASELINE"
  | "INSIGHT_RUN_BLOCKED";

export type PostSyncInsightCategoryV2 =
  | "BUSINESS_PERFORMANCE"
  | "FINANCIAL"
  | "SALES"
  | "RECEIVABLES"
  | "INVENTORY"
  | "DATA_QUALITY"
  | "FRESHNESS"
  | "RECONCILIATION"
  | "OPERATIONAL_METADATA";

export type PostSyncInsightSeverityV2 = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type PostSyncInsightLifecycleV2 =
  | "REQUESTED"
  | "PLANNING"
  | "EXECUTING"
  | "VALIDATING"
  | "DETECTED"
  | "CERTIFIED"
  | "PUBLISHED"
  | "ACKNOWLEDGED"
  | "DISMISSED"
  | "EXPIRED"
  | "BLOCKED"
  | "FAILED"
  | "CANCELLED"
  | "SUPERSEDED";

export interface PostSyncInsightListItemV2 {
  insight_id: string;
  insight_type: PostSyncInsightTypeV2;
  category: PostSyncInsightCategoryV2;
  severity: PostSyncInsightSeverityV2;
  lifecycle: PostSyncInsightLifecycleV2;
  headline: string;
  metric_key: string;
  metric_label: string;
  formatted_delta: string;
  published_at: string;
  is_acknowledged: boolean;
  is_dismissed: boolean;
}

export interface PostSyncInsightFactV2 {
  fact_key: string;
  fact_label: string;
  numeric_value: string;
  formatted_value: string;
  unit: string;
  period_label: string;
}

export interface PostSyncInsightComparisonV2 {
  baseline_fact: PostSyncInsightFactV2;
  current_fact: PostSyncInsightFactV2;
  absolute_delta: string;
  percentage_delta?: string | null;
  formatted_delta: string;
  formatted_percentage?: string | null;
  direction: "UP" | "DOWN" | "FLAT" | "STABLE";
}

export interface PostSyncInsightEvidenceV2 {
  evidence_id: string;
  tenant_id: string;
  sync_run_id: string;
  source_id: string;
  watermark: string;
  metric_key: string;
  metric_label: string;
  formula: string;
  current_period: string;
  baseline_period: string;
  comparison: PostSyncInsightComparisonV2;
  facts: PostSyncInsightFactV2[];
  reconciliation_verified: boolean;
  checksum: string;
}

export interface PostSyncInsightV2 {
  insight_id: string;
  contract_version: "lumina.post-sync-insights/1.0";
  tenant_id: string;
  sync_run_id: string;
  insight_type: PostSyncInsightTypeV2;
  category: PostSyncInsightCategoryV2;
  severity: PostSyncInsightSeverityV2;
  lifecycle: PostSyncInsightLifecycleV2;
  summary: {
    headline: string;
    detail: string;
    template_key: string;
  };
  evidence: PostSyncInsightEvidenceV2;
  published_at: string;
  fingerprint: string;
}

export interface PostSyncInsightDetailV2 {
  insight: PostSyncInsightV2;
  user_acknowledgement?: {
    acknowledgement_id: string;
    acknowledged_at: string;
    note?: string;
  } | null;
  user_dismissal?: {
    dismissal_id: string;
    dismissed_at: string;
    reason: string;
  } | null;
}
