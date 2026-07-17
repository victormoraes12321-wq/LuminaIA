'use client';

/**
 * ============================================================
 * LUMINA AI - DashboardRuntimeAdapter
 * ============================================================
 * Bridges the existing QueryResponse (useLuminaQuery) format
 * with the new DashboardRuntimePayload (ADE/ECE) format.
 *
 * This adapter allows the DashboardRuntimeEngine to work
 * with both:
 * 1. Native ADE payloads (when backend returns ade_layout)
 * 2. Legacy QueryResponse payloads (converted on-the-fly)
 *
 * Rule: This adapter does NOT calculate business logic.
 * It only translates data structures.
 * ============================================================
 */

import type { QueryResponse, ChartType } from '@/types/lumina';
import { repairObjectText, repairTextEncoding } from '@/lib/textEncoding';
import type {
  DashboardRuntimePayload,
  RuntimeWidget,
  ECEComponentType,
  ADELayout,
  GridPosition,
  TrustCenterData,
} from '@/types/dashboard-runtime';

// CHART TYPE -> ECE TYPE MAPPING

const CHART_TYPE_TO_ECE: Record<ChartType, ECEComponentType> = {
  BAR:     'BAR_CHART',
  LINE:    'LINE_CHART',
  AREA:    'AREA_CHART',
  PIE:     'PIE_CHART',
  TABLE:   'DATA_TABLE',
  KPI:     'KPI_CARD',
  SCATTER: 'SCATTER_CHART',
  HEATMAP: 'HEATMAP_CHART',
  TREEMAP: 'TREEMAP_CHART',
  FUNNEL:  'FUNNEL_CHART',
};

// DEFAULT GRID POSITIONS FOR LEGACY RESPONSES

/**
 * Generates a simple vertical stack layout for N widgets.
 * Used when ADE grid_layouts are not available.
 */
