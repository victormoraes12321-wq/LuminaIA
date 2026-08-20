/**
 * ============================================================
 * LUMINA AI — Dashboard Runtime Engine Types
 * ============================================================
 * Defines the full TypeScript contract for all payloads
 * produced by the Adaptive Dashboard Engine (ADE) and
 * Enterprise Component Engine (ECE) on the backend.
 *
 * Rule: The frontend NEVER calculates, queries, or infers
 * business logic. It only interprets and renders.
 * ============================================================
 */

// ─────────────────────────────────────────────
// 1. BREAKPOINTS
// ─────────────────────────────────────────────

export type Breakpoint =
  | 'ultra_wide'  // ≥ 1920px
  | 'desktop'     // ≥ 1280px
  | 'notebook'    // ≥ 1024px
  | 'tablet'      // ≥ 768px
  | 'mobile';     // < 768px

export const BREAKPOINT_WIDTHS: Record<Breakpoint, number> = {
  ultra_wide: 1920,
  desktop: 1280,
  notebook: 1024,
  tablet: 768,
  mobile: 0,
};

// ─────────────────────────────────────────────
// 2. GRID POSITION (matches backend GridPosition)
// ─────────────────────────────────────────────

export interface GridPosition {
  /** Component ID this position belongs to */
  component_id: string;
  /** Column start (0-indexed, 12-column grid) */
  x: number;
  /** Row start (0-indexed) */
  y: number;
  /** Width in columns (1–12) */
  w: number;
  /** Height in rows (each row ≈ 100px) */
  h: number;
  /** Whether component is visible */
  visible: boolean;
}

export type GridLayout = GridPosition[];

export type ResponsiveGridLayouts = Partial<Record<Breakpoint, GridLayout>>;

// ─────────────────────────────────────────────
// 3. ECE COMPONENT TYPES
// ─────────────────────────────────────────────

export type ECEComponentType =
  | 'BAR_CHART'
  | 'LINE_CHART'
  | 'AREA_CHART'
  | 'PIE_CHART'
  | 'DONUT_CHART'
  | 'SCATTER_CHART'
  | 'HEATMAP_CHART'
  | 'TREEMAP_CHART'
  | 'FUNNEL_CHART'
  | 'GAUGE_CHART'
  | 'KPI_CARD'
  | 'KPI_SPARKLINE'
  | 'DATA_TABLE'
  | 'RANKING_TABLE'
  | 'FILTER_PANEL'
  | 'ALERT_BANNER'
  | 'TEXT_BLOCK'
  | 'DIVIDER';

// ─────────────────────────────────────────────
// 4. ECE COMPONENT METADATA (backend-injected)
// ─────────────────────────────────────────────

export interface ECEComponentMetadata {
  component_id: string;
  component_type: ECEComponentType;
  /** Display title shown on the card header */
  title: string;
  /** Optional subtitle / description */
  subtitle?: string;
  /** Visual weight for priority ranking */
  weight: number;
  /** Whether this component can be fullscreen-expanded */
  expandable: boolean;
  /** Whether to show border/shadow card wrapper */
  has_container: boolean;
  /** Theming hints from backend */
  theme_hints?: Record<string, string>;
  /** Accessibility label */
  aria_label?: string;
}

// ─────────────────────────────────────────────
// 5. ADE LAYOUT SCHEMA (matches backend ADELayoutSchema)
// ─────────────────────────────────────────────

export interface ADELayoutMetrics {
  total_components: number;
  visible_components: number;
  layout_efficiency: number;
  grid_utilization: number;
  estimated_load_time_ms: number;
}

export interface ADELayoutTelemetry {
  fps_estimate: number;
  render_complexity: 'low' | 'medium' | 'high' | 'critical';
  quality_score: number;
  health_score: number;
  warnings: string[];
}

export interface ADELayout {
  /** Responsive grid positions per breakpoint */
  grid_layouts: ResponsiveGridLayouts;
  /** ECE component metadata indexed by component_id */
  components: ECEComponentMetadata[];
  /** Layout computation metrics */
  metrics: ADELayoutMetrics;
  /** Render telemetry from backend optimizer */
  telemetry: ADELayoutTelemetry;
  /** Which layout strategy was chosen */
  layout_strategy: string;
  /** Timestamp of layout computation */
  generated_at: string;
}

// ─────────────────────────────────────────────
// 6. WIDGET (unified payload item)
// ─────────────────────────────────────────────

export interface RuntimeWidget {
  /** Unique ID matching ECEComponentMetadata.component_id */
  id: string;
  /** ECE component type (determines which library component to render) */
  component_type: ECEComponentType;
  /** The data payload for this widget — typed by component_type */
  data: Record<string, unknown>;
  /** ECE metadata injected by the backend */
  ece_metadata: ECEComponentMetadata;
  /** Optional error from backend for this specific component */
  error?: string;
}

// ─────────────────────────────────────────────
// 7. RUNTIME PAYLOAD (full backend response for dashboard)
// ─────────────────────────────────────────────

