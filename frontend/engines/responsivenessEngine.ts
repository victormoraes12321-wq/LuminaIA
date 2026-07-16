/**
 * ============================================================
 * LUMINA AI — Responsiveness Engine (Pure TypeScript)
 * ============================================================
 * Tracks container/window width changes and resolves
 * the current Breakpoint reactively via ResizeObserver.
 *
 * Provides utilities for breakpoint-aware rendering decisions.
 * ============================================================
 */

import type { Breakpoint } from '@/types/dashboard-runtime';
import { BREAKPOINT_WIDTHS } from '@/types/dashboard-runtime';
import { resolveBreakpoint } from './gridEngine';

// ─────────────────────────────────────────────
// BREAKPOINT UTILITIES
// ─────────────────────────────────────────────

/**
 * Returns ordered breakpoints from smallest to largest.
 */
export const BREAKPOINT_ORDER: Breakpoint[] = [
  'mobile',
  'tablet',
  'notebook',
  'desktop',
  'ultra_wide',
];

/**
 * Returns true if breakpointA is larger than breakpointB.
 */
export function isLargerBreakpoint(a: Breakpoint, b: Breakpoint): boolean {
  return BREAKPOINT_ORDER.indexOf(a) > BREAKPOINT_ORDER.indexOf(b);
}

/**
 * Returns true if the current breakpoint is mobile or tablet.
 */
export function isMobile(bp: Breakpoint): boolean {
  return bp === 'mobile' || bp === 'tablet';
}

export function isDesktop(bp: Breakpoint): boolean {
  return bp === 'desktop' || bp === 'ultra_wide';
}

// ─────────────────────────────────────────────
// RESIZE OBSERVER FACTORY
// ─────────────────────────────────────────────

export type BreakpointChangeCallback = (
  bp: Breakpoint,
  width: number,
) => void;

export interface ResponsivenessObserver {
  /** Start observing a DOM element's width */
  observe(element: Element): void;
  /** Stop observing */
  unobserve(element: Element): void;
  /** Disconnect completely */
  disconnect(): void;
}

/**
 * Creates a ResizeObserver that fires a callback whenever
 * the observed element's width changes to a different breakpoint.
 *
 * @param callback - Called with the new breakpoint and raw pixel width
 * @param throttleMs - Debounce interval in milliseconds (default: 100)
 */
export function createResponsivenessObserver(
  callback: BreakpointChangeCallback,
  throttleMs = 100,
): ResponsivenessObserver {
  let lastBp: Breakpoint | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const observer = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const width =
        entry.contentBoxSize?.[0]?.inlineSize ??
        entry.contentRect.width;

      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        const newBp = resolveBreakpoint(width);
        if (newBp !== lastBp) {
          lastBp = newBp;
          callback(newBp, width);
        }
      }, throttleMs);
    }
  });

  return {
    observe: (el) => observer.observe(el),
    unobserve: (el) => observer.unobserve(el),
    disconnect: () => {
      if (timer) clearTimeout(timer);
      observer.disconnect();
    },
  };
}

// ─────────────────────────────────────────────
// SERVER-SIDE SAFE BREAKPOINT (SSR fallback)
// ─────────────────────────────────────────────

/**
 * Returns the breakpoint based on window.innerWidth.
 * Safe to call only in browser context.
 */
export function getWindowBreakpoint(): Breakpoint {
  if (typeof window === 'undefined') return 'desktop';
  return resolveBreakpoint(window.innerWidth);
}

// ─────────────────────────────────────────────
// COLUMN SPAN UTILITIES
// ─────────────────────────────────────────────

/**
 * For a given breakpoint, returns the recommended default
 * column span for various component types.
 */
export type ComponentSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'full';

const COMPONENT_SIZE_COLS: Record<Breakpoint, Record<ComponentSize, number>> = {
  ultra_wide: { xs: 2, sm: 3, md: 4, lg: 6, xl: 8, full: 12 },
  desktop:    { xs: 2, sm: 3, md: 4, lg: 6, xl: 8, full: 12 },
  notebook:   { xs: 3, sm: 4, md: 6, lg: 8, xl: 10, full: 12 },
  tablet:     { xs: 4, sm: 6, md: 6, lg: 12, xl: 12, full: 12 },
  mobile:     { xs: 6, sm: 12, md: 12, lg: 12, xl: 12, full: 12 },
};

export function getDefaultColSpan(
  bp: Breakpoint,
  size: ComponentSize,
): number {
  return COMPONENT_SIZE_COLS[bp][size];
}

// ─────────────────────────────────────────────
// BREAKPOINT CSS CLASS MAP
// ─────────────────────────────────────────────

/**
 * CSS classes to apply for each breakpoint (Tailwind-compatible).
 */
export const BREAKPOINT_CSS_CLASSES: Record<Breakpoint, string> = {
  ultra_wide: 'bp-ultra-wide',
  desktop:    'bp-desktop',
  notebook:   'bp-notebook',
  tablet:     'bp-tablet',
  mobile:     'bp-mobile',
};

// ─────────────────────────────────────────────
// MEDIA QUERY STRINGS
// ─────────────────────────────────────────────

export const MEDIA_QUERIES: Record<Breakpoint, string> = {
  ultra_wide: `(min-width: ${BREAKPOINT_WIDTHS.ultra_wide}px)`,
  desktop:    `(min-width: ${BREAKPOINT_WIDTHS.desktop}px)`,
  notebook:   `(min-width: ${BREAKPOINT_WIDTHS.notebook}px)`,
  tablet:     `(min-width: ${BREAKPOINT_WIDTHS.tablet}px)`,
  mobile:     `(max-width: ${BREAKPOINT_WIDTHS.tablet - 1}px)`,
};

/**
 * Matches a media query and returns a boolean.
 * Falls back to true on SSR.
 */
export function matchesMediaQuery(query: string): boolean {
  if (typeof window === 'undefined') return true;
  return window.matchMedia(query).matches;
}
