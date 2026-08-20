'use client';

/**
 * ============================================================
 * LUMINA AI — Virtualization Engine (Performance Layer)
 * ============================================================
 * Renders only dashboard components that are visible in the
 * viewport, using IntersectionObserver.
 *
 * Heavy components (Treemap, Heatmap, Scatter, DataTable)
 * show a skeleton until they scroll into view.
 * ============================================================
 */

import React, {
  useEffect,
  useRef,
  useState,
  memo,
  type ReactNode,
} from 'react';
import { isHeavyComponent } from '@/engines/layoutIntelligence';
import type { ECEComponentType } from '@/types/dashboard-runtime';
import { SkeletonCard } from '@/components/component-library/status/StatusComponents';

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────

interface VirtualizedItemProps {
  componentType: ECEComponentType;
  /** Grid height in rows (1 row = 100px) */
  gridRows: number;
  children: ReactNode;
  /** Margin before item is considered visible (px) */
  rootMargin?: string;
  /** Skip virtualization for this item */
  forceVisible?: boolean;
}

// ─────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────

export const VirtualizedItem = memo(function VirtualizedItem({
  componentType,
  gridRows,
  children,
  rootMargin = '200px',
  forceVisible = false,
}: VirtualizedItemProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [observedVisible, setObservedVisible] = useState(false);

  const heavy = isHeavyComponent(componentType);
  const visible = !heavy || forceVisible || observedVisible;

  useEffect(() => {
    // Non-heavy components render immediately
    if (!heavy || forceVisible) {
      return;
    }

    if (!ref.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setObservedVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin, threshold: 0 },
    );

    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [heavy, forceVisible, rootMargin]);

  return (
    <div ref={ref} className="h-full w-full">
      {visible
        ? children
        : <SkeletonCard rows={gridRows} className="h-full" />}
    </div>
  );
});

// ─────────────────────────────────────────────
// VISIBILITY TRACKER (for metrics)
// ─────────────────────────────────────────────

/**
 * Higher-order hook that tracks how many elements are visible.
 * Returns a count of visible component IDs.
 */
export function useVisibilityTracker(ids: string[]): Set<string> {
  const [visibleIds, setVisibleIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const refs: Map<string, Element> = new Map();

    const observer = new IntersectionObserver(
      (entries) => {
        setVisibleIds((prev) => {
          const next = new Set(prev);
          entries.forEach((entry) => {
            const id = (entry.target as HTMLElement).dataset.componentId;
            if (!id) return;
            if (entry.isIntersecting) next.add(id);
            else next.delete(id);
          });
          return next;
        });
      },
      { threshold: 0.1 },
    );

    ids.forEach((id) => {
      const el = document.querySelector(`[data-component-id="${id}"]`);
      if (el) {
        refs.set(id, el);
        observer.observe(el);
      }
    });

    return () => observer.disconnect();
  }, [ids]);

  return visibleIds;
}
