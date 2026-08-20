/** Canonical contract-only mirror of lumina.dashboard-blueprint/2.0. */

export const DASHBOARD_BLUEPRINT_CONTRACT_VERSION = 'lumina.dashboard-blueprint/2.0' as const;

export type DashboardLifecycleV2 =
  | 'DRAFT' | 'IN_REVIEW' | 'APPROVED' | 'PUBLISHED'
  | 'SUPERSEDED' | 'DEPRECATED' | 'ARCHIVED' | 'REJECTED';

export type DashboardOriginV2 =
  | 'HUMAN_AUTHORED' | 'TEMPLATE' | 'MIGRATED_LEGACY'
  | 'AI_PROPOSED' | 'AI_ASSISTED' | 'SYSTEM_GENERATED';

export type DashboardClassificationV2 =
  | 'PUBLIC_METADATA' | 'TENANT_METADATA' | 'TENANT_BUSINESS_DATA'
  | 'RESTRICTED_BUSINESS_DATA' | 'PERSONAL_DATA'
  | 'SENSITIVE_PERSONAL_DATA' | 'SECRET' | 'FORBIDDEN';

export type DashboardCapabilityV2 =
  | 'dashboard:view' | 'dashboard:filter' | 'dashboard:drilldown'
  | 'dashboard:export' | 'dashboard:edit_visual' | 'dashboard:edit_semantic'
  | 'dashboard:review' | 'dashboard:publish' | 'dashboard:archive'
  | 'dashboard:view_provenance';

export interface DashboardRevisionV2 {
  readonly visual_revision: number;
  readonly semantic_revision: number;
}

export interface DashboardVersionV2 {
  readonly contract_id: 'lumina.dashboard-blueprint';
  readonly contract_version: typeof DASHBOARD_BLUEPRINT_CONTRACT_VERSION;
  readonly blueprint_version: string;
  readonly revision: DashboardRevisionV2;
  readonly publication_version?: string;
}

export interface DashboardIdentityV2 {
  readonly blueprint_id: string;
  readonly canonical_name: string;
  readonly title: string;
  readonly description: string;
  readonly locale: 'pt-BR';
  readonly timezone_policy: 'TENANT_AUTHORITY' | 'USER_THEN_TENANT' | 'APPLICATION_DEFAULT';
}

export interface DashboardPurposeV2 {
  readonly purpose_id: string;
  readonly summary: string;
  readonly analytical_domains: readonly string[];
  readonly intended_decisions: readonly string[];
}

export interface DashboardAudienceV2 {
  readonly audience_ids: readonly string[];
  readonly minimum_role: 'CONSULTA' | 'GESTOR' | 'ADMIN';
}

export interface DashboardPermissionRequirementV2 {
  readonly capability: DashboardCapabilityV2;
  readonly required: boolean;
  readonly reason: string;
}

export interface DashboardGovernanceV2 {
  readonly classification: DashboardClassificationV2;
  readonly contains_personal_data: boolean;
  readonly template_eligible: boolean;
  readonly permissions: readonly DashboardPermissionRequirementV2[];
}

export type DashboardBreakpointNameV2 = 'MOBILE' | 'TABLET' | 'DESKTOP' | 'ULTRAWIDE';

export interface DashboardGridV2 {
  readonly columns: number;
  readonly row_height_policy: 'CONTENT_AWARE' | 'FIXED_SMALL' | 'FIXED_MEDIUM' | 'FIXED_LARGE';
  readonly gap_px: number;
  readonly padding_px: number;
}

export interface DashboardGridItemV2 {
  readonly widget_id: string;
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
  readonly reading_order: number;
  readonly visible: boolean;
  readonly fallback_widget_id?: string;
}

export interface DashboardResponsiveBreakpointV2 {
  readonly breakpoint: DashboardBreakpointNameV2;
  readonly minimum_width_px: number;
  readonly grid: DashboardGridV2;
  readonly items: readonly DashboardGridItemV2[];
}

export interface DashboardLayoutV2 {
  readonly breakpoints: readonly DashboardResponsiveBreakpointV2[];
}

