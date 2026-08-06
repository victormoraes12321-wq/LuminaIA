import type { DashboardBlueprintV2, DashboardWidgetV2 } from '../../types/dashboard_blueprint_v2'
import type {
  DashboardDetailResponseV2,
  DashboardListItemResponseV2,
  DashboardRevisionRecordV2,
  DashboardRuntimeProvenanceV2,
  DashboardRuntimeResultV2,
  DashboardWidgetRuntimeResultV2,
} from '../../types/dashboard_backend_v2'

const HASH_A = 'a'.repeat(64)
const HASH_B = 'b'.repeat(64)
const HASH_C = 'c'.repeat(64)

function common(widgetId: string, title: string, bindingId?: string) {
  return {
    identity: { widget_id: widgetId, canonical_name: widgetId },
    title: { title, visible: true },
    ...(bindingId ? { binding_id: bindingId } : {}),
    formatting: { locale: 'pt-BR', number: { style: 'DECIMAL', minimum_fraction_digits: 2, maximum_fraction_digits: 2, negative_display: 'MINUS', null_display: 'SEM_VALOR', unit_visible: true }, theme_token: 'PRIMARY' },
    accessibility: { accessible_name: title, accessible_description: `Visualização governada de ${title}.`, summary_template: `Resumo textual de ${title}.`, table_alternative_required: true, chart_text_summary_required: true, focus_behavior: 'CONTAINER' },
    states: { loading: { label: `Carregando ${title}`, presentation: 'SKELETON', announce_to_screen_reader: true }, empty: { title: 'Sem dados', message: 'Sem dados certificados.', action: 'NONE' }, partial_message: 'Resultado parcial; consulte a proveniência.', stale_message: 'Resultado desatualizado; consulte a origem.', truncated_message: 'Resultado truncado; paginação governada pelo backend.', error: { title: 'Widget indisponível', message: 'A validação governada bloqueou o widget.', expose_diagnostics: false, action: 'OPEN_PROVENANCE' }, permission_denied_message: 'Permissão insuficiente.', unavailable_message: 'Conteúdo indisponível.' },
    theme_token: 'PRIMARY',
    visible: true,
  }
}

const chart = (type: 'LINE_CHART' | 'BAR_CHART' | 'STACKED_BAR_CHART' | 'AREA_CHART' | 'PIE_CHART' | 'DONUT_CHART', index: number) => ({
  ...common(`widget.chart.${index}`, `${type} certificado`, `binding.chart.${index}`),
  widget_type: type,
  expected_result_shape: 'TIME_SERIES',
  series: [{ series_id: `series.${index}`, metric_id: 'metric.revenue', label: 'Faturamento', theme_token: 'SERIES_1' }],
  category_axis: { binding_id: 'dimension.month', label: 'Mês', scale: 'TIME' },
  value_axis: { binding_id: 'metric.revenue', label: 'Valor', scale: 'LINEAR' },
  maximum_series: 4,
  maximum_points: 24,
}) as DashboardWidgetV2

