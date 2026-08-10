export type FeatureModeV2 =
  | 'LEGACY_ONLY'
  | 'SHADOW_OBSERVE'
  | 'V2_OBSERVABILITY_READ'
  | 'V2_EVALUATIONS'

export type TelemetryClassificationV2 =
  | 'PUBLIC_OPERATIONAL'
  | 'TENANT_OPERATIONAL'
  | 'INTERNAL_OPERATIONAL'
  | 'RESTRICTED_OPERATIONAL'
  | 'PERSONAL_DATA'
  | 'SECRET'
  | 'FORBIDDEN'

export type SloStatusV2 = 'HEALTHY' | 'AT_RISK' | 'EXHAUSTED' | 'INSUFFICIENT_DATA'

export type EvaluationOutcomeV2 = 'PASS' | 'FAIL' | 'BLOCKED' | 'ERROR'

export type EvaluationSuiteKindV2 =
  | 'TEMPORAL_NORMALIZATION'
  | 'COMPARISON_PLANNER'
  | 'COMPARISON_EXECUTOR'
  | 'CONTEXT_RESOLUTION'
  | 'ENTERPRISE_KNOWLEDGE'
  | 'SEMANTIC_RETRIEVAL'
  | 'AI_TOOL_REGISTRY'
  | 'SAFE_ANALYTICAL_POSTGRESQL'
  | 'AI_ORCHESTRATION'
  | 'VALIDATION_PROVENANCE'
  | 'SMART_CACHE'
  | 'DASHBOARD_BLUEPRINT'
  | 'DASHBOARD_BACKEND'
  | 'DASHBOARD_UI'
  | 'DASHBOARD_AI'
  | 'POST_SYNC_INSIGHTS'
  | 'TENANT_ISOLATION'
  | 'SECURITY'
  | 'REPRODUCIBILITY'

export type RegressionTypeV2 =
  | 'NEW_FAIL'
  | 'PASS_TO_FAIL'
  | 'SECURITY_INVARIANT_VIOLATION'
  | 'TENANT_LEAKAGE'
  | 'REPRODUCIBILITY_DIVERGENCE'
  | 'SCHEMA_DIVERGENCE'
  | 'UNSAFE_ACTION_ACCEPTED'
  | 'CANONICAL_RESOLUTION_DEGRADATION'
  | 'NEW_XFAIL_SKIP_MARKER'
  | 'UNEXPECTED_OPENAPI_CHANGE'

export interface ObservabilityHealthV2 {
  status: string
  uptime_seconds: string | number
  events_recorded: number
  dropped_telemetry_count: number
}

export interface ObservabilityReadinessV2 {
  ready: boolean
  mode: FeatureModeV2
  database_allowed: boolean
  registries_loaded: boolean
  reasons: string[]
}

export interface OperationalMetricDefinitionV2 {
  metric_id: string
  version: string
  metric_type: string
  description: string
  unit: string
  allowed_labels: string[]
  max_cardinality: number
  sli_association?: string | null
}

export interface OperationalMetricRollupV2 {
  metric_id: string
  window_start: string
  window_end: string
  count: number
  sum_value: string
  min_value: string
  max_value: string
  avg_value: string
  labels: [string, string][]
}

export interface ErrorBudgetV2 {
  slo_id: string
  total_events: number
  good_events: number
  bad_events: number
  target_percentage: string
  consumed_budget_percentage: string
  remaining_budget_percentage: string
  status: SloStatusV2
}

export interface SloEvaluationV2 {
  evaluation_id: string
  slo_id: string
  evaluated_at: string
  current_percentage: string
  target_percentage: string
  error_budget: ErrorBudgetV2
  status: SloStatusV2
}

export interface EvaluationSuiteV2 {
  suite_id: string
  kind: EvaluationSuiteKindV2
  title: string
  description: string
  case_count: number
  deterministic_only: boolean
}

export interface EvaluationEvidenceV2 {
  evidence_id: string
  case_id: string
  executed_at: string
  duration_ms: string
  sanitized_output_digest: string
  logs_digest: string
  checksum: string
}

export interface EvaluationResultV2 {
  result_id: string
  case_id: string
  suite: EvaluationSuiteKindV2
  outcome: EvaluationOutcomeV2
  duration_ms: string
  evidence: EvaluationEvidenceV2
  failure_reasons: string[]
  checksum: string
}

export interface EvaluationRegressionV2 {
  regression_id: string
  case_id: string
  suite: EvaluationSuiteKindV2
  regression_type: RegressionTypeV2
  description: string
  detected_at: string
  baseline_checksum: string
  current_checksum: string
}

export interface EvaluationRunV2 {
  run_id: string
  suite: EvaluationSuiteKindV2
  executed_at: string
  total_cases: number
  passed_cases: number
  failed_cases: number
  blocked_cases: number
  error_cases: number
  duration_ms: string
  results: EvaluationResultV2[]
  regressions: EvaluationRegressionV2[]
  checksum: string
}

export interface ObservabilitySummaryV2 {
  contract_version: string
  mode: FeatureModeV2
  health: ObservabilityHealthV2
  readiness: ObservabilityReadinessV2
  slo_count: number
  evaluation_runs_count: number
}