export type DashboardResultShapeV2 =
  | 'SCALAR' | 'COMPARISON' | 'TIME_SERIES' | 'GROUPED_SERIES'
  | 'RANKING' | 'TABLE' | 'STATUS_SUMMARY' | 'FACT_SET';

export interface DashboardMetricBindingV2 {
  readonly metric_id: string;
  readonly metric_registry_version: string;
  readonly expected_unit: string;
  readonly expected_aggregation: 'SUM' | 'AVERAGE' | 'COUNT' | 'MIN' | 'MAX' | 'NONE';
  readonly expected_fingerprint?: string;
  readonly display_alias?: string;
}

export interface DashboardDimensionBindingV2 {
  readonly dimension_id: string;
  readonly display_label: string;
  readonly grouping_intent: 'CATEGORY' | 'TIME_BUCKET' | 'HIERARCHY' | 'NONE';
  readonly sorting_intent: 'ASC' | 'DESC' | 'METRIC_ASC' | 'METRIC_DESC' | 'NONE';
  readonly null_handling: 'PRESERVE' | 'LABEL_UNKNOWN' | 'OMIT';
  readonly maximum_visual_cardinality: number;
  readonly drilldown_eligible: boolean;
}

export interface DashboardFixedPeriodBindingV2 {
  readonly period_type: 'FIXED';
  readonly period_id: string;
  readonly start_date: string;
  readonly end_date: string;
}

export interface DashboardRelativePeriodBindingV2 {
  readonly period_type: 'RELATIVE';
  readonly canonical_period_id: string;
  readonly relation: 'CURRENT' | 'PREVIOUS' | 'ROLLING' | 'TO_DATE';
  readonly offset: number;
}

export interface DashboardInheritedPeriodBindingV2 {
  readonly period_type: 'INHERITED_DASHBOARD';
  readonly source: 'DASHBOARD_CONTEXT';
}

export interface DashboardFilterDrivenPeriodBindingV2 {
  readonly period_type: 'FILTER_DRIVEN';
  readonly filter_id: string;
}

export type DashboardPeriodBindingV2 =
  | DashboardFixedPeriodBindingV2 | DashboardRelativePeriodBindingV2
  | DashboardInheritedPeriodBindingV2 | DashboardFilterDrivenPeriodBindingV2;

export interface DashboardComparisonBindingV2 {
  readonly current_period: DashboardPeriodBindingV2;
  readonly baseline_period: DashboardPeriodBindingV2;
  readonly relationship: 'PERIOD_OVER_PERIOD' | 'YEAR_OVER_YEAR' | 'ACTUAL_VS_TARGET' | 'ENTITY_VS_ENTITY';
  readonly display_delta_absolute: boolean;
  readonly display_percentage: boolean;
  readonly zero_baseline_policy: 'NOT_APPLICABLE' | 'ABSOLUTE_ONLY' | 'ERROR';
  readonly direction_semantics: 'HIGHER_IS_BETTER' | 'LOWER_IS_BETTER' | 'NEUTRAL' | 'METRIC_REGISTRY';
}

export interface DashboardProvenanceRequirementV2 {
  readonly public_summary_required: boolean;
  readonly source_freshness_required: boolean;
  readonly applied_filters_required: boolean;
  readonly metric_definition_required: boolean;
  readonly cache_indicator_required: boolean;
  readonly validation_status_required: boolean;
  readonly warnings_required: boolean;
}

export interface DashboardDataBindingV2 {
  readonly binding_id: string;
  readonly analytical_dataset_id: string;
  readonly metrics: readonly DashboardMetricBindingV2[];
  readonly dimensions: readonly DashboardDimensionBindingV2[];
  readonly period: DashboardPeriodBindingV2;
  readonly comparison?: DashboardComparisonBindingV2;
  readonly expected_result_shape: DashboardResultShapeV2;
  readonly completeness: 'COMPLETE' | 'TRUNCATION_ALLOWED_WITH_NOTICE' | 'PARTIAL_ALLOWED_WITH_NOTICE';
  readonly freshness: 'FRESH' | 'STALE_WITH_NOTICE' | 'BACKEND_POLICY';
  readonly provenance: DashboardProvenanceRequirementV2;
  readonly classification: DashboardClassificationV2;
  readonly cache_preference: 'CACHE_PREFERRED' | 'CACHE_BYPASS_PROHIBITED' | 'BACKEND_DECIDES';
  readonly materialization_preference: 'MATERIALIZATION_PREFERRED' | 'MATERIALIZATION_REQUIRED' | 'LIVE_QUERY_REQUIRED' | 'BACKEND_DECIDES';
}

