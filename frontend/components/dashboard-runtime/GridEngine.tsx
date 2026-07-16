'use client';

/**
 * ============================================================
 * LUMINA AI — Grid Engine (React Component)
 * ============================================================
 * Renders dashboard widgets on a 12-column CSS Grid,
 * using positions computed by the backend ADE and resolved
 * by the pure gridEngine.ts.
 *
 * Handles: responsive breakpoint tracking, position mapping,
 * grid gap, and fallback stacking for missing positions.
 * ============================================================
 */

import React, { memo, useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { RuntimeWidget } from '@/types/dashboard-runtime';
import {
  getGridContainerStyle,
  getGridItemStyle,
  buildPositionMap,
  validateGridLayout,
} from '@/engines/gridEngine';
import { useGridLayout } from '@/hooks/useGridLayout';
import type { ResponsiveGridLayouts } from '@/types/dashboard-runtime';
import { VirtualizedItem } from '@/components/performance/VirtualizationEngine';
import { RuntimeRenderer } from './RuntimeRenderer';

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────

interface GridEngineProps {
  widgets: RuntimeWidget[];
  gridLayouts: ResponsiveGridLayouts;
  expandedComponentId: string | null;
  onExpand: (id: string | null) => void;
  isRefreshing?: boolean;
  className?: string;
}

// ─────────────────────────────────────────────
// DEV VALIDATION
// ─────────────────────────────────────────────

const IS_DEV = process.env.NODE_ENV === 'development';

// ─────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────

export const GridEngine = memo(function GridEngine({
  widgets,
  gridLayouts,
  expandedComponentId,
  onExpand,
  isRefreshing = false,
  className,
}: GridEngineProps) {
  const { containerRef, breakpoint, layout } = useGridLayout(gridLayouts);

  // Build O(1) lookup map from component_id → position
  const positionMap = useMemo(() => buildPositionMap(layout), [layout]);

  // Dev-mode: validate grid to catch overlaps / out-of-bounds
  useMemo(() => {
    if (IS_DEV && layout.length > 0) {
      const result = validateGridLayout(layout);
      if (!result.valid) {
        console.warn('[GridEngine] Layout validation errors:', result.errors);
      }
      if (result.warnings.length > 0) {
        console.warn('[GridEngine] Layout warnings:', result.warnings);
      }
    }
  }, [layout]);

  const containerStyle = getGridContainerStyle();

  return (
    <div
      ref={containerRef}
      className={cn('w-full', className)}
      style={containerStyle}
      data-breakpoint={breakpoint}
      role="region"
      aria-label="Dashboard"
    >
      {widgets.map((widget, index) => {
        const pos = positionMap.get(widget.id);

        // Fallback: if no ADE position available, stack full-width
        const itemStyle = pos
          ? getGridItemStyle(pos)
          : {
              gridColumn: '1 / -1',
              gridRow: 'auto',
              minHeight: '300px',
              display: 'flex',
            };

        if (pos && !pos.visible) return null;

        const gridRows = pos?.h ?? 3;

        return (
          <div
            key={widget.id}
            style={itemStyle}
            className="min-w-0"
          >
            <VirtualizedItem
              componentType={widget.component_type}
              gridRows={gridRows}
              forceVisible={!pos}
            >
              <RuntimeRenderer
                widget={widget}
                expandedComponentId={expandedComponentId}
                onExpand={onExpand}
                isRefreshing={isRefreshing}
                animate
                animationDelay={index * 0.05}
              />
            </VirtualizedItem>
          </div>
        );
      })}
    </div>
  );
});
