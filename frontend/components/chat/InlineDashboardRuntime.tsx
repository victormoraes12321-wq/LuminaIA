'use client';

/**
 * ============================================================
 * LUMINA AI — InlineDashboardRuntime
 * ============================================================
 * Drop-in replacement for the legacy InlineDashboard component.
 * Uses the DashboardRuntimeEngine for rendering while maintaining
 * full backward compatibility with the existing API response.
 *
 * It detects whether the response already has a native ADE
 * payload (from the backend) or needs to be adapted from
 * the legacy QueryResponse format.
 * ============================================================
 */

import React, { useEffect, useMemo, memo } from 'react';
import { motion } from 'framer-motion';
import { DashboardRuntimeEngine } from '@/components/dashboard-runtime/DashboardRuntimeEngine';
import { DynamicRenderer } from '@/components/DynamicRenderer';
import { adaptQueryResponseToRuntimePayload, hasNativeADEPayload } from '@/lib/dashboardRuntimeAdapter';
import { useAuth } from '@/context/AuthContext';
import type { QueryResponse } from '@/types/lumina';
import type { DashboardRuntimePayload } from '@/types/dashboard-runtime';
import {
  buildComparisonPresentationModel,
  getComparisonRendererFeatureFlags,
  isComparisonQueryResponse,
} from '@/components/comparison';
import {
  emitComparisonTelemetry,
  structuralFingerprint,
} from '@/components/comparison/comparisonTelemetry';
import type {
  ComparisonPresentationModel,
  ComparisonUserRole,
} from '@/components/comparison';

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────

interface InlineDashboardRuntimeProps {
  response: QueryResponse;
  className?: string;
}

type QueryResponseWithRuntimePayload = QueryResponse & {
  ade_layout?: DashboardRuntimePayload | null;
};

// ─────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────

export const InlineDashboardRuntime = memo(function InlineDashboardRuntime({
  response,
  className,
}: InlineDashboardRuntimeProps) {
  const { token, user } = useAuth();
  const flags = getComparisonRendererFeatureFlags();
  const comparisonDetected = isComparisonQueryResponse(response);
  const role: ComparisonUserRole =
    user?.role === 'ADMIN' || user?.role === 'GESTOR' || user?.role === 'CONSULTA'
      ? user.role
      : 'CONSULTA';

  const comparisonAdaptation = useMemo<{
    model: ComparisonPresentationModel | null;
    durationMs: number;
    errorCode: string | null;
  }>(() => {
    if (!comparisonDetected || (!flags.enabled && !flags.shadowMode)) {
      return { model: null, durationMs: 0, errorCode: null };
    }
    const startedAt = performance.now();
    try {
      return {
        model: buildComparisonPresentationModel(response, { role }),
        durationMs: performance.now() - startedAt,
        errorCode: null,
      };
    } catch (error) {
      return {
        model: null,
        durationMs: performance.now() - startedAt,
        errorCode: error instanceof Error ? error.name : 'UNKNOWN_PRESENTATION_ERROR',
      };
    }
  }, [comparisonDetected, flags.enabled, flags.shadowMode, response, role]);

  // Determine the payload: native ADE or adapted from legacy
  const payload = useMemo<DashboardRuntimePayload | null>(() => {
    if (!response.chart_data && !response.visualizations?.length) return null;

    if (hasNativeADEPayload(response)) {
      // Backend already returned a full ADE payload
      return (response as QueryResponseWithRuntimePayload).ade_layout ?? null;
    }

    // Adapt legacy format to runtime format
    return adaptQueryResponseToRuntimePayload(response);
  }, [response]);

  useEffect(() => {
    const model = comparisonAdaptation.model;
    if (!comparisonDetected || (!flags.enabled && !flags.shadowMode)) return;
    const legacyVisualizationCount = response.visualizations?.length ??
      (response.chart_type && response.chart_data ? 1 : 0);
    emitComparisonTelemetry({
      presentationVersion: model?.presentationVersion ?? 'unavailable',
      comparisonKind: model?.comparisonKind ?? 'unavailable',
      renderer: flags.enabled ? 'COMPARISON_V2' : 'SHADOW',
      operandCount: model?.operands.length ?? 0,
      datasetCount: model?.datasets.length ?? 0,
      rowCount: model?.datasets.reduce((total, dataset) => total + dataset.rowCount, 0) ?? 0,
      visualizationCount: model?.visualizations.length ?? 0,
      partial: model?.partial ?? false,
      truncated: model?.truncated ?? false,
      status: model?.status ?? 'ERROR',
      adaptationDurationMs: comparisonAdaptation.durationMs,
      fallbackUsed: !flags.enabled,
      featureEnabled: flags.enabled,
      shadowDivergence: model
        ? model.visualizations.length !== legacyVisualizationCount
        : true,
      structuralFingerprint: model ? structuralFingerprint(model) : null,
      role,
      errorCode: comparisonAdaptation.errorCode,
    });
  }, [
    comparisonAdaptation,
    comparisonDetected,
    flags.enabled,
    flags.shadowMode,
    response.chart_data,
    response.chart_type,
    response.visualizations,
    role,
  ]);

  if (comparisonDetected && flags.enabled) {
    if (!comparisonAdaptation.model) {
      return (
        <div
          role="alert"
          className="border-y border-rose-500/30 bg-rose-500/5 px-4 py-3 text-sm text-rose-800 dark:text-rose-200"
        >
          O resultado comparativo possui um contrato inconsistente e nao pode ser exibido com seguranca.
        </div>
      );
    }
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className={className}
      >
        <DynamicRenderer
          chartType={response.chart_type}
          chartData={response.chart_data}
          visualizations={response.visualizations}
          title={response.view_name ?? undefined}
          comparisonModel={comparisonAdaptation.model}
        />
      </motion.div>
    );
  }

  // No data to render
  if (!payload) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={className}
    >
      <DashboardRuntimeEngine
        payload={payload}
        token={token}
        tenantId={user?.tenant_id ?? null}
        enableSSE={false} // SSE disabled in inline chat mode (no persistent dashboardId)
      />
    </motion.div>
  );
});