export interface DashboardRuntimePayload {
  dashboard_id: string;
  /** All widgets to be rendered */
  widgets: RuntimeWidget[];
  /** ADE layout metadata for grid positioning */
  ade_layout: ADELayout;
  /** Query that produced this dashboard */
  query: string;
  /** Timestamp when the backend built this payload */
  generated_at: string;
  /** True if this is a Smart Refresh (data only, no layout rebuild) */
  is_smart_refresh: boolean;
  /** Tenant context */
  tenant_id: string;
  /** Backend processing time in ms */
  processing_time_ms: number;
  /** Trust Center, Data Lineage & Status metadata */
  trust_center?: TrustCenterData;
}

// ─────────────────────────────────────────────
// 8. RUNTIME STATE
// ─────────────────────────────────────────────

export type RuntimeStatus =
  | 'idle'
  | 'loading'
  | 'rendering'
  | 'ready'
  | 'refreshing'
  | 'error';

export interface DashboardRuntimeState {
  status: RuntimeStatus;
  payload: DashboardRuntimePayload | null;
  activeBreakpoint: Breakpoint;
  expandedComponentId: string | null;
  activeFilters: Record<string, FilterValue>;
  error: string | null;
  lastRefreshedAt: string | null;
}

// ─────────────────────────────────────────────
// 9. FILTERS & CROSS-FILTER
// ─────────────────────────────────────────────

export type FilterValue = string | number | boolean | null;

export interface CrossFilterEvent {
  sourceComponentId: string;
  filterKey: string;
  filterValue: FilterValue;
}

// ─────────────────────────────────────────────
// 10. INTERACTION EVENTS
// ─────────────────────────────────────────────

export type InteractionType =
  | 'drill_down'
  | 'cross_filter'
  | 'expand'
  | 'collapse'
  | 'export'
  | 'refresh';

export interface InteractionEvent {
  type: InteractionType;
  sourceComponentId: string;
  payload?: Record<string, unknown>;
  timestamp: string;
}

// ─────────────────────────────────────────────
// 11. PERFORMANCE METRICS (client-side)
// ─────────────────────────────────────────────

export interface ClientRenderMetrics {
  totalRenderTimeMs: number;
  visibleComponents: number;
  totalComponents: number;
  fps: number;
  memoryUsageMB?: number;
}

// ─────────────────────────────────────────────
// 12. SSE EVENT (Smart Refresh)
// ─────────────────────────────────────────────

export interface SSERefreshEvent {
  event_type: 'data_refresh' | 'layout_refresh' | 'error';
  dashboard_id: string;
  tenant_id: string;
  widgets?: Partial<RuntimeWidget>[];
  error?: string;
  refreshed_at: string;
}

// ─────────────────────────────────────────────
// 13. COMPONENT REGISTRY ENTRY
// ─────────────────────────────────────────────

export interface ComponentRegistryEntry {
  type: ECEComponentType;
  /** React component to render for this type */
  component: React.ComponentType<Record<string, unknown>>;
  /** Whether this component needs a card wrapper */
  hasWrapper: boolean;
  /** Whether this component is heavy (lazy-load candidate) */
  isHeavy: boolean;
  /** Minimum grid width required */
  minWidth: number;
  /** Minimum grid height required */
  minHeight: number;
}

// ─────────────────────────────────────────────
// 14. TRUST CENTER, LINEAGE & SYSTEM STATUS
// ─────────────────────────────────────────────

export interface TrustBadgeData {
  status: 'VERIFIED' | 'PARTIAL' | 'PENDING';
  origem: string;
  tempo_desde_sync: string;
  proxima_sincronizacao: string | null;
  proxima_sincronizacao_restante: string;
  confidence_score: number;
  health_score: number;
}

export interface DataLineageStep {
  etapa: string;
  nome: string;
  detalhes: string;
  status: string;
}

export interface VersionCenterData {
  view_version: string;
  blueprint_version: string;
  dashboard_template_version: string;
  runtime_dataset_version: string;
  analytical_package_version: string;
  business_layer_version: string;
  metadata_catalog_version: string;
  semantic_catalog_version: string;
  created_at: string;
  updated_at: string;
  compatibility: string;
}

export interface SyncJobData {
  id?: string;
  data?: string;
  hora?: string;
  status?: string;
  registros?: number;
  duracao_ms?: number;
  [key: string]: string | number | boolean | null | undefined;
}

export interface SyncNoticeData {
  type?: string;
  message?: string;
  timestamp?: string;
  [key: string]: string | number | boolean | null | undefined;
}

export interface SyncCenterData {
  ultima_sync: string | null;
  proxima_sync: string | null;
  tempo_desde_sync: string;
  tempo_restante_sync: string;
  horarios_programados: SyncJobData[];
  quantidade_execucoes: number;
  ultimos_erros: SyncNoticeData[];
  ultimos_avisos: SyncNoticeData[];
  status_dados: 'UP_TO_DATE' | 'DEGRADED' | 'OUT_OF_DATE';
}

export interface PerformanceCenterData {
  time_blueprint_ms: number;
  time_backend_ms: number;
  time_runtime_dataset_ms: number;
  time_total_backend_ms: number;
  records_processed: number;
  records_displayed: number;
  components_rendered: number;
  components_reused: number;
}

