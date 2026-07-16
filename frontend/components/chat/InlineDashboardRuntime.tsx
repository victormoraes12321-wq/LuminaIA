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

import React, { useMemo, memo } from 'react';
import { motion } from 'framer-motion';
import { DashboardRuntimeEngine } from '@/components/dashboard-runtime/DashboardRuntimeEngine';
import { adaptQueryResponseToRuntimePayload, hasNativeADEPayload } from '@/lib/dashboardRuntimeAdapter';
import { useAuth } from '@/context/AuthContext';
import type { QueryResponse } from '@/types/lumina';
import type { DashboardRuntimePayload } from '@/types/dashboard-runtime';

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
