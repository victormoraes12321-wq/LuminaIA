// ================================================================
// LuminaAI — Tipos TypeScript Centrais (Strict Mode)
// Todos os contratos de dados entre Frontend e Backend FastAPI
// ================================================================

// ── Chart Types ───────────────────────────────────────────────

export type ChartType = 'BAR' | 'LINE' | 'PIE' | 'TABLE' | 'KPI' | 'AREA' | 'SCATTER' | 'HEATMAP' | 'TREEMAP' | 'FUNNEL'
export type JsonPrimitive = string | number | boolean | null
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue }

export type AnalyticalIntentKind =
  | 'METRIC' | 'RANKING' | 'BREAKDOWN' | 'COMPARISON' | 'DETAIL'
  | 'METADATA' | 'FOLLOW_UP' | 'CLARIFICATION' | 'OUT_OF_SCOPE'
export type AnalyticalReadiness =
  | 'READY' | 'CLARIFICATION_REQUIRED' | 'OUT_OF_SCOPE'
  | 'UNSUPPORTED' | 'BLOCKED' | 'ERROR'
export type AnalyticalFieldOrigin =
  | 'EXPLICIT_USER' | 'INHERITED_CONVERSATION' | 'USER_PREFERENCE'
  | 'TENANT_KNOWLEDGE' | 'DETERMINISTIC_DEFAULT' | 'LLM_INFERENCE'
  | 'LEGACY_ADAPTER' | 'SYSTEM_GENERATED'
export type AnalyticalVisualizationKind =
  | 'KPI_CARD' | 'SUMMARY_CARD' | 'DATA_TABLE' | 'BAR_CHART'
  | 'LINE_CHART' | 'AREA_CHART' | 'PIE_CHART' | 'DONUT_CHART'
  | 'SCATTER_CHART' | 'HEATMAP' | 'TREEMAP' | 'FUNNEL' | 'INSIGHTS_LIST'
export type AnalyticalValidationStatus = 'PASSED' | 'FAILED' | 'WARNING' | 'NOT_EXECUTED'

export interface AnalyticalTemporalMetadata {
  normalizer_version: string
  timezone: string
  relation: 'NONE' | 'SINGLE' | 'RANGE' | 'PERIOD_LIST' | 'COMPARISON'
  rule_ids: string[]
  warnings: string[]
  readiness: AnalyticalReadiness
}

export interface AnalyticalComparisonPlannerMetadata {
  planner_version: string
  kind: AnalyticalComparison['kind']
  operand_count: number
  metric_count: number
  dimension_count: number
  complexity: 'LOW' | 'MEDIUM' | 'HIGH' | 'REJECTED'
  complexity_score: number
  readiness: AnalyticalReadiness
  issue_codes: string[]
  strategy_hint:
    | 'SINGLE_AGGREGATION' | 'CONDITIONAL_AGGREGATION' | 'MULTI_QUERY'
    | 'GROUPED_SERIES' | 'PIVOT' | 'TARGET_JOIN'
    | 'LEGACY_COMPATIBILITY' | 'UNDECIDED'
  rule_ids: string[]
  cache_identity: string
}

export interface AnalyticalAlignedDatasetSummary {
  dataset_id: string
  metric_id: string
  alignment_keys: string[]
  series: string[]
  row_count: number
  truncated: boolean
  missing_bucket_count: number
  null_bucket_count: number
  alignment_policy: string
}

export interface AnalyticalComparisonExecutorMetadata {
  executor_version: 'lumina.comparison-executor/1.0'
  strategy:
    | 'SINGLE_AGGREGATION' | 'CONDITIONAL_AGGREGATION' | 'MULTI_QUERY'
    | 'GROUPED_SERIES' | 'PIVOT' | 'TARGET_JOIN' | 'LEGACY_COMPATIBILITY'
  cache_status: 'HIT' | 'MISS' | 'BYPASS'
  partial: boolean
  aligned_datasets: AnalyticalAlignedDatasetSummary[]
  calculation_count: number
  zero_denominator_count: number
  not_applicable_count: number
  validation_status: AnalyticalValidationStatus
  provenance_count: number
}

