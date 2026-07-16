// ================================================================
// LuminaAI — Tipos TypeScript Centrais (Strict Mode)
// Todos os contratos de dados entre Frontend e Backend FastAPI
// ================================================================

// ── Chart Types ───────────────────────────────────────────────

export type ChartType = 'BAR' | 'LINE' | 'PIE' | 'TABLE' | 'KPI' | 'AREA' | 'SCATTER' | 'HEATMAP' | 'TREEMAP' | 'FUNNEL'

// ── API Request ────────────────────────────────────────────────

export type QueryMode = 'operational' | 'analytical' | 'executive'

export interface QueryRequest {
  pergunta: string
  tenant_id: string
  mode?: QueryMode
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
  view_catalog_id: string | null
  view_name: string | null
  chart_type: ChartType | null
  chart_data: AnyChartData | null
  visualizations: VisualizationItem[] | null
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
  telemetry?: QueryTelemetry | null
  trust_center?: unknown
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
