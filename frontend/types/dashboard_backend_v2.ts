/** Contract-only mirror of lumina.dashboard-backend/1.0. No runtime client. */
import type {
  DashboardBlueprintV2,
  DashboardLifecycleV2,
  DashboardOriginV2,
} from './dashboard_blueprint_v2';

export const DASHBOARD_BACKEND_CONTRACT_VERSION = 'lumina.dashboard-backend/1.0' as const;

export type DashboardOwnershipTypeV2 = 'USER' | 'TEAM' | 'TENANT' | 'SYSTEM_TEMPLATE';
export type DashboardCollaboratorRoleV2 =
  | 'VIEWER' | 'EDITOR_VISUAL' | 'EDITOR_SEMANTIC'
  | 'REVIEWER' | 'PUBLISHER' | 'ADMINISTRATOR';
export type DashboardCapabilityBackendV2 =
  | 'dashboard:create' | 'dashboard:view' | 'dashboard:list'
  | 'dashboard:edit_visual' | 'dashboard:edit_semantic'
  | 'dashboard:review' | 'dashboard:approve' | 'dashboard:publish'
  | 'dashboard:rollback' | 'dashboard:archive' | 'dashboard:clone'
  | 'dashboard:manage_collaborators' | 'dashboard:execute'
  | 'dashboard:view_provenance' | 'dashboard:view_audit';
export type DashboardRuntimeStatusV2 = 'COMPLETE' | 'PARTIAL' | 'BLOCKED' | 'UNAVAILABLE';
export type DashboardCacheIndicatorV2 = 'HIT' | 'MISS' | 'BYPASS' | 'MATERIALIZATION_HIT';

