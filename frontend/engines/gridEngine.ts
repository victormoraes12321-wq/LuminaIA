/**
 * ============================================================
 * LUMINA AI — Pure Grid Engine (TypeScript, no React)
 * ============================================================
 * Mirrors the backend AdaptiveGridEngine logic in pure TS.
 * Converts ADE grid_layouts[breakpoint] to CSS Grid styles.
 *
 * 12-column grid, each row = 100px.
 * 5 breakpoints: ultra_wide, desktop, notebook, tablet, mobile.
 * ============================================================
 */

import type {
  Breakpoint,
  GridLayout,
  GridPosition,
  ResponsiveGridLayouts,
} from '@/types/dashboard-runtime';
import { BREAKPOINT_WIDTHS } from '@/types/dashboard-runtime';

// ─────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────

export const GRID_COLUMNS = 12;
export const GRID_ROW_HEIGHT_PX = 100;
export const GRID_GAP_PX = 16;

// ─────────────────────────────────────────────
// BREAKPOINT RESOLUTION
// ─────────────────────────────────────────────

/**
 * Returns the current breakpoint based on container/window width.
 */
export function resolveBreakpoint(width: number): Breakpoint {
  if (width >= BREAKPOINT_WIDTHS.ultra_wide) return 'ultra_wide';
  if (width >= BREAKPOINT_WIDTHS.desktop) return 'desktop';
  if (width >= BREAKPOINT_WIDTHS.notebook) return 'notebook';
  if (width >= BREAKPOINT_WIDTHS.tablet) return 'tablet';
  return 'mobile';
}

/**
 * Returns the best available grid layout for the current breakpoint,
 * falling back gracefully to larger breakpoints if not defined.
 */
export function resolveGridLayout(
  gridLayouts: ResponsiveGridLayouts,
  breakpoint: Breakpoint,
): GridLayout {
  const fallbackOrder: Breakpoint[] = [
    breakpoint,
    'desktop',
    'notebook',
    'tablet',
    'ultra_wide',
    'mobile',
  ];

  for (const bp of fallbackOrder) {
    const layout = gridLayouts[bp];
    if (layout && layout.length > 0) return layout;
  }

  return [];
}

// ─────────────────────────────────────────────
// CSS GRID STYLE GENERATION
// ─────────────────────────────────────────────

export interface CSSGridItemStyle {
  gridColumn: string;
  gridRow: string;
  minHeight: string;
  display: string;
}

export interface CSSGridContainerStyle {
  display: string;
  gridTemplateColumns: string;
  gap: string;
  width: string;
}

/**
 * Returns the CSS Grid container styles.
 */
export function getGridContainerStyle(): CSSGridContainerStyle {
  return {
    display: 'grid',
    gridTemplateColumns: `repeat(${GRID_COLUMNS}, 1fr)`,
    gap: `${GRID_GAP_PX}px`,
    width: '100%',
  };
}

/**
 * Converts a GridPosition to CSS Grid inline styles.
 * Uses 1-indexed CSS grid coordinates (backend uses 0-indexed x,y).
 */
export function getGridItemStyle(pos: GridPosition): CSSGridItemStyle {
  const colStart = pos.x + 1;
  const colEnd = pos.x + pos.w + 1;
  const rowStart = pos.y + 1;
  const rowEnd = pos.y + pos.h + 1;

  return {
    gridColumn: `${colStart} / ${colEnd}`,
    gridRow: `${rowStart} / ${rowEnd}`,
    minHeight: `${pos.h * GRID_ROW_HEIGHT_PX + (pos.h - 1) * GRID_GAP_PX}px`,
    display: pos.visible ? 'flex' : 'none',
  };
}

// ─────────────────────────────────────────────
// VISIBILITY FILTERING
// ─────────────────────────────────────────────

/**
 * Filters out invisible positions from a grid layout.
 */
export function getVisiblePositions(layout: GridLayout): GridLayout {
  return layout.filter((pos) => pos.visible);
}

/**
 * Returns a map from component_id → GridPosition for O(1) lookup.
 */