export interface AnalyticalContractMetadata {
  schema_name: 'lumina.analytics'
  schema_version: '2.0'
  created_at: string
  request_id: string | null
  trace_id: string | null
  pipeline: 'NEW' | 'LEGACY'
  adapter_used: string | null
  extensions: Record<string, JsonValue> & {
    temporal?: AnalyticalTemporalMetadata
    comparison_planner?: AnalyticalComparisonPlannerMetadata
    comparison_executor?: AnalyticalComparisonExecutorMetadata
  }
}

export interface AnalyticalConfidence {
  level: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN'
  score: string | number
  reasons: string[]
  requires_confirmation: boolean
}

export interface AnalyticalTimeWindow {
  window_id: string
  label: string
  start: string
  end: string
  end_inclusive: boolean
  granularity: 'DAY' | 'WEEK' | 'MONTH' | 'QUARTER' | 'SEMESTER' | 'YEAR' | 'CUSTOM'
  timezone: string
  origin: AnalyticalFieldOrigin
  confidence: AnalyticalConfidence
  raw_expression: string | null
}

export interface AnalyticalMetricReference {
  metric_id: string
  metric_version: string
  display_name: string
  unit: string
  aggregation: string
  origin: AnalyticalFieldOrigin
  confidence: AnalyticalConfidence
}

export interface AnalyticalVisualization {
  visualization_id: string
  kind: AnalyticalVisualizationKind
  title: string
  metric_ids: string[]
  dimension_ids: string[]
  data_reference: string
  priority: number
  is_primary: boolean
  origin: AnalyticalFieldOrigin
  options: Record<string, JsonValue>
}

export interface AnalyticalComparisonOperand {
  operand_id: string
  label: string
  metric_refs: AnalyticalMetricReference[]
  time_windows: AnalyticalTimeWindow[]
  filters: JsonValue[]
  entity_refs: JsonValue[]
  origin: AnalyticalFieldOrigin
}

export interface AnalyticalComparison {
  comparison_id: string
  kind: 'PERIOD_VS_PERIOD' | 'ENTITY_VS_ENTITY' | 'METRIC_VS_METRIC' | 'ACTUAL_VS_TARGET' | 'MULTI_PERIOD' | 'MULTI_ENTITY'
  operands: AnalyticalComparisonOperand[]
  calculations: Array<'VALUE' | 'ABSOLUTE_DIFFERENCE' | 'PERCENTAGE_DIFFERENCE' | 'DIRECTION' | 'SHARE' | 'RANK'>
  baseline_operand_id: string | null
  alignment_dimensions: string[]
  requested_sort: string | null
  origin: AnalyticalFieldOrigin
  confidence: AnalyticalConfidence
}

export interface AnalyticalIntentV2 {
  contract: AnalyticalContractMetadata
  intent_kind: AnalyticalIntentKind
  readiness: AnalyticalReadiness
  raw_question: string
  normalized_question: string
  metric_refs: AnalyticalMetricReference[]
  dimension_refs: JsonValue[]
  filters: JsonValue[]
  time_windows: AnalyticalTimeWindow[]
  comparison: AnalyticalComparison | null
  requested_visualizations: AnalyticalVisualization[]
  confidence: AnalyticalConfidence
  clarification: JsonValue
  out_of_scope_reason: string | null
  field_origins: Record<string, AnalyticalFieldOrigin>
}

export interface AnalyticalDatasetV2 {
  dataset_id: string
  columns: JsonValue[]
  rows: Array<Record<string, JsonValue>>
  row_count: number
  truncated: boolean
  numeric_metadata: Record<string, string | number>
  data_classification: 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'RESTRICTED'
}

export interface AnalyticalResponseV2 {
  contract: AnalyticalContractMetadata
  scope_summary: {
    tenant_id: string
    user_role: string
    session_id: string | null
  }
  intent: AnalyticalIntentV2
  plan_summary: JsonValue
  datasets: AnalyticalDatasetV2[]
  visualizations: AnalyticalVisualization[]
  provenance: JsonValue[]
  validation: {
    status: AnalyticalValidationStatus
    checks: JsonValue[]
    validated_at: string | null
    validator_version: string
  }
  summary: string | null
  insights: string[]
  warnings: string[]
  errors: JsonValue[]
  clarification: JsonValue
  legacy_compatibility: JsonValue
}

// ── API Request ────────────────────────────────────────────────

