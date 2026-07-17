'use client';

/**
 * ============================================================
 * LUMINA AI - Dashboard Runtime Engine
 * ============================================================
 * THE central orchestrator for the entire dashboard rendering
 * pipeline.
 *
 * Responsibilities:
 * - Accepts a DashboardRuntimePayload (from backend ADE/ECE)
 * - Renders widgets on a responsive 12-column CSS Grid
 * - Manages fullscreen expansion state
 * - Shows loading skeleton / error states
 * - Exposes Smart Refresh indicator (SSE)
 * - Wraps in CrossFilterProvider for cross-component filtering
 * - Emits performance metrics in development
 *
 * Rule: NEVER calculates business logic.
 * Rule: NEVER queries the database directly.
 * Rule: NEVER rebuilds analytical intelligence.
 * ============================================================
 */

import React, { memo, useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Wifi, WifiOff, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DashboardRuntimePayload } from '@/types/dashboard-runtime';
import { GridEngine } from './GridEngine';
import { FullscreenManager } from '@/components/interaction-engine/FullscreenManager';
import { CrossFilterProvider, ActiveFiltersBar } from '@/components/interaction-engine/CrossFilterManager';
import {
  SkeletonGrid,
  ErrorState,
} from '@/components/component-library/status/StatusComponents';
import { useDashboardRuntime } from '@/hooks/useDashboardRuntime';
import { usePerformanceMonitor } from '@/hooks/usePerformanceMonitor';
import { TrustCenterPanel } from './TrustCenterPanel';

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// TYPES
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface DashboardRuntimeEngineProps {
  /** Pre-loaded payload (e.g., from useLuminaQuery response) */
  payload?: DashboardRuntimePayload | null;
  /** Dashboard ID for fetching (alternative to payload) */
  dashboardId?: string;
  /** Auth token */
  token: string | null;
  /** Tenant ID */
  tenantId: string | null;
  /** Enable Server-Sent Events for Smart Refresh */
  enableSSE?: boolean;
  /** Extra class for the root element */
  className?: string;
  /** Called after the dashboard is fully rendered */
  onReady?: () => void;
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// SSE STATUS INDICATOR
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function SSEIndicator({ connected }: { connected: boolean }) {
  return (
    <div
      className={cn(
        'flex items-center gap-1.5 rounded-full px-2 py-1 text-[10px] font-medium',
        connected
          ? 'bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/25'
          : 'border',
      )}
      style={connected ? undefined : {
        background: 'rgb(var(--bg-elevated) / 0.65)',
        borderColor: 'rgb(var(--border) / 0.55)',
        color: 'rgb(var(--text-muted))',
      }}
      title={connected ? 'Atualização automática ativa' : 'Atualização automática desconectada'}
      aria-label={connected ? 'Conexão ativa' : 'Conexão inativa'}
    >
      {connected
        ? <Wifi className="h-2.5 w-2.5" />
        : <WifiOff className="h-2.5 w-2.5" />}
      {connected ? 'Ao vivo' : 'Offline'}
    </div>
  );
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// DASHBOARD HEADER (meta info + actions)
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface DashboardHeaderProps {
  payload: DashboardRuntimePayload;
  sseConnected: boolean;
  isRefreshing: boolean;
  onReload: () => void;
  onOpenTrustCenter: () => void;
}

function DashboardHeader({
  payload,
  sseConnected,
  isRefreshing,
  onReload,
  onOpenTrustCenter,
}: DashboardHeaderProps) {
  const { telemetry } = payload.ade_layout;
  const qualityPct = Math.round(telemetry.quality_score * 100);

  const statusColors = {
    VERIFIED: 'text-green-400 hover:border-green-500/30',
    PARTIAL: 'text-amber-400 hover:border-amber-500/30',
    PENDING: 'text-red-400 hover:border-red-500/30',
  };

  const badgeStatus = payload.trust_center?.trust_badge?.status || 'VERIFIED';
  const colorClass = statusColors[badgeStatus];

  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 shrink-0 border-b pb-4"
      style={{ borderColor: 'rgb(var(--border) / 0.45)' }}
    >
      <div className="flex items-center gap-3 flex-wrap min-w-0">
        <SSEIndicator connected={sseConnected} />
        {isRefreshing && (
          <div className="flex items-center gap-1.5 text-[10px] text-[#6C63FF]">
            <RefreshCw className="h-2.5 w-2.5 animate-spin" />
            Atualizando...
          </div>
        )}
        
        {/* Trust Badge */}
        {payload.trust_center && (
          <button
            onClick={onOpenTrustCenter}
            className="flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold border transition-all cursor-pointer"
            style={{
              background: 'rgb(var(--bg-elevated) / 0.55)',
              borderColor: 'rgb(var(--border) / 0.55)',
            }}
            title="Clique para ver a Linhagem de Dados e Status do Sistema"
          >
            <ShieldCheck className={cn("h-3.5 w-3.5 shrink-0", colorClass)} />
            <span style={{ color: 'rgb(var(--text-primary))' }}>Confiança: {payload.trust_center.confidence_score.score}%</span>
            <span style={{ color: 'rgb(var(--text-muted))' }}>|</span>
            <span className="truncate hidden sm:inline" style={{ color: 'rgb(var(--text-secondary))' }}>{payload.trust_center.trust_badge.origem}</span>
          </button>
        )}

        {/* Quality badge in dev */}
        {process.env.NODE_ENV === 'development' && (
          <span className="text-[10px]" style={{ color: 'rgb(var(--text-muted))' }}>
            Q:{qualityPct}% | {payload.ade_layout.layout_strategy} | {payload.processing_time_ms}ms
          </span>
        )}
      </div>

      <button
        onClick={onReload}
        disabled={isRefreshing}
        className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs self-end sm:self-auto transition-all disabled:opacity-30 cursor-pointer"
        style={{ color: 'rgb(var(--text-secondary))' }}
        aria-label="Recarregar dashboard"
      >
        <RefreshCw className={cn('h-3 w-3', isRefreshing && 'animate-spin')} />
        Recarregar
      </button>
    </div>
  );
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// MAIN COMPONENT
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export const DashboardRuntimeEngine = memo(function DashboardRuntimeEngine({
  payload: externalPayload,
  dashboardId,
  token,
  tenantId,
  enableSSE = true,
  className,
  onReady,
}: DashboardRuntimeEngineProps) {
  const { state, fetchDashboard, reloadDashboard, expandComponent, sseConnected } =
    useDashboardRuntime({ token, tenantId, enableSSE });

  const { recordRender } = usePerformanceMonitor();

  const [isTrustCenterOpen, setIsTrustCenterOpen] = useState(false);

  // Use external payload if provided, else fetch by ID
  const payload = externalPayload ?? state.payload;
  const status = externalPayload ? 'ready' : state.status;
  const error = state.error;

  useEffect(() => {
    if (dashboardId && !externalPayload) {
      fetchDashboard(dashboardId);
    }
  }, [dashboardId, externalPayload, fetchDashboard]);

  useEffect(() => {
    if (status === 'ready' && payload) {
      recordRender(
        'DashboardRuntimeEngine',
        payload.ade_layout.metrics.visible_components,
        payload.ade_layout.metrics.total_components,
      );
      onReady?.();
    }
  }, [onReady, payload, recordRender, status]);

  // â”€â”€ Loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  if (status === 'loading' || status === 'idle') {
    return (
      <div className={cn('w-full', className)}>
        <SkeletonGrid count={8} />
      </div>
    );
  }

  // â”€â”€ Error â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  if (status === 'error' || !payload) {
    return (
      <div className={cn('w-full flex items-center justify-center min-h-64', className)}>
        <ErrorState
          title="Erro ao carregar dashboard"
          message={error ?? 'Tente novamente.'}
          onRetry={() => dashboardId ? fetchDashboard(dashboardId) : reloadDashboard()}
          className="max-w-md w-full"
        />
      </div>
    );
  }

  // â”€â”€ Ready â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  const isRefreshing = status === 'refreshing';

  const expandedWidget = state.expandedComponentId
    ? payload.widgets.find((w) => w.id === state.expandedComponentId)
    : null;

  return (
    <CrossFilterProvider>
      <div
        className={cn('lumina-runtime-theme-scope flex flex-col w-full min-h-0', className)}
        role="main"
        aria-label="Dashboard Analytics"
      >
        {/* Header */}
        <DashboardHeader
          payload={payload}
          sseConnected={sseConnected}
          isRefreshing={isRefreshing}
          onReload={reloadDashboard}
          onOpenTrustCenter={() => setIsTrustCenterOpen(true)}
        />

        {/* Active Cross-Filters */}
        <ActiveFiltersBar className="mb-4" />

        {/* Grid */}
        <GridEngine
          widgets={payload.widgets}
          gridLayouts={payload.ade_layout.grid_layouts}
          expandedComponentId={state.expandedComponentId}
          onExpand={expandComponent}
          isRefreshing={isRefreshing}
        />

        {/* Fullscreen overlay */}
        <AnimatePresence>
          {expandedWidget && (
            <FullscreenManager
              key="fullscreen"
              componentId={state.expandedComponentId}
              title={expandedWidget.ece_metadata.title}
              onClose={() => expandComponent(null)}
            >
              <GridEngine
                widgets={[expandedWidget]}
                gridLayouts={{
                  desktop: [{
                    component_id: expandedWidget.id,
                    x: 0, y: 0, w: 12, h: 8, visible: true,
                  }],
                }}
                expandedComponentId={null}
                onExpand={() => {}}
              />
            </FullscreenManager>
          )}
        </AnimatePresence>

        {/* Trust Center Slide-over Drawer */}
        <AnimatePresence>
          {isTrustCenterOpen && payload.trust_center && (
            <>
              {/* Backdrop */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.5 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs"
                onClick={() => setIsTrustCenterOpen(false)}
              />
              {/* Drawer Container */}
              <motion.div
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="fixed inset-y-0 right-0 z-50 w-full max-w-2xl border-l shadow-2xl overflow-y-auto"
                style={{
                  background: 'rgb(var(--bg-surface) / 0.96)',
                  borderColor: 'rgb(var(--border) / 0.7)',
                }}
                role="dialog"
                aria-modal="true"
                aria-label="Trust Center"
              >
                {/* Drawer Header */}
                <div
                  className="flex items-center justify-between px-6 py-4 border-b sticky top-0 backdrop-blur-md z-10"
                  style={{
                    background: 'rgb(var(--bg-surface) / 0.85)',
                    borderColor: 'rgb(var(--border) / 0.6)',
                  }}
                >
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-[#6C63FF]" />
                    <h3 className="text-base font-bold" style={{ color: 'rgb(var(--text-primary))' }}>LuminaAI Trust Center</h3>
                  </div>
                  <button
                    onClick={() => setIsTrustCenterOpen(false)}
                    className="p-1 rounded-lg transition-all cursor-pointer"
                    style={{ color: 'rgb(var(--text-secondary))' }}
                    aria-label="Fechar painel"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                {/* Drawer Body */}
                <div className="p-6">
                  <TrustCenterPanel data={payload.trust_center} />
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </CrossFilterProvider>
  );
});

