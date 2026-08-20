import type { DashboardBlueprintV2, DashboardSemanticPatchV2, DashboardVisualPatchV2 } from './dashboard_blueprint_v2'

export type DashboardAiAssistanceModeV2 = 'LEGACY_ONLY' | 'SHADOW_ANALYZE' | 'AI_PROPOSAL_PREVIEW' | 'AI_DRAFT_CREATE' | 'AI_ASSISTED_EDIT'
export type DashboardAiOperationV2 = 'CREATE_DASHBOARD' | 'PROPOSE_VISUAL_CHANGE' | 'PROPOSE_SEMANTIC_CHANGE' | 'REVISE_PROPOSAL' | 'EXPLAIN_PROPOSAL' | 'CANCEL_PROPOSAL'
export type DashboardAiProposalStatusV2 = 'RECEIVED' | 'ANALYZING' | 'NEEDS_CLARIFICATION' | 'RESOLVING' | 'SYNTHESIZING' | 'VALIDATING' | 'READY_FOR_REVIEW' | 'REJECTED' | 'ACCEPTED' | 'APPLYING' | 'APPLIED' | 'BLOCKED' | 'FAILED' | 'CANCELLED' | 'SUPERSEDED' | 'EXPIRED'

export interface DashboardAiClarificationOptionV2 {
  readonly option_id: string
  readonly label: string
  readonly description: string
  readonly canonical_reference?: string
}

export interface DashboardAiClarificationQuestionV2 {
  readonly question_id: string
  readonly kind: 'OBJECTIVE' | 'METRIC' | 'DIMENSION' | 'PERIOD' | 'DATASET' | 'FILTER' | 'TOP_N'
  readonly prompt: string
  readonly options: readonly DashboardAiClarificationOptionV2[]
  readonly allow_multiple: boolean
}

export interface DashboardAiEvidenceV2 {
  readonly evidence_id: string
  readonly evidence_type: 'METRIC_REGISTRY' | 'KNOWLEDGE' | 'SEMANTIC_RETRIEVAL' | 'TEMPORAL' | 'CATALOG' | 'VALIDATION'
  readonly canonical_reference: string
  readonly public_label: string
  readonly authority_version: string
  readonly checksum: string
}

export interface DashboardAiWarningV2 { readonly code: string; readonly message: string }
export interface DashboardAiRiskV2 { readonly code: string; readonly severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'BLOCKING'; readonly message: string }
export interface DashboardAiRationaleV2 { readonly summary: string; readonly decisions: readonly string[]; readonly omitted_details_notice: string }

export interface DashboardAiDesignSpecV2 {
  readonly design_spec_id: string
  readonly title: string
  readonly description: string
  readonly template_id: string
  readonly metric_ids: readonly string[]
  readonly dimension_ids: readonly string[]
  readonly canonical_period_id: string
  readonly widgets: readonly { readonly widget_key: string; readonly purpose: string; readonly widget_type: string; readonly metric_ids: readonly string[]; readonly dimension_ids: readonly string[]; readonly top_n?: number }[]
  readonly resolution_checksum: string
}

export interface DashboardAiProposalVersionV2 {
  readonly proposal_id: string
  readonly version: number
  readonly status: DashboardAiProposalStatusV2
  readonly blueprint_proposal?: { readonly design_spec: DashboardAiDesignSpecV2; readonly blueprint: DashboardBlueprintV2; readonly blueprint_checksum: string; readonly semantic_checksum: string; readonly visual_checksum: string }
  readonly semantic_proposal?: { readonly patch: DashboardSemanticPatchV2; readonly patch_checksum: string }
  readonly visual_proposal?: { readonly objective: string; readonly patch: DashboardVisualPatchV2; readonly patch_checksum: string }
  readonly rationale: DashboardAiRationaleV2
  readonly evidence: readonly DashboardAiEvidenceV2[]
  readonly warnings: readonly DashboardAiWarningV2[]
  readonly risks: readonly DashboardAiRiskV2[]
  readonly content_checksum: string
  readonly created_at: string
}

export interface DashboardAiProposalV2 {
  readonly contract_version: 'lumina.dashboard-ai-assistance/1.0'
  readonly proposal_id: string
  readonly operation: DashboardAiOperationV2
  readonly origin: 'CREATION_WIZARD' | 'DASHBOARD_EDITOR' | 'SIDE_CHAT' | 'API'
  readonly status: DashboardAiProposalStatusV2
  readonly current_version: number
  readonly lock_version: number
  readonly latest?: DashboardAiProposalVersionV2
  readonly clarification?: { readonly proposal_id: string; readonly proposal_version: number; readonly questions: readonly DashboardAiClarificationQuestionV2[]; readonly expires_at: string; readonly lock_version: number }
  readonly target_dashboard_id?: string
  readonly target_revision_id?: string
  readonly applied_dashboard_id?: string
  readonly applied_revision_id?: string
  readonly created_at: string
  readonly updated_at: string
}

export interface DashboardAiAssistanceRequestV2 {
  readonly operation: DashboardAiOperationV2
  readonly origin: 'CREATION_WIZARD' | 'DASHBOARD_EDITOR' | 'SIDE_CHAT' | 'API'
  readonly instruction: string
  readonly context: { readonly session_id?: string; readonly target_dashboard_id?: string; readonly target_revision_id?: string; readonly locale: 'pt-BR'; readonly timezone: string; readonly expected_lock_version?: number }
  readonly client_request_id: string
}

export interface DashboardAiApplyResultV2 {
  readonly proposal_id: string
  readonly proposal_version: number
  readonly status: 'APPLIED'
  readonly dashboard_id: string
  readonly revision_id: string
  readonly replayed: boolean
}