export type QueryMode = 'operational' | 'analytical' | 'executive'
export type DashboardValueBasis = 'liquido' | 'bruto' | 'ambos'
export type DashboardFormat = 'tabela' | 'grafico' | 'ambos'

export interface DashboardDefaults {
  basis: DashboardValueBasis
  format: DashboardFormat
  instructions: string
}

export interface QueryRequest {
  pergunta: string
  tenant_id: string
  mode?: QueryMode
  session_id?: string
  parent_id?: string | null
  client_message_id?: string
  expected_context_version?: number
}

// ── Chart Data Structures (espelhando o backend Python) ────────

export interface ChartDataset {
  label: string
  data: number[]
  backgroundColor: string | string[]
  borderColor: string
  borderWidth?: number
  type?: string
  tension?: number
  fill?: boolean
  yAxisID?: string
  pointRadius?: number
  pointHoverRadius?: number
  borderDash?: number[]
  borderRadius?: number
}

export interface ChartResumo {
  [key: string]: number | string
}

export interface ChartDataBar {
  labels: string[]
  datasets: ChartDataset[]
  resumo: ChartResumo
}

export interface ChartDataLine {
  labels: string[]
  datasets: ChartDataset[]
  resumo: ChartResumo
}

export interface ChartDataArea {
  labels: string[]
  datasets: ChartDataset[]
  resumo: ChartResumo
}

export interface ChartDataPie {
  labels: string[]
  values: number[]
  valores_brutos?: number[]
  colors: string[]
  resumo: ChartResumo
}

export interface TableColumn {
  key: string
  label: string
  type: 'string' | 'number' | 'currency' | 'date' | 'badge' | 'boolean'
  sortable?: boolean
  width?: string | null
}

export type TableRow = Record<string, unknown>

export interface ChartDataTable {
  columns: TableColumn[]
  rows: TableRow[]
  total_rows: number
  resumo: ChartResumo
}

export interface KPIItem {
  id: string
  label: string
  value: number
  value_formatado: string
  unit: 'BRL' | 'percent' | 'count' | 'score'
  trend: 'up' | 'down' | 'stable'
  trend_value: number
  trend_label: string
  icon: 'currency' | 'chart' | 'users' | 'star' | 'ticket'
  sparkline?: number[]
}

export interface ChartDataKPI {
  kpis: KPIItem[]
  periodo: string
  gerado_em: string
}

export interface ChartDataScatter {
  datasets: Array<{
    label: string
    data: Array<{ x: number; y: number }>
    backgroundColor: string
    borderColor: string
  }>
  eixo_x_label?: string
  eixo_y_label?: string
  resumo: ChartResumo
}

export interface BIKpis {
  receita_total?: number
  ticket_medio?: number
  [key: string]: number | string | null | undefined
}

export interface BIDatasetRow {
  segmento: string
  total: number
  [key: string]: string | number | boolean | null | undefined
}

export interface BITimeSeries {
  media_movel_3p?: number[]
  [key: string]: number[] | string[] | undefined
}

export interface BIAnomaly {
  item: string
  desvio_z?: number | string
  tipo?: string
  justificativa?: string
  [key: string]: string | number | boolean | null | undefined
}

export interface BIIntelligence {
  kpis?: BIKpis
  datasets?: Record<string, BIDatasetRow[]>
  time_series?: BITimeSeries
  anomalies?: BIAnomaly[]
}

export interface QueryTelemetry {
  timings?: Record<string, number | undefined>
}

export interface ChartDataHeatmap {
  labels_x: string[]
  labels_y: string[]
  values: Array<[number, number, number]>
  eixo_x_label?: string
  eixo_y_label?: string
}

export interface TreemapItem {
  name: string
  value: number
  children?: TreemapItem[]
}

export interface ChartDataTreemap {
  children: TreemapItem[]
}

export interface FunnelItem {
  name: string
  value: number
}

export interface ChartDataFunnel {
  values: FunnelItem[]
}

export interface ChartDataClarification {
  clarification_required?: boolean
  options?: string[]
}

export type AnyChartData =
  | ChartDataBar
  | ChartDataLine
  | ChartDataArea
  | ChartDataPie
  | ChartDataTable
  | ChartDataKPI
  | ChartDataScatter
  | ChartDataHeatmap
  | ChartDataTreemap
  | ChartDataFunnel
  | ChartDataClarification

