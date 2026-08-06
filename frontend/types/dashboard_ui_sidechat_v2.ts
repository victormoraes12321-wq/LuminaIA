import type {
  DashboardBlueprintV2,
  DashboardFilterTypeV2,
  DashboardLifecycleV2,
  DashboardPatchOperationV2,
  DashboardVisualPatchV2,
  DashboardWidgetV2,
} from './dashboard_blueprint_v2'
import type {
  DashboardCapabilityBackendV2,
  DashboardRecordV2,
  DashboardRevisionRecordV2,
  DashboardRuntimeProvenanceV2,
  DashboardWidgetRuntimeResultV2,
} from './dashboard_backend_v2'

export const DASHBOARD_UI_SIDECHAT_CONTRACT_VERSION = 'lumina.dashboard-ui-sidechat/1.0' as const

export type DashboardUiModeV2 =
  | 'LEGACY_ONLY'
  | 'V2_PREVIEW'
  | 'V2_READ'
  | 'V2_AUTHORING'
  | 'V2_SIDE_CHAT'

export interface DashboardRouteContextV2 {
  readonly mode: DashboardUiModeV2
  readonly dashboard_id?: string
  readonly screen: 'LIBRARY' | 'RUNTIME' | 'EDITOR' | 'HISTORY'
}

export type DashboardScreenStateV2 =
  | { readonly state: 'LOADING'; readonly message: string }
  | { readonly state: 'READY' }
  | { readonly state: 'EMPTY'; readonly message: string }
  | { readonly state: 'PARTIAL' | 'STALE' | 'BLOCKED' | 'UNAVAILABLE' | 'ARCHIVED' | 'UNPUBLISHED'; readonly message: string }
  | { readonly state: 'PERMISSION_DENIED' | 'NOT_FOUND'; readonly message: string }
  | { readonly state: 'ERROR'; readonly code: string; readonly message: string; readonly retryable: boolean }

export interface DashboardLibraryItemV2 {
  readonly dashboard: DashboardRecordV2
  readonly capabilities: readonly DashboardCapabilityBackendV2[]
  readonly owner_label: string
  readonly active_publication: boolean
  readonly latest_revision_id?: string
}

export type DashboardWidgetStateV2 =
  | 'LOADING' | 'READY' | 'EMPTY' | 'PARTIAL' | 'STALE'
  | 'TRUNCATED' | 'BLOCKED' | 'UNAVAILABLE' | 'INVALID_CONTRACT'

export interface DashboardWidgetViewModelV2 {
  readonly widget: DashboardWidgetV2
  readonly result?: DashboardWidgetRuntimeResultV2
  readonly state: DashboardWidgetStateV2
  readonly textual_fallback: string
}

export interface DashboardRuntimeViewModelV2 {
  readonly contract_version: typeof DASHBOARD_UI_SIDECHAT_CONTRACT_VERSION
  readonly dashboard: DashboardRecordV2
  readonly blueprint: DashboardBlueprintV2
  readonly revision: DashboardRevisionRecordV2
  readonly widgets: readonly DashboardWidgetViewModelV2[]
  readonly provenance?: DashboardRuntimeProvenanceV2
  readonly capabilities: readonly DashboardCapabilityBackendV2[]
}

export interface DashboardFilterStateV2 {
  readonly filter_id: string
  readonly filter_type: DashboardFilterTypeV2
  readonly blueprint_default: readonly (string | number | boolean)[]
  readonly effective_server: readonly (string | number | boolean)[]
  readonly local_draft: readonly (string | number | boolean)[]
  readonly submitted: readonly (string | number | boolean)[]
  readonly runtime_confirmed: readonly (string | number | boolean)[]
  readonly status: 'CLEAN' | 'DIRTY' | 'SUBMITTING' | 'APPLIED' | 'REJECTED'
}