export type DashboardThemeTokenV2 =
  | 'PRIMARY' | 'SECONDARY' | 'POSITIVE' | 'NEGATIVE' | 'WARNING'
  | 'NEUTRAL' | 'INFO' | 'SERIES_1' | 'SERIES_2' | 'SERIES_3'
  | 'SERIES_4' | 'SERIES_5' | 'SERIES_6' | 'SERIES_7' | 'SERIES_8';

export interface DashboardFormattingV2 {
  readonly locale: 'pt-BR';
  readonly number: {
    readonly style: 'DECIMAL' | 'INTEGER' | 'COMPACT';
    readonly minimum_fraction_digits: number;
    readonly maximum_fraction_digits: number;
    readonly negative_display: 'MINUS' | 'PARENTHESES';
    readonly null_display: 'SEM_VALOR' | 'TRACO' | 'VAZIO';
    readonly unit_visible: boolean;
  };
  readonly currency?: { readonly currency_code: 'BRL' | 'USD' | 'EUR'; readonly display: 'SYMBOL' | 'CODE' | 'NAME'; readonly decimal_places: number };
  readonly date?: { readonly format: 'DATE_SHORT' | 'DATE_LONG' | 'MONTH_YEAR' | 'YEAR' | 'DATETIME'; readonly timezone_policy: 'DASHBOARD' | 'TENANT' | 'USER' };
  readonly percentage_display?: 'ALREADY_PERCENT' | 'RATIO_TO_PERCENT';
  readonly theme_token: DashboardThemeTokenV2;
}

export interface DashboardWidgetAccessibilityV2 {
  readonly accessible_name: string;
  readonly accessible_description: string;
  readonly summary_template: string;
  readonly table_alternative_required: boolean;
  readonly chart_text_summary_required: boolean;
  readonly focus_behavior: 'CONTAINER' | 'FIRST_CONTROL' | 'NOT_FOCUSABLE';
}

export interface DashboardWidgetStatesV2 {
  readonly loading: { readonly label: string; readonly presentation: 'SKELETON' | 'PROGRESS' | 'TEXT'; readonly announce_to_screen_reader: boolean };
  readonly empty: { readonly title: string; readonly message: string; readonly action: 'NONE' | 'RESET_FILTERS' | 'CHANGE_PERIOD' };
  readonly partial_message: string;
  readonly stale_message: string;
  readonly truncated_message: string;
  readonly error: { readonly title: string; readonly message: string; readonly expose_diagnostics: boolean; readonly action: 'NONE' | 'RETRY' | 'OPEN_PROVENANCE' };
  readonly permission_denied_message: string;
  readonly unavailable_message: string;
}

export interface DashboardWidgetCommonV2 {
  readonly identity: { readonly widget_id: string; readonly canonical_name: string };
  readonly title: { readonly title: string; readonly subtitle?: string; readonly visible: boolean };
  readonly binding_id?: string;
  readonly formatting: DashboardFormattingV2;
  readonly accessibility: DashboardWidgetAccessibilityV2;
  readonly states: DashboardWidgetStatesV2;
  readonly theme_token: DashboardThemeTokenV2;
  readonly visible: boolean;
}

export interface DashboardKpiWidgetV2 extends DashboardWidgetCommonV2 {
  readonly widget_type: 'KPI';
  readonly binding_id: string;
  readonly expected_result_shape: 'SCALAR' | 'COMPARISON';
  readonly unit_display: 'AUTO' | 'SHOW' | 'HIDE';
  readonly trend_display: 'NONE' | 'DIRECTION' | 'SPARKLINE_REFERENCE';
}