export function buildPositionMap(
  layout: GridLayout,
): Map<string, GridPosition> {
  return new Map(layout.map((pos) => [pos.component_id, pos]));
}

// ─────────────────────────────────────────────
// GRID INTEGRITY VALIDATION
// ─────────────────────────────────────────────

export interface GridValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Validates a grid layout for overlaps and out-of-bounds positions.
 * Used for diagnostics and development-mode warnings.
 */
export function validateGridLayout(layout: GridLayout): GridValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  for (const pos of layout) {
    // Bounds check
    if (pos.x < 0 || pos.x + pos.w > GRID_COLUMNS) {
      errors.push(
        `[${pos.component_id}] x=${pos.x}, w=${pos.w} exceeds ${GRID_COLUMNS} columns`,
      );
    }
    if (pos.y < 0) {
      errors.push(`[${pos.component_id}] y=${pos.y} is negative`);
    }
    if (pos.w < 1 || pos.h < 1) {
      errors.push(
        `[${pos.component_id}] Invalid dimensions: w=${pos.w}, h=${pos.h}`,
      );
    }
  }

  // Overlap detection
  const cells = new Set<string>();
  for (const pos of layout) {
    if (!pos.visible) continue;
    for (let r = pos.y; r < pos.y + pos.h; r++) {
      for (let c = pos.x; c < pos.x + pos.w; c++) {
        const key = `${r},${c}`;
        if (cells.has(key)) {
          warnings.push(
            `[${pos.component_id}] Overlaps another component at cell (${r},${c})`,
          );
        }
        cells.add(key);
      }
    }
  }

  return { valid: errors.length === 0, errors, warnings };
}

// ─────────────────────────────────────────────
// COMPACTION (collapse empty rows)
// ─────────────────────────────────────────────

/**
 * Compacts a grid layout vertically — moves all items as high as possible
 * without overlapping. Used when the backend layout has gaps.
 */
export function compactGridLayout(layout: GridLayout): GridLayout {
  if (layout.length === 0) return layout;

  // Sort by (y, x)
  const sorted = [...layout].sort((a, b) => a.y - b.y || a.x - b.x);

  // Track occupied cells
  const occupied = new Set<string>();

  function isOccupied(pos: GridPosition, newY: number): boolean {
    for (let r = newY; r < newY + pos.h; r++) {
      for (let c = pos.x; c < pos.x + pos.w; c++) {
        if (occupied.has(`${r},${c}`)) return true;
      }
    }
    return false;
  }

  function markOccupied(pos: GridPosition, newY: number): void {
    for (let r = newY; r < newY + pos.h; r++) {
      for (let c = pos.x; c < pos.x + pos.w; c++) {
        occupied.add(`${r},${c}`);
      }
    }
  }

  return sorted.map((pos) => {
    let newY = 0;
    while (isOccupied(pos, newY)) {
      newY++;
    }
    markOccupied(pos, newY);
    return { ...pos, y: newY };
  });
}

// ─────────────────────────────────────────────
// GRID METRICS
// ─────────────────────────────────────────────

export interface GridMetrics {
  totalRows: number;
  occupiedCells: number;
  totalCells: number;
  utilization: number;
  totalHeightPx: number;
}

/**
 * Computes useful metrics about a grid layout.
 */
export function computeGridMetrics(layout: GridLayout): GridMetrics {
  const visible = getVisiblePositions(layout);
  if (visible.length === 0) {
    return {
      totalRows: 0,
      occupiedCells: 0,
      totalCells: 0,
      utilization: 0,
      totalHeightPx: 0,
    };
  }

  const maxRow = Math.max(...visible.map((p) => p.y + p.h));
  const occupiedCells = visible.reduce((sum, p) => sum + p.w * p.h, 0);
  const totalCells = maxRow * GRID_COLUMNS;
  const totalHeightPx =
    maxRow * GRID_ROW_HEIGHT_PX + (maxRow - 1) * GRID_GAP_PX;

  return {
    totalRows: maxRow,
    occupiedCells,
    totalCells,
    utilization: totalCells > 0 ? occupiedCells / totalCells : 0,
    totalHeightPx,
  };
}
