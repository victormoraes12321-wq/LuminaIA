export type ValidationStatus =
  | 'VALID'
  | 'VALID_WITH_WARNINGS'
  | 'PARTIAL'
  | 'INVALID'
  | 'BLOCKED'
  | 'UNVERIFIABLE'
  | 'NOT_APPLICABLE'
  | 'SKIPPED_DEPENDENCY_FAILED';

export type ValidationSeverity = 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

export interface PublicProvenanceSummaryV2 {
  contract_version: string;
  metric_names: string[];
  period_description?: string;
  applied_filters: string[];
  data_source_description: string;
  source_last_updated?: string;
  validation_status: ValidationStatus;
  warnings: string[];
  truncated: boolean;
  certification_checksum: string;
}

export interface ValidationIssueV2 {
  issue_id: string;
  stage: string;
  severity: ValidationSeverity;
  message: string;
  field_path?: string;
  validator_id: string;
}

export interface AnalyticalFactV2 {
  fact_id: string;
  fact_type: string;
  canonical_metric_id?: string;
  unit?: string;
  currency?: string;
  validation_status: ValidationStatus;
  checksum: string;
}

export interface AnalyticalClaimV2 {
  claim_id: string;
  claim_type: string;
  text: string;
  fact_references: string[];
  checksum: string;
}

export interface CertificationEnvelopeV2 {
  contract_version: string;
  certification_id: string;
  tenant_id: string;
  user_id: string;
  request_id: string;
  public_summary: PublicProvenanceSummaryV2;
  overall_status: ValidationStatus;
  warnings: string[];
  critical_issues: string[];
  policy_version: string;
  created_at: string;
  checksum: string;
}