export interface DashboardComparisonKpiWidgetV2 extends DashboardWidgetCommonV2 {
  readonly widget_type: 'COMPARISON_KPI';
  readonly binding_id: string;
  readonly expected_result_shape: 'COMPARISON';
  readonly delta_absolute_display: boolean;
  readonly percentage_display: boolean;
  readonly zero_denominator_presentation: 'NOT_APPLICABLE' | 'ABSOLUTE_ONLY' | 'ERROR';
  readonly direction_semantics_visible: boolean;
}

export type DashboardChartTypeV2 = 'LINE_CHART' | 'BAR_CHART' | 'STACKED_BAR_CHART' | 'AREA_CHART' | 'PIE_CHART' | 'DONUT_CHART';

export interface DashboardChartWidgetV2 extends DashboardWidgetCommonV2 {
  readonly widget_type: DashboardChartTypeV2;
  readonly binding_id: string;
  readonly expected_result_shape: 'TIME_SERIES' | 'GROUPED_SERIES';
  readonly series: readonly { readonly series_id: string; readonly metric_id: string; readonly label: string; readonly theme_token: DashboardThemeTokenV2 }[];
  readonly category_axis: { readonly binding_id: string; readonly label: string; readonly scale: 'LINEAR' | 'TIME' | 'CATEGORY' };
  readonly value_axis: { readonly binding_id: string; readonly label: string; readonly scale: 'LINEAR' | 'TIME' | 'CATEGORY' };
  readonly maximum_series: number;
  readonly maximum_points: number;
}

export interface DashboardTableWidgetV2 extends DashboardWidgetCommonV2 {
  readonly widget_type: 'TABLE';
  readonly binding_id: string;
  readonly expected_result_shape: 'TABLE' | 'FACT_SET';
  readonly columns: readonly { readonly column_id: string; readonly source_binding_id: string; readonly column_kind: 'METRIC' | 'DIMENSION' | 'STATUS'; readonly label: string; readonly sortable: boolean; readonly visible: boolean }[];
  readonly maximum_visual_rows: number;
  readonly truncation_indicator: 'REQUIRED' | 'NOT_APPLICABLE';
}

export interface DashboardRankingWidgetV2 extends DashboardWidgetCommonV2 {
  readonly widget_type: 'RANKING';
  readonly binding_id: string;
  readonly expected_result_shape: 'RANKING';
  readonly metric_id: string;
  readonly ranking_dimension_id: string;
  readonly top_n: number;
}

export interface DashboardSimpleAnalyticalWidgetV2 extends DashboardWidgetCommonV2 {
  readonly widget_type: 'STATUS_SUMMARY' | 'PROGRESS';
  readonly binding_id: string;
  readonly expected_result_shape: 'STATUS_SUMMARY' | 'COMPARISON';
}

export interface DashboardFilterPanelWidgetV2 extends DashboardWidgetCommonV2 {
  readonly widget_type: 'FILTER_PANEL';
  readonly filter_ids: readonly string[];
  readonly orientation: 'HORIZONTAL' | 'VERTICAL' | 'RESPONSIVE';
}

export interface DashboardTextBlockWidgetV2 extends DashboardWidgetCommonV2 {
  readonly widget_type: 'TEXT_BLOCK';
  readonly content_format: 'PLAIN_TEXT' | 'LIMITED_MARKDOWN';
  readonly content: string;
  readonly internal_links: readonly { readonly label: string; readonly route_id: string }[];
}

export interface DashboardDividerWidgetV2 extends DashboardWidgetCommonV2 {
  readonly widget_type: 'DIVIDER';
  readonly orientation: 'HORIZONTAL' | 'VERTICAL';
}

export interface DashboardProvenanceSummaryWidgetV2 extends DashboardWidgetCommonV2 {
  readonly widget_type: 'PROVENANCE_SUMMARY';
  readonly display: readonly ('SOURCE_FRESHNESS' | 'FILTERS_APPLIED' | 'METRIC_DEFINITION' | 'VALIDATION_STATUS' | 'WARNINGS')[];
}