export interface VisualizationItem {
  chart_type: ChartType
  chart_data: AnyChartData
}

// ── API Response ───────────────────────────────────────────────

export interface QueryResponse {
  query_id: string
  request_id?: string | null
  session_id?: string | null
  query_node_id?: string | null
  response_node_id?: string | null
  parent_id?: string | null
  context_version?: number | null
  context_epoch?: number | null
  conversation_status?: 'ACTIVE' | 'ARCHIVED' | 'EXPIRED' | 'DELETED' | null
  idempotent_replay?: boolean
  conversation_warning?: string | null
  view_catalog_id: string | null
  view_name: string | null
  chart_type: ChartType | null
  chart_data: AnyChartData | null
  visualizations: VisualizationItem[] | null
  analytical_contract?: AnalyticalResponseV2 | null
  bi_intelligence?: BIIntelligence | null
  parametros_extraidos: Record<string, string>
  ia_confianca: number | null
  ia_justificativa: string | null
  ia_analise?: string | null
  pergunta_original: string
  pode_favoritar: boolean
  mensagem: string | null
  resposta_direta?: string | null
  plano_execucao?: Record<string, unknown> | null
  analytical_package_id?: string | null
  package_reused?: boolean
  telemetry?: QueryTelemetry | null
  trust_center?: unknown
  data_status?: {
    query_source: 'POSTGRESQL_ANALYTICAL_CLONE'
    source_label: string
    view_name?: string | null
    synced_at: string | null
    checked_at: string
    age_minutes: number | null
    freshness: 'CURRENT' | 'STALE' | 'SYNCING' | 'DEGRADED' | 'UNKNOWN'
    sync_status: string
    records_last_sync: number
    freshness_warning_minutes: number
  } | null
  validation_summary?: {
    status: 'PASSED' | 'FAILED'
    checks_total: number
    checks_passed: number
    checks_failed: number
    validated_at: string
    checks: Array<{
      code: string
      status: 'PASS' | 'FAIL'
      actual: number
      expected: number
      difference: number
      required: boolean
    }>
  } | null
  interaction_options?: Array<{
    id: string
    label: string
    prompt: string
  }>
  admin_diagnostics?: Record<string, unknown> | null
  status?: string
  ambiguities?: string[]
  missing_information?: string[]
  goal?: string
}

export interface ApiErrorResponse {
  success: boolean
  error: {
    code: number
    message: string
    type: string
    path?: string
  }
}

// ── Session & UI State ─────────────────────────────────────────

export type MessageRole = 'user' | 'assistant' | 'error'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  timestamp: Date
  queryResponse?: QueryResponse
}

export interface HistoryItem {
  id: string
  pergunta: string
  viewName: string | null
  chartType: ChartType | null
  timestamp: Date
}

export interface FavoriteItem {
  id: string
  titulo: string
  viewName: string
  chartType: ChartType
  parametros: Record<string, string>
  queryId: string
}

// ── Theme ──────────────────────────────────────────────────────

export type Theme = 'dark' | 'light'

export interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
  isDark: boolean
}

// ── Type Guards ────────────────────────────────────────────────

export function isChartDataBar(data: AnyChartData): data is ChartDataBar {
  return 'labels' in data && 'datasets' in data && !('values' in data)
}

export function isChartDataPie(data: AnyChartData): data is ChartDataPie {
  return 'labels' in data && 'values' in data && 'colors' in data
}

export function isChartDataTable(data: AnyChartData): data is ChartDataTable {
  return 'columns' in data && 'rows' in data
}

export function isChartDataKPI(data: AnyChartData): data is ChartDataKPI {
  return 'kpis' in data
}

export function isChartDataScatter(data: AnyChartData): data is ChartDataScatter {
  return 'datasets' in data && 'eixo_x_label' in data
}

export function isChartDataHeatmap(data: AnyChartData): data is ChartDataHeatmap {
  return 'labels_x' in data && 'labels_y' in data && 'values' in data
}

export function isChartDataTreemap(data: AnyChartData): data is ChartDataTreemap {
  return 'children' in data
}

export function isChartDataFunnel(data: AnyChartData): data is ChartDataFunnel {
  return 'values' in data && !('labels' in data)
}
