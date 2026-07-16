/**
 * ============================================================
 * LUMINA AI — Layout Intelligence Engine (Pure TypeScript)
 * ============================================================
 * Provides priority scoring, ordering, and weighting logic
 * for dashboard components — based purely on ECE metadata.
 *
 * Rule: NO business logic. Only visual priority computation.
 * ============================================================
 */

import type { ECEComponentMetadata, ECEComponentType } from '@/types/dashboard-runtime';

// ─────────────────────────────────────────────
// COMPONENT VISUAL PRIORITY TABLE
// ─────────────────────────────────────────────

/**
 * Default visual priority score per component type.
 * Higher = rendered earlier / given more prominent position.
 */
const COMPONENT_PRIORITY: Record<ECEComponentType, number> = {
  KPI_CARD:       100,
  KPI_SPARKLINE:  90,
  ALERT_BANNER:   95,
  BAR_CHART:      80,
  LINE_CHART:     78,
  AREA_CHART:     76,
  PIE_CHART:      74,
  DONUT_CHART:    72,
  GAUGE_CHART:    70,
  SCATTER_CHART:  65,
  HEATMAP_CHART:  60,
  TREEMAP_CHART:  58,
  FUNNEL_CHART:   55,
  RANKING_TABLE:  70,
  DATA_TABLE:     50,
  FILTER_PANEL:   85,
  TEXT_BLOCK:     30,
  DIVIDER:        10,
};

/**
 * Returns the visual priority score for a component.
 * Combines the type baseline with the backend's weight field.
 */
export function computeComponentPriority(meta: ECEComponentMetadata): number {
  const typePriority = COMPONENT_PRIORITY[meta.component_type] ?? 50;
  // Backend weight is 0–100; blend 50% type + 50% backend weight
  return Math.round(typePriority * 0.5 + meta.weight * 0.5);
}

// ─────────────────────────────────────────────
// RENDERING ORDER
// ─────────────────────────────────────────────

/**
 * Sorts component metadata by descending visual priority.
 * Used to determine render order when grid positions are equal.
 */
export function sortByPriority(
  components: ECEComponentMetadata[],
): ECEComponentMetadata[] {
  return [...components].sort(
    (a, b) => computeComponentPriority(b) - computeComponentPriority(a),
  );
}

// ─────────────────────────────────────────────
// COMPONENT SIZE RECOMMENDATIONS
// ─────────────────────────────────────────────

export type RecommendedSize = {
  cols: { desktop: number; tablet: number; mobile: number };
  rows: number;
};

const COMPONENT_SIZE_RECOMMENDATIONS: Record<ECEComponentType, RecommendedSize> = {
  KPI_CARD:       { cols: { desktop: 3,  tablet: 6,  mobile: 12 }, rows: 2 },
  KPI_SPARKLINE:  { cols: { desktop: 3,  tablet: 6,  mobile: 12 }, rows: 2 },
  ALERT_BANNER:   { cols: { desktop: 12, tablet: 12, mobile: 12 }, rows: 1 },
  BAR_CHART:      { cols: { desktop: 6,  tablet: 12, mobile: 12 }, rows: 4 },
  LINE_CHART:     { cols: { desktop: 6,  tablet: 12, mobile: 12 }, rows: 4 },
  AREA_CHART:     { cols: { desktop: 6,  tablet: 12, mobile: 12 }, rows: 4 },
  PIE_CHART:      { cols: { desktop: 4,  tablet: 6,  mobile: 12 }, rows: 4 },
  DONUT_CHART:    { cols: { desktop: 4,  tablet: 6,  mobile: 12 }, rows: 4 },
  GAUGE_CHART:    { cols: { desktop: 3,  tablet: 6,  mobile: 12 }, rows: 3 },
  SCATTER_CHART:  { cols: { desktop: 6,  tablet: 12, mobile: 12 }, rows: 4 },
  HEATMAP_CHART:  { cols: { desktop: 8,  tablet: 12, mobile: 12 }, rows: 5 },
  TREEMAP_CHART:  { cols: { desktop: 8,  tablet: 12, mobile: 12 }, rows: 5 },
  FUNNEL_CHART:   { cols: { desktop: 4,  tablet: 6,  mobile: 12 }, rows: 5 },
  RANKING_TABLE:  { cols: { desktop: 4,  tablet: 12, mobile: 12 }, rows: 5 },
  DATA_TABLE:     { cols: { desktop: 12, tablet: 12, mobile: 12 }, rows: 5 },
  FILTER_PANEL:   { cols: { desktop: 12, tablet: 12, mobile: 12 }, rows: 2 },
  TEXT_BLOCK:     { cols: { desktop: 6,  tablet: 12, mobile: 12 }, rows: 2 },
  DIVIDER:        { cols: { desktop: 12, tablet: 12, mobile: 12 }, rows: 1 },
};

/**
 * Returns the recommended size for a component type.
 */
export function getRecommendedSize(type: ECEComponentType): RecommendedSize {
  return COMPONENT_SIZE_RECOMMENDATIONS[type] ?? {
    cols: { desktop: 6, tablet: 12, mobile: 12 },
    rows: 4,
  };
}

// ─────────────────────────────────────────────
// HEAVY COMPONENT DETECTION
// ─────────────────────────────────────────────

/**
 * Heavy components benefit from lazy loading.
 */
const HEAVY_COMPONENT_TYPES: Set<ECEComponentType> = new Set([
  'HEATMAP_CHART',
  'TREEMAP_CHART',
  'SCATTER_CHART',
  'DATA_TABLE',
]);

export function isHeavyComponent(type: ECEComponentType): boolean {
  return HEAVY_COMPONENT_TYPES.has(type);
}

// ─────────────────────────────────────────────
// CARD WRAPPER DETECTION
// ─────────────────────────────────────────────

/**
 * Components that should NOT have a card wrapper around them.
 */
const NO_WRAPPER_TYPES: Set<ECEComponentType> = new Set([
  'DIVIDER',
  'ALERT_BANNER',
]);

export function needsCardWrapper(type: ECEComponentType): boolean {
  return !NO_WRAPPER_TYPES.has(type);
}

// ─────────────────────────────────────────────
// LAYOUT STRATEGY LABELS
// ─────────────────────────────────────────────

export type LayoutStrategy =
  | 'kpi_first'
  | 'chart_dominant'
  | 'table_focus'
  | 'mixed'
  | 'single'
  | 'empty';

/**
 * Infers a layout strategy from the list of component types
 * (used for fallback rendering when ADE layout is not available).
 */
export function inferLayoutStrategy(
  types: ECEComponentType[],
): LayoutStrategy {
  if (types.length === 0) return 'empty';
  if (types.length === 1) return 'single';

  const kpiCount = types.filter((t) => t === 'KPI_CARD' || t === 'KPI_SPARKLINE').length;
  const chartCount = types.filter((t) =>
    ['BAR_CHART', 'LINE_CHART', 'AREA_CHART', 'PIE_CHART', 'DONUT_CHART', 'SCATTER_CHART', 'GAUGE_CHART', 'HEATMAP_CHART', 'TREEMAP_CHART', 'FUNNEL_CHART'].includes(t),
  ).length;
  const tableCount = types.filter((t) => t === 'DATA_TABLE' || t === 'RANKING_TABLE').length;

  if (kpiCount >= types.length * 0.5) return 'kpi_first';
  if (tableCount >= types.length * 0.5) return 'table_focus';
  if (chartCount >= types.length * 0.5) return 'chart_dominant';
  return 'mixed';
}