export type DashboardWidgetV2 =
  | DashboardKpiWidgetV2 | DashboardComparisonKpiWidgetV2 | DashboardChartWidgetV2
  | DashboardTableWidgetV2 | DashboardRankingWidgetV2 | DashboardSimpleAnalyticalWidgetV2
  | DashboardFilterPanelWidgetV2 | DashboardTextBlockWidgetV2 | DashboardDividerWidgetV2
  | DashboardProvenanceSummaryWidgetV2;

export type DashboardFilterTypeV2 = 'DATE_RANGE' | 'RELATIVE_PERIOD' | 'SINGLE_SELECT' | 'MULTI_SELECT' | 'ENTITY_SELECT' | 'BOOLEAN' | 'NUMBER_RANGE' | 'STATUS_SELECT' | 'SEARCH';

export interface DashboardFilterV2 {
  readonly filter_type: DashboardFilterTypeV2;
  readonly filter_id: string;
  readonly canonical_target_id: string;
  readonly scope: 'DASHBOARD_GLOBAL' | 'WIDGET_LOCAL' | 'SECTION' | 'INHERITED_CONTEXT';
  readonly target_widget_ids: readonly string[];
  readonly default: { readonly mode: 'EXPLICIT' | 'ALL_ALLOWED' | 'INHERITED_CONTEXT' | 'NONE'; readonly canonical_values: readonly (string | number | boolean)[] };
  readonly required: boolean;
  readonly visible: boolean;
  readonly allowed_source: 'USER_SELECTION' | 'INHERITED_CONTEXT' | 'GOVERNED_DEFAULT';
  readonly maximum_selections: number;
  readonly accessibility_label: string;
}

export type DashboardInteractionV2 =
  | { readonly interaction_type: 'CROSS_FILTER'; readonly interaction_id: string; readonly source_widget_id: string; readonly source_dimension_id: string; readonly target_widget_ids: readonly string[]; readonly target_filter_id: string; readonly propagation_mode: 'DIRECT' | 'DASHBOARD_GLOBAL'; readonly clear_behavior: 'CLEAR_ON_DESELECT' | 'PERSIST_UNTIL_RESET'; readonly enabled: boolean }
  | { readonly interaction_type: 'DRILLDOWN'; readonly interaction_id: string; readonly source_widget_id: string; readonly source_dimension_id: string; readonly target_dimension_id: string; readonly hierarchy_id: string; readonly target_dashboard_id?: string; readonly permission_requirement: 'dashboard:drilldown'; readonly fallback: 'DISABLE' | 'SHOW_MESSAGE' | 'OPEN_TABLE'; readonly enabled: boolean }
  | { readonly interaction_type: 'RESET_FILTERS' | 'OPEN_PROVENANCE' | 'EXPAND_WIDGET' | 'SORT' | 'PAGINATE'; readonly interaction_id: string; readonly source_widget_id: string; readonly enabled: boolean }
  | { readonly interaction_type: 'INTERNAL_NAVIGATION'; readonly interaction_id: string; readonly source_widget_id: string; readonly route_id: string; readonly dashboard_reference: string; readonly enabled: boolean };

export interface DashboardAccessibilityV2 {
  readonly accessible_title: string;
  readonly accessible_description: string;
  readonly reading_order: readonly string[];
  readonly landmark_strategy: 'SINGLE_MAIN' | 'SECTIONS_WITH_LABELS';
  readonly keyboard_navigation: 'DOCUMENT_ORDER' | 'GRID_WITH_DOCUMENT_FALLBACK';
  readonly reduced_motion: 'RESPECT_SYSTEM' | 'ALWAYS_REDUCED';
  readonly screen_reader_summary: string;
  readonly textual_fallback_required: boolean;
  readonly color_independent_status: boolean;
}

export interface DashboardCompatibilityV2 {
  readonly minimum_contract_version: '2.0';
  readonly maximum_contract_version_exclusive: '3.0';
  readonly required_features: readonly string[];
  readonly deprecated_features: readonly string[];
}

