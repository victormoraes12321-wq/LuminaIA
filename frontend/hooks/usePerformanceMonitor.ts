'use client';

/**
 * ============================================================
 * LUMINA AI — usePerformanceMonitor Hook
 * ============================================================
 * Tracks client-side render performance (FPS, render time,
 * memory) and exposes metrics for diagnostics/telemetry.
 * ============================================================
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ClientRenderMetrics } from '@/types/dashboard-runtime';
import {
  createFPSTracker,
  buildRenderMetrics,
  logMetrics,
  evaluatePerformance,
  type PerformanceBudgetStatus,
} from '@/engines/performanceMonitor';

export interface UsePerformanceMonitorResult {
  /** Latest render metrics snapshot */
  metrics: ClientRenderMetrics | null;
  /** Overall performance evaluation */
  status: PerformanceBudgetStatus | null;
  /** Call this after rendering is complete to record a snapshot */
  recordRender(label: string, visibleComponents: number, totalComponents: number): void;
}

/**
 * Monitors FPS and render timing for dashboard performance analysis.
 *
 * @param enabled - Set to false to disable tracking (e.g., in production)
 */
export function usePerformanceMonitor(
  enabled = process.env.NODE_ENV === 'development',
): UsePerformanceMonitorResult {
  const trackerRef = useRef(createFPSTracker());
  const renderStartRef = useRef<number>(0);
  const [metrics, setMetrics] = useState<ClientRenderMetrics | null>(null);
  const [status, setStatus] = useState<PerformanceBudgetStatus | null>(null);

  useEffect(() => {
    if (!enabled) return;
    const tracker = trackerRef.current;
    tracker.start();
    renderStartRef.current = performance.now();
    return () => tracker.stop();
  }, [enabled]);

  const recordRender = useCallback(
    (label: string, visibleComponents: number, totalComponents: number) => {
      if (!enabled) return;
      const now = performance.now();
      const durationMs = now - (renderStartRef.current || now);
      const fps = trackerRef.current.getFPS();
      const m = buildRenderMetrics(durationMs, visibleComponents, totalComponents, fps);
      setMetrics(m);
      setStatus(evaluatePerformance(m));
      logMetrics(label, m);
    },
    [enabled],
  );

  return { metrics, status, recordRender };
}