const widgets: readonly DashboardWidgetV2[] = [
  { ...common('widget.kpi', 'Faturamento julho', 'binding.kpi'), widget_type: 'KPI', expected_result_shape: 'SCALAR', unit_display: 'SHOW', trend_display: 'NONE' } as DashboardWidgetV2,
  { ...common('widget.comparison', 'Junho versus julho', 'binding.comparison'), widget_type: 'COMPARISON_KPI', expected_result_shape: 'COMPARISON', delta_absolute_display: true, percentage_display: true, zero_denominator_presentation: 'NOT_APPLICABLE', direction_semantics_visible: true } as DashboardWidgetV2,
  chart('LINE_CHART', 1), chart('BAR_CHART', 2), chart('STACKED_BAR_CHART', 3), chart('AREA_CHART', 4), chart('PIE_CHART', 5), chart('DONUT_CHART', 6),
  { ...common('widget.table', 'Contas em aberto', 'binding.table'), widget_type: 'TABLE', expected_result_shape: 'TABLE', columns: [{ column_id: 'status', source_binding_id: 'dimension.status', column_kind: 'STATUS', label: 'Status', sortable: true, visible: true }, { column_id: 'value', source_binding_id: 'metric.open.accounts', column_kind: 'METRIC', label: 'Valor', sortable: true, visible: true }], maximum_visual_rows: 50, truncation_indicator: 'REQUIRED' } as DashboardWidgetV2,
  { ...common('widget.ranking', 'Ranking de produtos', 'binding.ranking'), widget_type: 'RANKING', expected_result_shape: 'RANKING', metric_id: 'metric.revenue', ranking_dimension_id: 'dimension.product', top_n: 3 } as DashboardWidgetV2,
  { ...common('widget.status', 'Status do estoque', 'binding.status'), widget_type: 'STATUS_SUMMARY', expected_result_shape: 'STATUS_SUMMARY' } as DashboardWidgetV2,
  { ...common('widget.progress', 'Atingimento certificado', 'binding.progress'), widget_type: 'PROGRESS', expected_result_shape: 'COMPARISON' } as DashboardWidgetV2,
  { ...common('widget.filters', 'Filtros'), widget_type: 'FILTER_PANEL', filter_ids: ['filter.branch'], orientation: 'RESPONSIVE' } as DashboardWidgetV2,
  { ...common('widget.text', 'Orientação'), widget_type: 'TEXT_BLOCK', content_format: 'PLAIN_TEXT', content: 'Valores vêm exclusivamente do runtime certificado.', internal_links: [] } as DashboardWidgetV2,
  { ...common('widget.divider', 'Separador'), widget_type: 'DIVIDER', orientation: 'HORIZONTAL' } as DashboardWidgetV2,
  { ...common('widget.provenance', 'Resumo de proveniência'), widget_type: 'PROVENANCE_SUMMARY', display: ['SOURCE_FRESHNESS', 'FILTERS_APPLIED', 'METRIC_DEFINITION', 'VALIDATION_STATUS', 'WARNINGS'] } as DashboardWidgetV2,
]

const binding = (id: string, shape: string) => ({ binding_id: id, analytical_dataset_id: 'dataset.sales', metrics: [{ metric_id: 'metric.revenue', metric_registry_version: 'metric-registry/1', expected_unit: 'BRL', expected_aggregation: 'SUM' }], dimensions: [{ dimension_id: 'dimension.month', display_label: 'Mês', grouping_intent: 'TIME_BUCKET', sorting_intent: 'ASC', null_handling: 'PRESERVE', maximum_visual_cardinality: 24, drilldown_eligible: true }], period: { period_type: 'FIXED', period_id: 'period.2026.07', start_date: '2026-07-01', end_date: '2026-07-31' }, expected_result_shape: shape, completeness: 'PARTIAL_ALLOWED_WITH_NOTICE', freshness: 'BACKEND_POLICY', provenance: { public_summary_required: true, source_freshness_required: true, applied_filters_required: true, metric_definition_required: true, cache_indicator_required: true, validation_status_required: true, warnings_required: true }, classification: 'TENANT_BUSINESS_DATA', cache_preference: 'BACKEND_DECIDES', materialization_preference: 'BACKEND_DECIDES' })