export interface CacheCenterData {
  blueprint_reused: boolean;
  analytical_package_reused: boolean;
  dashboard_template_reused: boolean;
  runtime_reused: boolean;
  cache_status: 'HIT' | 'MISS';
  last_cache_update: string;
  cache_version: string;
  economia_estimada: string;
}

export interface HealthCenterData {
  scores: Record<string, number>;
  health_geral: number;
}

export interface ConfidenceScoreData {
  score: number;
  stars: number;
  justificativa: string;
}

export interface DiagnosticsData {
  status: 'NORMAL' | 'ATTENTION';
  servico_afetado: string;
  impacto: string;
  causa_provavel: string;
  sugestao_investigacao: string;
}

export interface TimelineStep {
  passo: number;
  etapa: string;
  nome: string;
  tempo: string;
  status: string;
  health: number;
  versao: string;
}

export interface AuditTrailData {
  pergunta: string;
  blueprint_id: string;
  analytical_package_id: string;
  view_name: string;
  runtime_dataset_id: string;
  dashboard_template_id: string;
  tempo_total_ms: number;
  tenant_id: string;
  timestamp: string;
  request_id?: string | null;
}

export interface POPIncidentData {
  type: string;
  actor: string;
  [key: string]: string | number | boolean | null | undefined;
}

export interface POPReportData {
  health_score_geral?: number;
  performance_score?: number;
  avg_latencies_ms?: Partial<Record<'ia' | 'backend' | 'data_platform' | 'cache' | 'scheduler' | 'rendering', number>>;
  system_resources?: {
    cpu_percent?: number;
    memory_mb?: number;
    network_calls_avoided?: number;
  };
  cache_efficiency?: {
    hit_ratio_percent?: number;
    time_saved_ms?: number;
    avoided_ai_calls?: number;
    avoided_queries?: number;
  };
  alerts?: string[];
  warnings?: string[];
  pop_report?: {
    security_score?: number;
    incidents_blocked?: number;
    sessions?: {
      active_tokens?: number;
    };
    recent_incidents?: POPIncidentData[];
  };
}

export interface TrustCenterData {
  trust_badge: TrustBadgeData;
  data_lineage: DataLineageStep[];
  version_center: VersionCenterData;
  sync_center: SyncCenterData;
  performance_center: PerformanceCenterData;
  cache_center: CacheCenterData;
  health_center: HealthCenterData;
  confidence_score: ConfidenceScoreData;
  diagnostics: DiagnosticsData;
  timeline: TimelineStep[];
  audit_trail: AuditTrailData;
  pop_report?: POPReportData;
  ris_audit?: RISAuditData;
}

export interface RISAuditInsight {
  texto?: string;
  classificacao?: string;
  evidencia_numerica?: string | number;
  causalidade?: string;
}

export interface RISAuditRecommendation {
  recomendacao?: string;
  prioridade?: string;
  area_responsavel?: string;
  risco?: string;
  impacto_estimado?: string;
}

export interface RISAuditData {
  trust?: {
    score?: number;
    classification?: string;
  };
  sla?: {
    score?: number;
    tempo_total_ms?: number;
    tokens_utilizados?: number;
  };
  explainability?: {
    explicacao_executiva?: string;
  };
  insights?: RISAuditInsight[];
  recommendations?: RISAuditRecommendation[];
}

// ─────────────────────────────────────────────
// 15. PIPELINE & CONVERSATION GRAPH TYPES
// ─────────────────────────────────────────────

export enum ExecutionStatus {
  READY = 'READY',
  AMBIGUOUS = 'AMBIGUOUS',
  MISSING_INFORMATION = 'MISSING_INFORMATION',
  OUT_OF_SCOPE = 'OUT_OF_SCOPE',
  UNSUPPORTED = 'UNSUPPORTED',
  INVALID = 'INVALID',
  NEEDS_REPLANNING = 'NEEDS_REPLANNING',
}

export enum VisualizationType {
  TABLE = 'TABLE',
  KPI_CARD = 'KPI_CARD',
  BAR = 'BAR',
  LINE = 'LINE',
  PIE = 'PIE',
  DONUT = 'DONUT',
  SCATTER = 'SCATTER',
  HEATMAP = 'HEATMAP',
}

export interface ExecutionResult {
  status: ExecutionStatus;
  dataset: Record<string, unknown>[];
  metadata: Record<string, unknown>;
  warnings: string[];
  execution_time_ms: number;
  row_count: number;
  cache_hit: boolean;
}

export interface DashboardState {
  chart_type: VisualizationType | string;
  selected_chart_id: string | null;
  drilldown_stack: string[];
  hidden_columns: string[];
  visible_metrics: string[];
  selected_filters: Record<string, unknown>;
  pagination_page: number;
  [key: string]: unknown; // Permite extensibilidade para controle de estado visual
}

export interface ConversationNode {
  node_id: string;
  parent_id: string | null;
  children_ids: string[];
  user_query: string;
  execution_result?: ExecutionResult;
  dashboard_state: DashboardState;
}

export interface ConversationGraph {
  nodes: Record<string, ConversationNode>;
  current_node_id: string | null;
}

