/**
 * ============================================================
 * LUMINA AI — Client-Side Performance Monitor (Pure TypeScript)
 * ============================================================
 * Tracks FPS, render time, and memory usage for diagnostics.
 * Intended for development / performance telemetry only.
 * Does NOT affect rendering behaviour.
 * ============================================================
 */

import type { ClientRenderMetrics } from '@/types/dashboard-runtime';

interface PerformanceMemoryInfo {
  usedJSHeapSize: number;
}

interface PerformanceWithMemory extends Performance {
  memory?: PerformanceMemoryInfo;
}

// ─────────────────────────────────────────────
// FPS TRACKER
// ─────────────────────────────────────────────

export interface FPSTracker {
  start(): void;
  stop(): void;
  getFPS(): number;
}

/**
 * Creates a lightweight FPS tracker using requestAnimationFrame.
 * Samples over a rolling 60-frame window.
 */
export function createFPSTracker(): FPSTracker {
  let running = false;
  let frames = 0;
  let lastTime = performance.now();
  let fps = 60;
  let rafId: number | null = null;

  function tick(): void {
    if (!running) return;
    frames++;
    const now = performance.now();
    const elapsed = now - lastTime;

    if (elapsed >= 1000) {
      fps = Math.round((frames * 1000) / elapsed);
      frames = 0;
      lastTime = now;
    }

    rafId = requestAnimationFrame(tick);
  }

  return {
    start() {
      if (running) return;
      running = true;
      lastTime = performance.now();
      frames = 0;
      rafId = requestAnimationFrame(tick);
    },
    stop() {
      running = false;
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    },
    getFPS() {
      return fps;
    },
  };
}

// ─────────────────────────────────────────────
// RENDER TIMER
// ─────────────────────────────────────────────

/**
 * Measures the wall-clock time for a synchronous operation.
 */
export function measureSyncRender<T>(fn: () => T): { result: T; durationMs: number } {
  const start = performance.now();
  const result = fn();
  return { result, durationMs: performance.now() - start };
}

/**
 * Wraps an async function and measures its duration.
 */
export async function measureAsyncRender<T>(
  fn: () => Promise<T>,
): Promise<{ result: T; durationMs: number }> {
  const start = performance.now();
  const result = await fn();
  return { result, durationMs: performance.now() - start };
}

// ─────────────────────────────────────────────
// MEMORY SAMPLER
// ─────────────────────────────────────────────

/**
 * Samples current JS heap usage in MB.
 * Only available in Chromium browsers with performance.memory.
 * Returns null in other environments.
 */
export function sampleMemoryMB(): number | null {
  const mem = (performance as PerformanceWithMemory).memory;
  if (!mem) return null;
  return Math.round(mem.usedJSHeapSize / 1_048_576);
}

// ─────────────────────────────────────────────
// METRIC AGGREGATION
// ─────────────────────────────────────────────

/**
 * Builds a complete ClientRenderMetrics snapshot.
 */
export function buildRenderMetrics(
  renderTimeMs: number,
  visibleComponents: number,
  totalComponents: number,
  fps: number,
): ClientRenderMetrics {
  const memoryMB = sampleMemoryMB();
  return {
    totalRenderTimeMs: Math.round(renderTimeMs),
    visibleComponents,
    totalComponents,
    fps,
    ...(memoryMB !== null ? { memoryUsageMB: memoryMB } : {}),
  };
}

// ─────────────────────────────────────────────
// PERFORMANCE BUDGET EVALUATION
// ─────────────────────────────────────────────

export type PerformanceBudgetStatus = 'excellent' | 'good' | 'fair' | 'poor';

/**
 * Evaluates render performance against predefined budgets.
 */
export function evaluatePerformance(
  metrics: ClientRenderMetrics,
): PerformanceBudgetStatus {
  const { totalRenderTimeMs, fps } = metrics;

  if (totalRenderTimeMs < 100 && fps >= 55) return 'excellent';
  if (totalRenderTimeMs < 300 && fps >= 45) return 'good';
  if (totalRenderTimeMs < 600 && fps >= 30) return 'fair';
  return 'poor';
}

// ─────────────────────────────────────────────
// DEVELOPMENT LOGGER
// ─────────────────────────────────────────────

const IS_DEV = process.env.NODE_ENV === 'development';

/**
 * Logs render metrics to the console in development.
 * No-op in production.
 */
export function logMetrics(label: string, metrics: ClientRenderMetrics): void {
  if (!IS_DEV) return;
  const status = evaluatePerformance(metrics);
  const icon =
    status === 'excellent' ? '🟢' :
    status === 'good' ? '🟡' :
    status === 'fair' ? '🟠' :
    '🔴';

  console.groupCollapsed(
    `${icon} [LuminaAI Performance] ${label} — ${metrics.totalRenderTimeMs}ms | ${metrics.fps}fps`,
  );
  console.table(metrics);
  console.groupEnd();
}