export const dashboardBlueprintFixture = {
  version: { contract_id: 'lumina.dashboard-blueprint', contract_version: 'lumina.dashboard-blueprint/2.0', blueprint_version: '2.0.0', revision: { visual_revision: 1, semantic_revision: 1 }, publication_version: '1.0.0' },
  identity: { blueprint_id: 'dashboard.sales.001', canonical_name: 'dashboard.sales.001', title: 'Visão comercial governada', description: 'Painel certificado para decisões comerciais.', locale: 'pt-BR', timezone_policy: 'TENANT_AUTHORITY' },
  purpose: { purpose_id: 'purpose.sales', summary: 'Acompanhar resultados certificados.', analytical_domains: ['sales'], intended_decisions: ['monitorar desempenho'] },
  lifecycle: 'PUBLISHED', created_origin: 'HUMAN_AUTHORED', audience: { audience_ids: ['audience.management'], minimum_role: 'CONSULTA' },
  governance: { classification: 'TENANT_BUSINESS_DATA', contains_personal_data: false, template_eligible: true, permissions: [{ capability: 'dashboard:view', required: true, reason: 'Leitura governada.' }] },
  layout: { breakpoints: (['MOBILE', 'TABLET', 'DESKTOP', 'ULTRAWIDE'] as const).map((breakpoint, breakpointIndex) => { const columns = [4, 8, 12, 16][breakpointIndex]; return { breakpoint, minimum_width_px: [0, 700, 1180, 1720][breakpointIndex], grid: { columns, row_height_policy: 'FIXED_MEDIUM', gap_px: 16, padding_px: 16 }, items: widgets.map((widget, index) => ({ widget_id: widget.identity.widget_id, x: 0, y: index * 4, width: columns, height: 4, reading_order: index, visible: true })) } }) },
  widgets,
  data_bindings: [binding('binding.kpi', 'SCALAR'), binding('binding.comparison', 'COMPARISON'), ...[1, 2, 3, 4, 5, 6].map(index => binding(`binding.chart.${index}`, 'TIME_SERIES')), binding('binding.table', 'TABLE'), binding('binding.ranking', 'RANKING'), binding('binding.status', 'STATUS_SUMMARY'), binding('binding.progress', 'COMPARISON')],
  filters: [{ filter_type: 'SINGLE_SELECT', filter_id: 'filter.branch', canonical_target_id: 'dimension.branch', scope: 'DASHBOARD_GLOBAL', target_widget_ids: widgets.filter(widget => 'binding_id' in widget).map(widget => widget.identity.widget_id), default: { mode: 'ALL_ALLOWED', canonical_values: [] }, required: false, visible: true, allowed_source: 'USER_SELECTION', maximum_selections: 1, accessibility_label: 'Filial' }],
  interactions: [
    { interaction_type: 'CROSS_FILTER', interaction_id: 'interaction.branch', source_widget_id: 'widget.chart.2', source_dimension_id: 'dimension.branch', target_widget_ids: ['widget.kpi'], target_filter_id: 'filter.branch', propagation_mode: 'DASHBOARD_GLOBAL', clear_behavior: 'CLEAR_ON_DESELECT', enabled: true },
    { interaction_type: 'DRILLDOWN', interaction_id: 'interaction.product', source_widget_id: 'widget.chart.2', source_dimension_id: 'dimension.branch', target_dimension_id: 'dimension.product', hierarchy_id: 'hierarchy.sales', permission_requirement: 'dashboard:drilldown', fallback: 'SHOW_MESSAGE', enabled: true },
  ],
  accessibility: { accessible_title: 'Visão comercial governada', accessible_description: 'Dashboard certificado.', reading_order: widgets.map(widget => widget.identity.widget_id), landmark_strategy: 'SECTIONS_WITH_LABELS', keyboard_navigation: 'DOCUMENT_ORDER', reduced_motion: 'RESPECT_SYSTEM', screen_reader_summary: 'Resumo do painel comercial.', textual_fallback_required: true, color_independent_status: true },
  refresh_policy: 'MANUAL', compatibility: { minimum_contract_version: '2.0', maximum_contract_version_exclusive: '3.0', required_features: ['responsive_grid', 'provenance_panel'], deprecated_features: [] }, checksum: null, contract_state: 'CONTRACT_ONLY',
} as DashboardBlueprintV2