export type DashboardInteractionStateV2 =
  | { readonly kind: 'IDLE' }
  | { readonly kind: 'CROSS_FILTER_PENDING'; readonly interaction_id: string; readonly source_widget_id: string }
  | { readonly kind: 'DRILLDOWN_PENDING'; readonly interaction_id: string; readonly breadcrumb: readonly string[] }
  | { readonly kind: 'APPLIED'; readonly interaction_id: string }
  | { readonly kind: 'FAILED'; readonly interaction_id: string; readonly message: string }

export interface DashboardRuntimeInteractionRequestV2 {
  readonly interaction_id: string
  readonly action: 'CROSS_FILTER' | 'DRILLDOWN'
  readonly source_widget_id: string
  readonly target_widget_id?: string
  readonly target_filter_id?: string
  readonly canonical_value?: string
  readonly breadcrumb_label?: string
}

export interface DashboardSelectionStateV2 {
  readonly selected_widget_id?: string
  readonly selected_dimension_id?: string
  readonly selected_canonical_value?: string
  readonly drilldown_breadcrumb: readonly string[]
}

export interface DashboardEditorStateV2 {
  readonly mode: 'VISUAL' | 'SEMANTIC'
  readonly base_blueprint: DashboardBlueprintV2
  readonly preview_blueprint: DashboardBlueprintV2
  readonly dirty: boolean
  readonly operations: readonly DashboardPatchOperationV2[]
  readonly undo_depth: number
  readonly validation: 'NOT_RUN' | 'STRUCTURALLY_VALID' | 'BACKEND_VALID' | 'INVALID'
}

export interface DashboardRevisionStateV2 {
  readonly base_revision_id: string
  readonly base_blueprint_checksum: string
  readonly semantic_checksum: string
  readonly visual_revision: number
  readonly dashboard_lock_version: number
  readonly revision_lock_version: number
}

export type DashboardLifecycleActionV2 =
  | { readonly action: 'SUBMIT_REVIEW'; readonly revision_id: string; readonly comment: string }
  | { readonly action: 'REQUEST_CHANGES' | 'APPROVE' | 'REJECT'; readonly revision_id: string; readonly comment: string }
  | { readonly action: 'PUBLISH'; readonly revision_id: string; readonly publication_version: string }
  | { readonly action: 'ROLLBACK'; readonly publication_id: string; readonly reason: string }
  | { readonly action: 'ARCHIVE'; readonly reason: string }

export type DashboardMutationStateV2 =
  | { readonly status: 'IDLE' }
  | { readonly status: 'PENDING'; readonly idempotency_key: string }
  | { readonly status: 'SUCCEEDED'; readonly revision_id?: string }
  | { readonly status: 'CONFLICT'; readonly base_revision_id: string; readonly current_revision_id?: string }
  | { readonly status: 'FAILED'; readonly code: string; readonly message: string; readonly retryable: boolean }

export type DashboardSideChatModeV2 =
  | 'ASK' | 'EXPLAIN_WIDGET' | 'EXPLAIN_VARIANCE' | 'FILTER' | 'NAVIGATE' | 'VISUAL_EDIT'

export type DashboardSideChatStreamStatusV2 =
  | 'IDLE'
  | 'CONNECTING'
  | 'RECEIVING'
  | 'COMPLETE'
  | 'CANCELLED'
  | 'FAILED'
  | 'RETRYABLE'
  | 'ACTION_PENDING'
  | 'ACTION_CONFIRMED'

export interface DashboardSideChatSessionV2 {
  readonly session_id: string
  readonly context_version: number
  readonly mode: DashboardSideChatModeV2
  readonly messages: readonly DashboardSideChatMessageV2[]
}

export type DashboardSideChatMessageV2 =
  | { readonly message_id: string; readonly role: 'USER'; readonly content: string; readonly created_at: string }
  | { readonly message_id: string; readonly role: 'ASSISTANT'; readonly content: string; readonly created_at: string; readonly action?: DashboardSideChatActionV2 }
  | { readonly message_id: string; readonly role: 'SYSTEM'; readonly content: string; readonly created_at: string }

