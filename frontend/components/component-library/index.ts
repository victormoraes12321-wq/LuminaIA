'use client';

/**
 * ============================================================
 * LUMINA AI — Component Library Registry
 * ============================================================
 * Maps ECEComponentType → React Component.
 * All rendering goes through this registry.
 *
 * Rule: The DashboardRuntimeEngine NEVER imports chart
 * components directly. It always uses the registry.
 * ============================================================
 */

import React, { lazy } from 'react';
import type { ECEComponentType } from '@/types/dashboard-runtime';
import type { ComponentRegistryEntry } from '@/types/dashboard-runtime';

// Import lightweight components eagerly
import { KpiCard } from './kpis/KpiCard';
import { AlertBanner } from './controls/AlertBanner';
import { EmptyState } from './status/StatusComponents';

// Import heavy chart components lazily (all use named exports, not default)
const EBarChart     = lazy(() => import('@/components/charts/EBarChart').then(m => ({ default: m.EBarChart ?? (m as Record<string, unknown>)[Object.keys(m)[0] as string] as React.ComponentType })));
const ELineChart    = lazy(() => import('@/components/charts/ELineChart').then(m => ({ default: m.ELineChart ?? (m as Record<string, unknown>)[Object.keys(m)[0] as string] as React.ComponentType })));
const EAreaChart    = lazy(() => import('@/components/charts/EAreaChart').then(m => ({ default: m.EAreaChart ?? (m as Record<string, unknown>)[Object.keys(m)[0] as string] as React.ComponentType })));
const EPieChart     = lazy(() => import('@/components/charts/EPieChart').then(m => ({ default: m.EPieChart ?? (m as Record<string, unknown>)[Object.keys(m)[0] as string] as React.ComponentType })));
const EScatterChart = lazy(() => import('@/components/charts/EScatterChart').then(m => ({ default: m.EScatterChart ?? (m as Record<string, unknown>)[Object.keys(m)[0] as string] as React.ComponentType })));
const EHeatmapChart = lazy(() => import('@/components/charts/EHeatmapChart').then(m => ({ default: m.EHeatmapChart ?? (m as Record<string, unknown>)[Object.keys(m)[0] as string] as React.ComponentType })));
const ETreemapChart = lazy(() => import('@/components/charts/ETreemapChart').then(m => ({ default: m.ETreemapChart ?? (m as Record<string, unknown>)[Object.keys(m)[0] as string] as React.ComponentType })));
const EFunnelChart  = lazy(() => import('@/components/charts/EFunnelChart').then(m => ({ default: m.EFunnelChart ?? (m as Record<string, unknown>)[Object.keys(m)[0] as string] as React.ComponentType })));
const DataTable     = lazy(() => import('@/components/charts/DataTable').then(m => ({ default: m.DataTable ?? (m as Record<string, unknown>)[Object.keys(m)[0] as string] as React.ComponentType })));
const RankingTable  = lazy(() => import('./tables/RankingTable').then(m => ({ default: m.RankingTable })));

// ─────────────────────────────────────────────
// REGISTRY DEFINITION
// ─────────────────────────────────────────────

const COMPONENT_REGISTRY: Record<ECEComponentType, ComponentRegistryEntry> = {
  KPI_CARD: {
    type: 'KPI_CARD',
    component: KpiCard as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 3,
    minHeight: 2,
  },
  KPI_SPARKLINE: {
    type: 'KPI_SPARKLINE',
    component: KpiCard as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 3,
    minHeight: 2,
  },
  BAR_CHART: {
    type: 'BAR_CHART',
    component: EBarChart as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 4,
    minHeight: 3,
  },
  LINE_CHART: {
    type: 'LINE_CHART',
    component: ELineChart as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 4,
    minHeight: 3,
  },
  AREA_CHART: {
    type: 'AREA_CHART',
    component: EAreaChart as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 4,
    minHeight: 3,
  },
  PIE_CHART: {
    type: 'PIE_CHART',
    component: EPieChart as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 3,
    minHeight: 3,
  },
  DONUT_CHART: {
    type: 'DONUT_CHART',
    component: EPieChart as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 3,
    minHeight: 3,
  },
  SCATTER_CHART: {
    type: 'SCATTER_CHART',
    component: EScatterChart as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: true,
    minWidth: 5,
    minHeight: 4,
  },
  HEATMAP_CHART: {
    type: 'HEATMAP_CHART',
    component: EHeatmapChart as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: true,
    minWidth: 6,
    minHeight: 4,
  },
  TREEMAP_CHART: {
    type: 'TREEMAP_CHART',
    component: ETreemapChart as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: true,
    minWidth: 6,
    minHeight: 4,
  },
  FUNNEL_CHART: {
    type: 'FUNNEL_CHART',
    component: EFunnelChart as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 3,
    minHeight: 4,
  },
  GAUGE_CHART: {
    type: 'GAUGE_CHART',
    // Fallback to EPieChart until EGaugeChart is implemented
    component: EPieChart as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 3,
    minHeight: 3,
  },
  DATA_TABLE: {
    type: 'DATA_TABLE',
    component: DataTable as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: true,
    minWidth: 6,
    minHeight: 4,
  },
  RANKING_TABLE: {
    type: 'RANKING_TABLE',
    component: RankingTable as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 3,
    minHeight: 4,
  },
  ALERT_BANNER: {
    type: 'ALERT_BANNER',
    component: AlertBanner as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: false,
    isHeavy: false,
    minWidth: 12,
    minHeight: 1,
  },
  FILTER_PANEL: {
    type: 'FILTER_PANEL',
    component: EmptyState as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: false,
    isHeavy: false,
    minWidth: 12,
    minHeight: 2,
  },
  TEXT_BLOCK: {
    type: 'TEXT_BLOCK',
    component: EmptyState as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: true,
    isHeavy: false,
    minWidth: 4,
    minHeight: 2,
  },
  DIVIDER: {
    type: 'DIVIDER',
    component: EmptyState as unknown as React.ComponentType<Record<string, unknown>>,
    hasWrapper: false,
    isHeavy: false,
    minWidth: 12,
    minHeight: 1,
  },
};

// ─────────────────────────────────────────────
// REGISTRY API
// ─────────────────────────────────────────────

export function getRegistryEntry(
  type: ECEComponentType,
): ComponentRegistryEntry | null {
  return COMPONENT_REGISTRY[type] ?? null;
}

export function getRegisteredTypes(): ECEComponentType[] {
  return Object.keys(COMPONENT_REGISTRY) as ECEComponentType[];
}

export function isRegisteredType(type: string): type is ECEComponentType {
  return type in COMPONENT_REGISTRY;
}

export { COMPONENT_REGISTRY };