export const dashboardRevisionFixture: DashboardRevisionRecordV2 = { revision_id: 'revision.sales.001', dashboard_id: 'dashboard.sales.001', blueprint_contract_version: 'lumina.dashboard-blueprint/2.0', blueprint_version: '2.0.0', semantic: { number: 1, checksum: HASH_A, validation_status: 'VALID' }, visual: { number: 1, checksum: HASH_B }, blueprint: dashboardBlueprintFixture, blueprint_checksum: HASH_C, validation_reference: 'validation.sales.001', author_reference: 'user-admin', created_at: '2026-08-05T12:00:00Z', reason: 'Publicação inicial', origin: 'HUMAN_AUTHORED', lock_version: 1 }

export const dashboardDetailFixture: DashboardDetailResponseV2 = { dashboard: { contract_version: 'lumina.dashboard-backend/1.0', identity: { dashboard_id: 'dashboard.sales.001', canonical_name: 'dashboard.sales.001', title: 'Visão comercial governada', description: 'Painel certificado para decisões comerciais.' }, ownership: { ownership_type: 'USER', owner_reference: 'user-admin' }, lifecycle: 'PUBLISHED', head_lifecycle: 'PUBLISHED', origin: 'HUMAN_AUTHORED', classification: 'TENANT_BUSINESS_DATA', head_revision_id: dashboardRevisionFixture.revision_id, active_publication_id: 'publication.sales.001', lock_version: 1, created_at: '2026-08-05T12:00:00Z', updated_at: '2026-08-05T12:00:00Z' }, head_revision: dashboardRevisionFixture, active_publication: { publication_id: 'publication.sales.001', dashboard_id: 'dashboard.sales.001', revision: { revision_id: dashboardRevisionFixture.revision_id, dashboard_id: 'dashboard.sales.001', blueprint_checksum: HASH_C, semantic_checksum: HASH_A, visual_checksum: HASH_B }, publication_version: '1.0.0', generation: 1, status: 'PUBLISHED', published_by: 'user-publisher', published_at: '2026-08-05T12:00:00Z' }, collaborators: [{ collaborator_id: 'collaborator.001', user_reference: 'user-editor', role: 'EDITOR_VISUAL', lock_version: 1, created_at: '2026-08-05T12:00:00Z', updated_at: '2026-08-05T12:00:00Z' }], effective_capabilities: ['dashboard:create', 'dashboard:view', 'dashboard:list', 'dashboard:clone', 'dashboard:execute', 'dashboard:view_provenance', 'dashboard:edit_visual', 'dashboard:edit_semantic', 'dashboard:review', 'dashboard:approve', 'dashboard:publish', 'dashboard:rollback', 'dashboard:view_audit'] }

export const dashboardListFixture: readonly DashboardListItemResponseV2[] = [{ dashboard: dashboardDetailFixture.dashboard, effective_capabilities: dashboardDetailFixture.effective_capabilities }]

const provenance: DashboardRuntimeProvenanceV2 = { publication_id: 'publication.sales.001', blueprint_version: '2.0.0', revision_id: 'revision.sales.001', effective_filters: [], period_summary: 'Julho de 2026', metric_definition_references: ['metric.revenue.public'], validation_status: 'PARTIAL', source_freshness: 'STALE_WITH_NOTICE · 2026-08-05T11:30:00Z', cache_indicator: 'HIT', warnings: [{ code: 'SOURCE_STALE', message: 'Fonte atualizada há 30 minutos.', severity: 'WARNING' }] }