export interface DashboardSideChatContextV2 {
  readonly contract_version: typeof DASHBOARD_UI_SIDECHAT_CONTRACT_VERSION
  readonly dashboard_id: string
  readonly publication_id?: string
  readonly revision_id: string
  readonly blueprint_semantic_checksum: string
  readonly visible_widget_ids: readonly string[]
  readonly selected_widget_id?: string
  readonly binding_ids: readonly string[]
  readonly metric_ids: readonly string[]
  readonly dimension_ids: readonly string[]
  readonly effective_period?: string
  readonly filters: readonly { readonly filter_id: string; readonly values: readonly (string | number | boolean)[] }[]
  readonly selection?: { readonly dimension_id: string; readonly canonical_value: string }
  readonly public_provenance_references: readonly string[]
  readonly certification_references: readonly string[]
  readonly conversation_session_id: string
  readonly context_version: number
}

export interface DashboardVisualUpdateActionV2 {
  readonly action_type: 'VISUAL_PATCH_PROPOSAL' | 'VISUAL_PATCH_APPLY'
  readonly dashboard_id: string
  readonly revision_id: string
  readonly semantic_checksum: string
  readonly operations: readonly DashboardPatchOperationV2[]
  readonly summary: string
}

export interface DashboardFilterActionV2 {
  readonly action_type: 'APPLY_FILTER'
  readonly filter_id: string
  readonly values: readonly (string | number | boolean)[]
}

export interface DashboardFocusWidgetActionV2 {
  readonly action_type: 'FOCUS_WIDGET'
  readonly widget_id: string
}

export interface DashboardOpenProvenanceActionV2 {
  readonly action_type: 'OPEN_PROVENANCE'
  readonly widget_id?: string
}

export interface DashboardExplainWidgetActionV2 {
  readonly action_type: 'EXPLAIN_WIDGET'
  readonly widget_id: string
}

export type DashboardSideChatActionV2 =
  | { readonly action_type: 'NO_ACTION' }
  | DashboardFocusWidgetActionV2
  | DashboardOpenProvenanceActionV2
  | DashboardFilterActionV2
  | { readonly action_type: 'RESET_FILTERS' }
  | { readonly action_type: 'DRILLDOWN'; readonly interaction_id: string; readonly source_widget_id: string; readonly canonical_value: string }
  | DashboardVisualUpdateActionV2
  | { readonly action_type: 'BLOCKED'; readonly code: string; readonly message: string }

export type DashboardVisualInterceptorOutcomeV2 =
  | 'UI_MODIFIED' | 'FULL_RENDERING_REQUIRED' | 'NO_OP'
  | 'BLOCKED' | 'CONFLICT' | 'INVALID_ACTION'

export interface DashboardSideChatActionResultV2 {
  readonly outcome: DashboardVisualInterceptorOutcomeV2
  readonly message: string
  readonly preview_patch?: DashboardVisualPatchV2
  readonly revision_id?: string
}

export interface DashboardSideChatErrorV2 {
  readonly code: 'CANCELLED' | 'STALE_RESPONSE' | 'INVALID_ACTION' | 'PERMISSION_DENIED' | 'CONFLICT' | 'UNAVAILABLE'
  readonly message: string
  readonly retryable: boolean
}

export type DashboardTelemetryEventV2 =
  | { readonly event: 'DASHBOARD_UI_OPENED' | 'DASHBOARD_UI_CLOSED'; readonly dashboard_id: string; readonly mode: DashboardUiModeV2 }
  | { readonly event: 'DASHBOARD_WIDGET_RENDERED' | 'DASHBOARD_WIDGET_FAILED'; readonly dashboard_id: string; readonly widget_type: DashboardWidgetV2['widget_type'] }
  | { readonly event: 'DASHBOARD_SIDE_CHAT_UI_MODIFIED'; readonly dashboard_id: string; readonly operation_count: number }
  | { readonly event: 'DASHBOARD_SIDE_CHAT_BLOCKED' | 'DASHBOARD_SIDE_CHAT_CANCELLED'; readonly dashboard_id: string; readonly reason_code: string }
  | { readonly event: 'DASHBOARD_MUTATION_CONFLICT'; readonly dashboard_id: string; readonly lifecycle: DashboardLifecycleV2 }