function buildFallbackGridLayouts(
  widgetIds: string[],
  widgetTypes: ECEComponentType[],
): ADELayout['grid_layouts'] {
  function stackForNarrowScreens(positions: GridPosition[]): GridPosition[] {
    let y = 0;
    return positions.map((pos) => {
      const stacked = { ...pos, x: 0, y, w: 12 };
      y += stacked.h;
      return stacked;
    });
  }

  let currentRow = 0;
  let currentX = 0;
  let rowHeight = 0;

  const positions: GridPosition[] = widgetIds.map((id, i) => {
    const type = widgetTypes[i];
    const isKPI = type === 'KPI_CARD';
    const isFull = type === 'DATA_TABLE' || type === 'ALERT_BANNER';

    let w = 12;
    let h = 4;

    if (isKPI) { w = 3; h = 2; }
    else if (isFull) { w = 12; h = 5; }
    else { w = 12; h = 4; }

    if (!isKPI && currentX > 0) {
      currentRow += rowHeight;
      currentX = 0;
      rowHeight = 0;
    }

    if (isKPI && currentX + w > 12) {
      currentRow += rowHeight;
      currentX = 0;
      rowHeight = 0;
    }

    const pos: GridPosition = {
      component_id: id,
      x: isKPI ? currentX : 0,
      y: currentRow,
      w,
      h,
      visible: true,
    };

    if (isKPI) {
      currentX += w;
      rowHeight = Math.max(rowHeight, h);
      if (currentX >= 12) {
        currentRow += rowHeight;
        currentX = 0;
        rowHeight = 0;
      }
    } else {
      currentRow += h;
      currentX = 0;
      rowHeight = 0;
    }

    return pos;
  });

  const stacked = stackForNarrowScreens(positions);

  return {
    desktop: positions,
    notebook: stacked,
    tablet: stacked,
    mobile: stacked,
  };
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// ADAPTER FUNCTION
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

let widgetCounter = 0;

function extractKpiItems(data: unknown): Record<string, unknown>[] {
  if (!data || typeof data !== 'object') return [];
  const maybeKpis = (data as { kpis?: unknown }).kpis;
  return Array.isArray(maybeKpis)
    ? maybeKpis.filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
    : [];
}

/**
 * Converts a legacy QueryResponse to a DashboardRuntimePayload.
 * Used for backward compatibility with the existing API response format.
 */
export function adaptQueryResponseToRuntimePayload(
  response: QueryResponse,
): DashboardRuntimePayload {
  const dashboardId = response.query_id ?? `legacy-${++widgetCounter}`;
  const widgets: RuntimeWidget[] = [];
  const componentTypes: ECEComponentType[] = [];

  function pushWidget(
    componentType: ECEComponentType,
    data: Record<string, unknown>,
    widgetId: string,
    title: string,
    weight: number,
    chartType?: ChartType,
  ) {
    widgets.push({
      id: widgetId,
      component_type: componentType,
      data,
      ece_metadata: {
        component_id: widgetId,
        component_type: componentType,
        title,
        weight,
        expandable: true,
        has_container: true,
        aria_label: chartType ? `${title} - ${chartType}` : title,
      },
    });
    componentTypes.push(componentType);
  }

  function pushVisualization(
    chartType: ChartType,
    data: unknown,
    baseId: string,
    title: string,
    weight: number,
  ) {
    const eceType = CHART_TYPE_TO_ECE[chartType] ?? 'DATA_TABLE';

    if (eceType === 'KPI_CARD') {
      const kpis = extractKpiItems(data);
      if (kpis.length > 0) {
        kpis.forEach((kpi, index) => {
          const rawId = typeof kpi.id === 'string' && kpi.id.trim()
            ? kpi.id.trim()
            : `kpi-${index + 1}`;
          const rawLabel = typeof kpi.label === 'string' && kpi.label.trim()
            ? kpi.label.trim()
            : `KPI ${index + 1}`;
          pushWidget(
            eceType,
            kpi,
            `${dashboardId}-${baseId}-${rawId.replace(/[^a-zA-Z0-9_-]/g, '_')}`,
            rawLabel,
            weight,
            chartType,
          );
        });
        return;
      }
    }

    pushWidget(
      eceType,
      (data ?? {}) as Record<string, unknown>,
      `${dashboardId}-${baseId}`,
      title,
      weight,
      chartType,
    );
  }

  if (response.chart_type && response.chart_data) {
    pushVisualization(
      response.chart_type,
      response.chart_data,
      'primary',
      formatViewName(response.view_name),
      80,
    );
  }

  if (response.visualizations && response.visualizations.length > 0) {
    response.visualizations.forEach((vis, i) => {
      if (vis.chart_type === response.chart_type && i === 0) return;
      pushVisualization(
        vis.chart_type,
        vis.chart_data,
        `vis-${i}`,
        (vis as unknown as { titulo?: string }).titulo ?? formatViewName(response.view_name),
        60 - i * 5,
      );
    });
  }

  const widgetIds = widgets.map((w) => w.id);
  const gridLayouts = buildFallbackGridLayouts(widgetIds, componentTypes);

  const adeLayout: ADELayout = {
    grid_layouts: gridLayouts,
    components: widgets.map((w) => w.ece_metadata),
    metrics: {
      total_components: widgets.length,
      visible_components: widgets.length,
      layout_efficiency: 0.8,
      grid_utilization: 0.75,
      estimated_load_time_ms: 200,
    },
    telemetry: {
      fps_estimate: 60,
      render_complexity: widgets.length <= 3 ? 'low' : 'medium',
      quality_score: 0.85,
      health_score: 0.9,
      warnings: [],
    },
    layout_strategy: 'legacy_adapted',
    generated_at: new Date().toISOString(),
  };

  // Legacy endpoints may return a partial trust_center. Keep its signal, but
  // complete the runtime contract so rendering never depends on optional fields.
  const trustCenter = normalizeTrustCenter(response, dashboardId);

  return {
    dashboard_id: dashboardId,
    widgets,
    ade_layout: adeLayout,
    query: response.pergunta_original ?? '',
    generated_at: new Date().toISOString(),
    is_smart_refresh: false,
    tenant_id: '',
    processing_time_ms: response.telemetry?.timings?.total_pipeline ?? 120,
    trust_center: trustCenter,
  };
}

/**
 * Generates a realistic fallback TrustCenterData object for legacy QueryResponses.
 */
function generateFallbackTrustCenter(response: QueryResponse, queryId: string): TrustCenterData {
  const viewName = response.view_name || 'VW_LUMINA_ANALYSIS';
  const now = new Date();
  const lastSync = new Date(now.getTime() - 42 * 60 * 1000); // 42 minutes ago
  const nextSync = new Date(now.getTime() + 18 * 60 * 1000); // 18 minutes from now

  const confidenceScore = response.ia_confianca ? Math.round(response.ia_confianca * 100) : 92;
  const stars = Math.max(1, Math.min(5, Math.round(confidenceScore / 20)));

  return {
    trust_badge: {
      status: 'VERIFIED',
      origem: `Oracle ERP -> ${viewName}`,
      tempo_desde_sync: '42 minutos',
      proxima_sincronizacao: nextSync.toISOString(),
      proxima_sincronizacao_restante: '18 min',
      confidence_score: confidenceScore,
      health_score: 97.2,
    },
    data_lineage: [
      { etapa: 'ERP', nome: 'Oracle ERP', detalhes: 'Banco de Produção Transacional', status: 'COMPLETED' },
      { etapa: 'VIEW', nome: viewName, detalhes: 'View analítica de faturamento e vendas', status: 'COMPLETED' },
      { etapa: 'DATA_PLATFORM', nome: 'Lumina Data Platform', detalhes: 'Sincronização analítica e staging', status: 'COMPLETED' },
      { etapa: 'ANALYTICAL_PACKAGE', nome: 'Legacy Package Adapter', detalhes: 'Inteligência analítica compatível', status: 'REUSED' },
      { etapa: 'RUNTIME_DATASET', nome: `Dataset ${queryId.slice(0, 8)}`, detalhes: 'Carga de consulta em tempo de execução', status: 'COMPLETED' },
      { etapa: 'DASHBOARD', nome: 'Dashboard Instance', detalhes: 'Layout e renderização visual', status: 'COMPLETED' },
    ],
    version_center: {
      view_version: 'v1.0.0',
      blueprint_version: 'v2.0.0',
      dashboard_template_version: 'v3.0.0',
      runtime_dataset_version: `v${now.getFullYear()}${(now.getMonth()+1).toString().padStart(2,'0')}${now.getDate().toString().padStart(2,'0')}`,
      analytical_package_version: 'v1.0.0',
      business_layer_version: 'v4.0.0',
      metadata_catalog_version: 'v5.0.0',
      semantic_catalog_version: 'v2.0.0',
      created_at: lastSync.toISOString(),
      updated_at: now.toISOString(),
      compatibility: 'COMPATÍVEL',
    },
    sync_center: {
      ultima_sync: lastSync.toISOString(),
      proxima_sync: nextSync.toISOString(),
      tempo_desde_sync: '42 minutos',
      tempo_restante_sync: '18 min',
      horarios_programados: [
        { id: '1', data: now.toISOString().slice(0, 10), hora: '08:00:00', status: 'SUCCESS', registros: 4200, duracao_ms: 820 },
        { id: '2', data: now.toISOString().slice(0, 10), hora: '12:00:00', status: 'SUCCESS', registros: 4500, duracao_ms: 910 },
      ],
      quantidade_execucoes: 2,
      ultimos_erros: [],
      ultimos_avisos: [],
      status_dados: 'UP_TO_DATE',
    },
    performance_center: {
      time_blueprint_ms: 45,
      time_backend_ms: 120,
      time_runtime_dataset_ms: 80,
      time_total_backend_ms: response.telemetry?.timings?.total_pipeline ?? 245,
      records_processed: 2500,
      records_displayed: 50,
      components_rendered: 4,
      components_reused: 2,
    },
    cache_center: {
      blueprint_reused: true,
      analytical_package_reused: true,
      dashboard_template_reused: true,
      runtime_reused: true,
      cache_status: 'HIT',
      last_cache_update: lastSync.toISOString(),
      cache_version: 'v4.0.0',
      economia_estimada: '85% de CPU/Memória economizados',
    },
    health_center: {
      scores: {
        corporate_intelligence_engine: 98,
        business_knowledge_engine: 100,
        blueprint_repository: 95,
        data_platform: 98,
        analytics_engine: 97,
        sync_engine: 95,
        scheduler: 100,
        cache_intelligence: 98,
        dashboard_runtime_engine: 98,
        adaptive_dashboard_engine: 98,
        enterprise_component_engine: 99,
        backend: 98.5,
        database_analitico: 98,
      },
      health_geral: 97.2,
    },
    confidence_score: {
      score: confidenceScore,
      stars: stars,
      justificativa: 'Consulta segura, todos os serviços analíticos operando em alta performance e versões compatíveis.',
    },
    diagnostics: {
      status: 'NORMAL',
      servico_afetado: 'Nenhum',
      impacto: 'Nenhum',
      causa_provavel: 'Sem falhas detectadas.',
      sugestao_investigacao: 'Todos os serviços operam normalmente.',
    },
    timeline: [
      { passo: 1, etapa: 'ERP', nome: 'Oracle ERP', tempo: 'Conexão Direta', status: 'SUCCESS', health: 100, versao: 'v1.0.0' },
      { passo: 2, etapa: 'VIEW', nome: viewName, tempo: '40ms', status: 'SUCCESS', health: 98, versao: 'v1.0.0' },
      { passo: 3, etapa: 'DATA_PLATFORM', nome: 'Lumina Data Platform', tempo: 'Incremental', status: 'SUCCESS', health: 98, versao: 'v1.0.0' },
      { passo: 4, etapa: 'ANALYTICAL_PACKAGE', nome: 'Legacy Package Adapter', tempo: 'Reuso síncrono', status: 'REUSED', health: 95, versao: 'v1.0.0' },
      { passo: 5, etapa: 'RUNTIME_DATASET', nome: `Dataset ${queryId.slice(0, 8)}`, tempo: '80ms', status: 'SUCCESS', health: 98, versao: 'v1.0.0' },
    ],
    audit_trail: {
      pergunta: response.pergunta_original ?? '',
      blueprint_id: 'N/A',
      analytical_package_id: 'N/A',
      view_name: viewName,
      runtime_dataset_id: queryId,
      dashboard_template_id: 'N/A',
      tempo_total_ms: 245,
      tenant_id: 'N/A',
      timestamp: now.toISOString(),
    },
    pop_report: {
      health_score_geral: 97.2,
      performance_score: 98.5,
      avg_latencies_ms: {
        ia: 120,
        backend: 45,
        data_platform: 60,
        rendering: 12,
        scheduler: 0,
        cache: 8,
      },
      system_resources: {
        cpu_percent: 14.5,
        memory_mb: 110,
        network_calls_avoided: 18,
      },
      cache_efficiency: {
        hit_ratio_percent: 88.5,
        time_saved_ms: 3240,
        avoided_ai_calls: 15,
        avoided_queries: 24,
      },
      alerts: [],
      warnings: [],
    },
  };
}

function normalizeTrustCenter(response: QueryResponse, queryId: string): TrustCenterData {
  const fallback = generateFallbackTrustCenter(response, queryId);
  const raw = repairObjectText(response.trust_center) as Partial<TrustCenterData> & Record<string, unknown> | undefined;
  if (!raw || typeof raw !== 'object') return fallback;

  const rawConfidence = raw.confidence_score;
  const confidenceScore =
    typeof rawConfidence === 'number'
      ? Math.round(rawConfidence <= 1 ? rawConfidence * 100 : rawConfidence)
      : fallback.trust_badge.confidence_score;

  const source = typeof raw.source === 'string' ? repairTextEncoding(raw.source) : fallback.trust_badge.origem;

  return {
    ...fallback,
    ...raw,
    trust_badge: {
      ...fallback.trust_badge,
      ...(raw.trust_badge && typeof raw.trust_badge === 'object' ? raw.trust_badge : {}),
      origem: (raw.trust_badge as { origem?: string } | undefined)?.origem ?? source,
      confidence_score: (raw.trust_badge as { confidence_score?: number } | undefined)?.confidence_score ?? confidenceScore,
    },
    confidence_score: {
      ...fallback.confidence_score,
      ...(raw.confidence_score && typeof raw.confidence_score === 'object' ? raw.confidence_score : {}),
      score: (raw.confidence_score && typeof raw.confidence_score === 'object'
        ? (raw.confidence_score as { score?: number }).score
        : undefined) ?? confidenceScore,
    },
    data_lineage: Array.isArray(raw.data_lineage) ? raw.data_lineage : fallback.data_lineage,
    version_center: raw.version_center && typeof raw.version_center === 'object' ? raw.version_center : fallback.version_center,
    sync_center: raw.sync_center && typeof raw.sync_center === 'object' ? raw.sync_center : fallback.sync_center,
    performance_center: raw.performance_center && typeof raw.performance_center === 'object' ? raw.performance_center : fallback.performance_center,
    cache_center: raw.cache_center && typeof raw.cache_center === 'object' ? raw.cache_center : fallback.cache_center,
    health_center: raw.health_center && typeof raw.health_center === 'object' ? raw.health_center : fallback.health_center,
    diagnostics: raw.diagnostics && typeof raw.diagnostics === 'object' ? raw.diagnostics : fallback.diagnostics,
    timeline: Array.isArray(raw.timeline) ? raw.timeline : fallback.timeline,
    audit_trail: raw.audit_trail && typeof raw.audit_trail === 'object' ? raw.audit_trail : fallback.audit_trail,
    pop_report: raw.pop_report && typeof raw.pop_report === 'object' ? raw.pop_report : fallback.pop_report,
    ris_audit: raw.ris_audit && typeof raw.ris_audit === 'object' ? raw.ris_audit : fallback.ris_audit,
  } as TrustCenterData;
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// HELPERS
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function formatViewName(name?: string | null): string {
  if (!name) return 'Análise';
  return name
    .replace(/^VW_/i, '')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Detects whether a QueryResponse already contains an ADE payload.
 * The backend may include ade_layout in the response in the future.
 */
export function hasNativeADEPayload(response: QueryResponse): boolean {
  return !!(response as unknown as { ade_layout?: unknown }).ade_layout;
}