function widgetResult(widgetId: string, bindingId: string, shape: string, data: DashboardWidgetRuntimeResultV2['data'], options?: { readonly partial?: boolean; readonly truncated?: boolean }): DashboardWidgetRuntimeResultV2 {
  return { widget_id: widgetId, binding_id: bindingId, status: 'COMPLETE', expected_result_shape: shape, data, fact_references: ['fact.synthetic.001'], certification_reference: 'certification.synthetic.001', provenance: { ...provenance, binding_id: bindingId }, completeness: options?.partial ? 'PARTIAL' : 'COMPLETE', freshness: 'STALE_WITH_NOTICE · 2026-08-05T11:30:00Z', truncated: options?.truncated ?? false, partial: options?.partial ?? false, warnings: options?.partial ? [{ code: 'PARTIAL_RESULT', message: 'Resultado parcial preservado.', severity: 'WARNING', widget_id: widgetId }] : [], cache_indicator: 'HIT', generated_at: '2026-08-05T12:00:00Z', checksum: HASH_A }
}

const timeSeries = { data_type: 'TABULAR' as const, rows: [{ cells: [{ column_id: 'month', text_value: 'Junho' }, { column_id: 'revenue', decimal_value: '300.00', unit: 'BRL' }] }, { cells: [{ column_id: 'month', text_value: 'Julho' }, { column_id: 'revenue', decimal_value: '400.00', unit: 'BRL' }] }] }
export const dashboardRuntimeFixture: DashboardRuntimeResultV2 = { execution_id: 'execution.sales.001', dashboard_id: 'dashboard.sales.001', publication_id: 'publication.sales.001', status: 'PARTIAL', widgets: [
  widgetResult('widget.kpi', 'binding.kpi', 'SCALAR', { data_type: 'SCALAR', value: '400.00', unit: 'BRL', currency: 'BRL' }),
  widgetResult('widget.comparison', 'binding.comparison', 'COMPARISON', { data_type: 'TABULAR', rows: [{ cells: [{ column_id: 'current', decimal_value: '400.00' }, { column_id: 'baseline', decimal_value: '300.00' }, { column_id: 'delta', decimal_value: '100.00' }, { column_id: 'percentage', text_value: '+33,33%' }, { column_id: 'direction', text_value: 'Aumentou' }] }] }),
  ...[1, 2, 3, 4, 5, 6].map(index => widgetResult(`widget.chart.${index}`, `binding.chart.${index}`, 'TIME_SERIES', timeSeries)),
  widgetResult('widget.table', 'binding.table', 'TABLE', { data_type: 'TABULAR', rows: [{ cells: [{ column_id: 'status', text_value: 'ABERTO' }, { column_id: 'value', decimal_value: '1250.00' }] }] }, { partial: true, truncated: true }),
  widgetResult('widget.ranking', 'binding.ranking', 'RANKING', { data_type: 'TABULAR', rows: [{ cells: [{ column_id: 'rank', decimal_value: '1' }, { column_id: 'label', text_value: 'Produto A' }, { column_id: 'value', decimal_value: '400.00' }, { column_id: 'tie', text_value: 'false' }] }] }, { truncated: true }),
  widgetResult('widget.status', 'binding.status', 'STATUS_SUMMARY', { data_type: 'SCALAR', value: 'ATUALIZADO', unit: 'status' }),
  widgetResult('widget.progress', 'binding.progress', 'COMPARISON', { data_type: 'SCALAR', value: '82.50', unit: 'PERCENT' }),
], provenance, warnings: [{ code: 'PARTIAL_RESULT', message: 'Um widget foi truncado.', severity: 'WARNING', widget_id: 'widget.table' }], started_at: '2026-08-05T12:00:00Z', completed_at: '2026-08-05T12:00:01Z', checksum: HASH_C }

export function revisedDashboardFixture(title = 'Título atualizado pelo side chat'): DashboardRevisionRecordV2 {
  return { ...dashboardRevisionFixture, revision_id: 'revision.sales.002', parent_revision_id: dashboardRevisionFixture.revision_id, visual: { number: 2, checksum: 'd'.repeat(64) }, blueprint: { ...dashboardBlueprintFixture, identity: { ...dashboardBlueprintFixture.identity, title } }, blueprint_checksum: 'e'.repeat(64), reason: 'Ajuste visual pelo side chat', lock_version: 1 }
}