export interface DashboardBlueprintV2 {
  readonly version: DashboardVersionV2;
  readonly identity: DashboardIdentityV2;
  readonly purpose: DashboardPurposeV2;
  readonly lifecycle: DashboardLifecycleV2;
  readonly created_origin: DashboardOriginV2;
  readonly audience: DashboardAudienceV2;
  readonly governance: DashboardGovernanceV2;
  readonly layout: DashboardLayoutV2;
  readonly widgets: readonly DashboardWidgetV2[];
  readonly data_bindings: readonly DashboardDataBindingV2[];
  readonly filters: readonly DashboardFilterV2[];
  readonly interactions: readonly DashboardInteractionV2[];
  readonly accessibility: DashboardAccessibilityV2;
  readonly refresh_policy: 'MANUAL' | 'ON_OPEN' | 'AFTER_SYNC' | 'SOURCE_WATERMARK' | 'INTERVAL_POLICY' | 'DISABLED';
  readonly compatibility: DashboardCompatibilityV2;
  readonly checksum: null;
  readonly contract_state: 'CONTRACT_ONLY';
}

export type DashboardPatchValueV2 =
  | string | number | boolean | null
  | DashboardGridItemV2 | DashboardFormattingV2
  | { readonly title: string; readonly subtitle?: string; readonly visible: boolean };

export interface DashboardPatchOperationV2 {
  readonly operation: 'ADD' | 'REPLACE' | 'REMOVE' | 'MOVE';
  readonly path: string;
  readonly value?: DashboardPatchValueV2;
  readonly from_path?: string;
}

export interface DashboardVisualPatchV2 {
  readonly patch_type: 'VISUAL';
  readonly blueprint_id: string;
  readonly base_blueprint_checksum: string;
  readonly base_semantic_checksum: string;
  readonly base_visual_revision: number;
  readonly target_visual_revision: number;
  readonly operations: readonly DashboardPatchOperationV2[];
}

export interface DashboardSemanticPatchV2 {
  readonly patch_type: 'SEMANTIC';
  readonly blueprint_id: string;
  readonly base_blueprint_checksum: string;
  readonly base_semantic_checksum: string;
  readonly base_semantic_revision: number;
  readonly target_semantic_revision: number;
  readonly requires_revalidation: true;
  readonly operations: readonly DashboardPatchOperationV2[];
}

export type DashboardValidationStatusV2 = 'VALID' | 'VALID_WITH_WARNINGS' | 'INVALID' | 'BLOCKED' | 'UNSUPPORTED_VERSION';

export interface DashboardValidationIssueV2 {
  readonly code: string;
  readonly stage: string;
  readonly severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  readonly message: string;
  readonly field_path?: string;
  readonly blocking: boolean;
}

export interface DashboardValidationResultV2 {
  readonly status: DashboardValidationStatusV2;
  readonly issues: readonly DashboardValidationIssueV2[];
  readonly completed_stages: readonly string[];
  readonly canonicalization?: {
    readonly contract_version: typeof DASHBOARD_BLUEPRINT_CONTRACT_VERSION;
    readonly canonical_json: string;
    readonly checksums: {
      readonly blueprint_checksum: string;
      readonly semantic_checksum: string;
      readonly visual_checksum: string;
      readonly layout_checksum: string;
      readonly widgets_checksum: string;
      readonly bindings_checksum: string;
      readonly filters_checksum: string;
      readonly interactions_checksum: string;
      readonly accessibility_checksum: string;
    };
  };
}

export interface DashboardWidgetRegistryEntryV2 {
  readonly widget_type: DashboardWidgetV2['widget_type'];
  readonly supported_result_shapes: readonly DashboardResultShapeV2[];
  readonly binding_required: boolean;
  readonly accessibility_required: boolean;
  readonly maximum_series: number;
  readonly compatibility_version: '2.0';
}

export interface DashboardFeatureRegistryEntryV2 {
  readonly feature_id: string;
  readonly minimum_contract_version: '2.0';
  readonly supported: boolean;
}

