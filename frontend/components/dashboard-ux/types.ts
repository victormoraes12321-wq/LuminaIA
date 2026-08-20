export type MetricType =
  | 'faturamento'
  | 'quantidade'
  | 'ticket'
  | 'notas'
  | 'clientes'
  | 'vendedores'
  | 'produtos'
  | 'filiais'

export interface AnalyticalEntity {
  id: string
  name: string
  type: 'filial' | 'vendedor' | 'produto' | 'cliente'
  value?: number
  quantity?: number
  filial?: string
}

export interface BreadcrumbLevel {
  id: string
  label: string
  level: number
  context: Partial<AnalyticalContext>
}

export interface ActiveFilter {
  id: string
  label: string
  dimension: 'period' | 'filial' | 'vendedor' | 'produto' | 'cliente'
  value: string
}

export interface AnalyticalContext {
  metric: MetricType
  filial: string | null
  startDate: string
  endDate: string
  periodPreset: string
  vendedor: AnalyticalEntity | null
  produto: AnalyticalEntity | null
  cliente: AnalyticalEntity | null
  breadcrumb: BreadcrumbLevel[]
  activeFilters: ActiveFilter[]
  focusedWidget: FocusWidgetState | null
  viewModes: Record<string, 'chart' | 'table'>
}

export interface FocusWidgetState {
  widgetId: string
  title: string
  dimension: string
  metric: string
  data: any
}

export interface ExecutiveKpiData {
  faturamento: number
  quantidade: number
  total_notas: number
  total_pedidos: number
  clientes_ativos: number
  vendedores_ativos: number
  produtos_distintos: number
  filiais_ativas: number
  ticket_medio: number
  faturamento_formatted: string
  quantidade_formatted: string
  ticket_medio_formatted: string
  notas_formatted: string
  pedidos_formatted: string
}

export interface EvolutionItem {
  date: string
  label: string
  value: number
  volume: number
  invoices: number
  formatted: string
  formatted_volume: string
}

export interface BranchItem {
  filial: string
  name: string
  value: number
  percentage: number
  volume: number
  sellers_count: number
  clients_count: number
  invoices_count: number
  formatted: string
}

export interface TopSellerItem {
  id: string
  rca: number
  name: string
  filial: string
  value: number
  volume: number
  sales_count: number
  formatted: string
}

export interface TopProductItem {
  id: string
  codprod: number
  name: string
  value: number
  quantity: number
  transactions_count: number
  formatted: string
  quantity_formatted: string
}

export interface TopClientItem {
  id: string
  codcliente: number
  name: string
  value: number
  invoices_count: number
  volume: number
  formatted: string
}

export interface GovernedInsight {
  id: string
  title: string
  description: string
  type: 'highlight' | 'growth' | 'alert' | 'neutral'
  entity_type?: 'filial' | 'vendedor' | 'produto' | 'cliente'
  entity_id?: string
}

export interface DashboardMetadata {
  min_available_date: string
  max_available_date: string
  effective_start_date: string
  effective_end_date: string
  freshness: string
  available_branches: string[]
}

export interface ExecutiveDashboardData {
  metadata: DashboardMetadata
  kpis: ExecutiveKpiData
  evolution: EvolutionItem[]
  branch_performance: BranchItem[]
  top_sellers: TopSellerItem[]
  top_products: TopProductItem[]
  top_clients: TopClientItem[]
  insights: GovernedInsight[]
  loading?: boolean
  error?: string | null
}

export interface DashboardChatAction {
  action_type:
    | 'APPLY_FILTER'
    | 'DRILLDOWN'
    | 'TOGGLE_VISUALIZATION'
    | 'FOCUS_WIDGET'
    | 'GO_BACK'
    | 'RESET_FILTERS'
    | 'SET_DATE_RANGE'
  payload?: {
    dimension?: 'period' | 'filial' | 'vendedor' | 'produto' | 'cliente'
    value?: string
    entity?: AnalyticalEntity
    widget_id?: string
    view_mode?: 'chart' | 'table'
    startDate?: string
    endDate?: string
  }
}
