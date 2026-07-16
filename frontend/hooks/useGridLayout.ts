'use client';

/**
 * ============================================================
 * LUMINA AI — useGridLayout Hook
 * ============================================================
 * Tracks the container's current breakpoint reactively via
 * ResizeObserver and provides the resolved GridLayout for it.
 * ============================================================
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Breakpoint, GridLayout, ResponsiveGridLayouts } from '@/types/dashboard-runtime';
import { createResponsivenessObserver, getWindowBreakpoint } from '@/engines/responsivenessEngine';
import { resolveGridLayout } from '@/engines/gridEngine';

export interface UseGridLayoutResult {
  /** Container ref to attach to the grid wrapper element */
  containerRef: React.RefObject<HTMLDivElement | null>;
  /** Current resolved breakpoint */
  breakpoint: Breakpoint;
  /** Grid positions for the current breakpoint */
  layout: GridLayout;
  /** Raw container width in pixels */
  containerWidth: number;
}

/**
 * Tracks container width and resolves the correct grid layout
 * for the current breakpoint.
 *
 * @param gridLayouts - The responsive grid layouts from the ADE payload
 */
export function useGridLayout(
  gridLayouts: ResponsiveGridLayouts,
): UseGridLayoutResult {
  const containerRef = useRef<HTMLDivElement>(null);
  const [breakpoint, setBreakpoint] = useState<Breakpoint>(getWindowBreakpoint);
  const [containerWidth, setContainerWidth] = useState<number>(
    typeof window !== 'undefined' ? window.innerWidth : 1280,
  );

  const handleBreakpointChange = useCallback(
    (bp: Breakpoint, width: number) => {
      setBreakpoint(bp);
      setContainerWidth(width);
    },
    [],
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = createResponsivenessObserver(handleBreakpointChange, 80);
    observer.observe(el);

    // Initial measurement
    const rect = el.getBoundingClientRect();
    if (rect.width > 0) {
      handleBreakpointChange(
        getWindowBreakpoint(),
        rect.width,
      );
    }

    return () => observer.disconnect();
  }, [handleBreakpointChange]);

  const layout = resolveGridLayout(gridLayouts, breakpoint);

  return { containerRef, breakpoint, layout, containerWidth };
}