export interface DashboardRecordV2 {
  readonly contract_version: typeof DASHBOARD_BACKEND_CONTRACT_VERSION;
  readonly identity: {
    readonly dashboard_id: string;
    readonly canonical_name: string;
    readonly title: string;
    readonly description: string;
  };
  readonly ownership: {
    readonly ownership_type: DashboardOwnershipTypeV2;
    readonly owner_reference: string;
  };
  readonly lifecycle: DashboardLifecycleV2;
  readonly head_lifecycle: DashboardLifecycleV2;
  readonly origin: DashboardOriginV2;
  readonly classification: string;
  readonly head_revision_id?: string;
  readonly active_publication_id?: string;
  readonly lock_version: number;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface DashboardRevisionRecordV2 {
  readonly revision_id: string;
  readonly dashboard_id: string;
  readonly parent_revision_id?: string;
  readonly blueprint_contract_version: 'lumina.dashboard-blueprint/2.0';
  readonly blueprint_version: string;
  readonly semantic: { readonly number: number; readonly checksum: string; readonly validation_status: 'VALID' | 'BLOCKED' };
  readonly visual: { readonly number: number; readonly checksum: string };
  readonly blueprint: DashboardBlueprintV2;
  readonly blueprint_checksum: string;
  readonly validation_reference: string;
  readonly author_reference: string;
  readonly created_at: string;
  readonly reason: string;
  readonly origin: DashboardOriginV2;
  readonly lock_version: number;
}

export interface DashboardPublicationV2 {
  readonly publication_id: string;
  readonly dashboard_id: string;
  readonly revision: {
    readonly revision_id: string;
    readonly dashboard_id: string;
    readonly blueprint_checksum: string;
    readonly semantic_checksum: string;
    readonly visual_checksum: string;
  };
  readonly publication_version: string;
  readonly generation: number;
  readonly status: 'PUBLISHED' | 'SUPERSEDED';
  readonly supersedes_publication_id?: string;
  readonly published_by: string;
  readonly published_at: string;
}

export interface DashboardEffectiveFilterV2 {
  readonly filter_id: string;
  readonly canonical_target_id: string;
  readonly canonical_values: readonly string[];
}

export interface DashboardWidgetRuntimePlanV2 {
  readonly widget_id: string;
  readonly binding_id: string;
  readonly analytical_dataset_id: string;
  readonly widget_type: string;
  readonly expected_result_shape: string;
  readonly metric_ids: readonly string[];
  readonly dimension_ids: readonly string[];
  readonly entity_ids: readonly string[];
  readonly canonical_period: unknown;
  readonly comparison?: unknown;
  readonly effective_filters: readonly DashboardEffectiveFilterV2[];
  readonly completeness: string;
  readonly freshness: string;
  readonly classification_ceiling: string;
  readonly permission_scope: string;
  readonly cache_preference: string;
  readonly materialization_preference: string;
  readonly execution_group: string;
  readonly analytical_cache_fingerprint: string;
  readonly plan_checksum: string;
}

export interface DashboardRuntimePlanV2 {
  readonly dashboard_id: string;
  readonly publication_id: string;
  readonly revision_id: string;
  readonly blueprint_checksum: string;
  readonly tenant_reference: string;
  readonly user_access_scope: string;
  readonly effective_filters: readonly DashboardEffectiveFilterV2[];
  readonly widget_plans: readonly DashboardWidgetRuntimePlanV2[];
  readonly execution_groups: readonly string[];
  readonly cache_decisions: readonly string[];
  readonly dependencies: readonly string[];
  readonly deadline_at: string;
  readonly maximum_widgets: number;
  readonly maximum_result_size: number;
  readonly provenance_required: true;
  readonly plan_checksum: string;
}

export interface DashboardScalarDataV2 {
  readonly data_type: 'SCALAR';
  readonly value: string;
  readonly unit: string;
  readonly currency?: string;
}

export interface DashboardTabularCellV2 {
  readonly column_id: string;
  readonly text_value?: string;
  readonly decimal_value?: string;
  readonly unit?: string;
  readonly currency?: string;
}

export interface DashboardTabularDataV2 {
  readonly data_type: 'TABULAR';
  readonly rows: readonly { readonly cells: readonly DashboardTabularCellV2[] }[];
}

export type DashboardTypedDataV2 = DashboardScalarDataV2 | DashboardTabularDataV2;

export interface DashboardWidgetRuntimeResultV2 {
  readonly widget_id: string;
  readonly binding_id: string;
  readonly status: 'COMPLETE' | 'UNAVAILABLE' | 'BLOCKED';
  readonly expected_result_shape: string;
  readonly data?: DashboardTypedDataV2;
  readonly fact_references: readonly string[];
  readonly certification_reference?: string;
  readonly provenance: DashboardRuntimeProvenanceV2;
  readonly completeness: string;
  readonly freshness: string;
  readonly truncated: boolean;
  readonly partial: boolean;
  readonly warnings: readonly DashboardRuntimeWarningV2[];
  readonly cache_indicator: DashboardCacheIndicatorV2;
  readonly generated_at: string;
  readonly checksum: string;
}

export interface DashboardRuntimeResultV2 {
  readonly execution_id: string;
  readonly dashboard_id: string;
  readonly publication_id: string;
  readonly status: DashboardRuntimeStatusV2;
  readonly widgets: readonly DashboardWidgetRuntimeResultV2[];
  readonly provenance: DashboardRuntimeProvenanceV2;
  readonly warnings: readonly DashboardRuntimeWarningV2[];
  readonly started_at: string;
  readonly completed_at: string;
  readonly checksum: string;
}

export interface DashboardRuntimeWarningV2 {
  readonly code: string;
  readonly message: string;
  readonly severity: 'INFO' | 'WARNING' | 'CRITICAL';
  readonly widget_id?: string;
}

export interface DashboardRuntimeProvenanceV2 {
  readonly publication_id: string;
  readonly blueprint_version: string;
  readonly revision_id: string;
  readonly binding_id?: string;
  readonly effective_filters: readonly DashboardEffectiveFilterV2[];
  readonly period_summary?: string;
  readonly metric_definition_references: readonly string[];
  readonly validation_status: 'CERTIFIED' | 'PARTIAL' | 'BLOCKED';
  readonly source_freshness: string;
  readonly cache_indicator: DashboardCacheIndicatorV2;
  readonly warnings: readonly DashboardRuntimeWarningV2[];
}

export interface DashboardCollaboratorRecordV2 {
  readonly collaborator_id: string;
  readonly user_reference: string;
  readonly role: DashboardCollaboratorRoleV2;
  readonly lock_version: number;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface DashboardListItemResponseV2 {
  readonly dashboard: DashboardRecordV2;
  readonly effective_capabilities: readonly DashboardCapabilityBackendV2[];
}

export interface DashboardDetailResponseV2 {
  readonly dashboard: DashboardRecordV2;
  readonly head_revision: DashboardRevisionRecordV2 | null;
  readonly active_publication: DashboardPublicationV2 | null;
  readonly collaborators: readonly DashboardCollaboratorRecordV2[];
  readonly effective_capabilities: readonly DashboardCapabilityBackendV2[];
}
