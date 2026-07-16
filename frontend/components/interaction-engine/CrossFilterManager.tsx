'use client';

/**
 * ============================================================
 * LUMINA AI — Cross Filter Manager (Interaction Engine)
 * ============================================================
 * Manages cross-component filtering within a dashboard.
 * When a user clicks a data point in one component, all
 * other components with matching dimensions are filtered.
 *
 * Context-based — components call useCrossFilter() to
 * subscribe and emit filter events.
 * ============================================================
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  memo,
} from 'react';
import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CrossFilterEvent, FilterValue } from '@/types/dashboard-runtime';
import { cn } from '@/lib/utils';

// ─────────────────────────────────────────────
// CONTEXT
// ─────────────────────────────────────────────

interface CrossFilterState {
  filters: Record<string, { value: FilterValue; sourceId: string }>;
}

type CrossFilterAction =
  | { type: 'SET'; key: string; value: FilterValue; sourceId: string }
  | { type: 'CLEAR'; key: string }
  | { type: 'CLEAR_ALL' };

function crossFilterReducer(
  state: CrossFilterState,
  action: CrossFilterAction,
): CrossFilterState {
  switch (action.type) {
    case 'SET':
      return {
        filters: {
          ...state.filters,
          [action.key]: { value: action.value, sourceId: action.sourceId },
        },
      };
    case 'CLEAR': {
      const { [action.key]: _, ...rest } = state.filters;
      return { filters: rest };
    }
    case 'CLEAR_ALL':
      return { filters: {} };
    default:
      return state;
  }
}

interface CrossFilterContextValue {
  filters: Record<string, { value: FilterValue; sourceId: string }>;
  applyFilter(event: CrossFilterEvent): void;
  clearFilter(key: string): void;
  clearAllFilters(): void;
  activeCount: number;
}

const CrossFilterContext = createContext<CrossFilterContextValue | null>(null);

// ─────────────────────────────────────────────
// PROVIDER
// ─────────────────────────────────────────────

interface CrossFilterProviderProps {
  children: React.ReactNode;
}

export function CrossFilterProvider({ children }: CrossFilterProviderProps) {
  const [state, dispatch] = useReducer(crossFilterReducer, { filters: {} });

  const applyFilter = useCallback((event: CrossFilterEvent) => {
    dispatch({
      type: 'SET',
      key: event.filterKey,
      value: event.filterValue,
      sourceId: event.sourceComponentId,
    });
  }, []);

  const clearFilter = useCallback((key: string) => {
    dispatch({ type: 'CLEAR', key });
  }, []);

  const clearAllFilters = useCallback(() => {
    dispatch({ type: 'CLEAR_ALL' });
  }, []);

  const value = useMemo(
    () => ({
      filters: state.filters,
      applyFilter,
      clearFilter,
      clearAllFilters,
      activeCount: Object.keys(state.filters).length,
    }),
    [state.filters, applyFilter, clearFilter, clearAllFilters],
  );

  return (
    <CrossFilterContext.Provider value={value}>
      {children}
    </CrossFilterContext.Provider>
  );
}

// ─────────────────────────────────────────────
// HOOK
// ─────────────────────────────────────────────

export function useCrossFilter(): CrossFilterContextValue {
  const ctx = useContext(CrossFilterContext);
  if (!ctx) throw new Error('useCrossFilter must be used inside CrossFilterProvider');
  return ctx;
}

// ─────────────────────────────────────────────
// ACTIVE FILTERS BAR
// ─────────────────────────────────────────────

interface ActiveFiltersBarProps {
  className?: string;
}

export const ActiveFiltersBar = memo(function ActiveFiltersBar({
  className,
}: ActiveFiltersBarProps) {
  const { filters, clearFilter, clearAllFilters, activeCount } = useCrossFilter();

  return (
    <AnimatePresence>
      {activeCount > 0 && (
        <motion.div
          key="filters-bar"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.2 }}
          className={cn(
            'flex items-center gap-2 flex-wrap px-3 py-2',
            'rounded-xl border border-[#6C63FF]/20 bg-[#6C63FF]/[0.05]',
            className,
          )}
          role="region"
          aria-label="Filtros ativos"
        >
          <span className="text-xs font-medium text-[#9C95FF] shrink-0">
            Filtros ativos:
          </span>

          {Object.entries(filters).map(([key, { value }]) => (
            <motion.span
              key={key}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs
                bg-[#6C63FF]/20 text-[#9C95FF] border border-[#6C63FF]/30"
            >
              <span className="font-medium">{key}:</span>
              <span className="opacity-80">{String(value)}</span>
              <button
                onClick={() => clearFilter(key)}
                className="ml-1 opacity-60 hover:opacity-100 transition-opacity"
                aria-label={`Remover filtro ${key}`}
              >
                <X className="h-2.5 w-2.5" />
              </button>
            </motion.span>
          ))}

          <button
            onClick={clearAllFilters}
            className="ml-auto text-xs text-white/30 hover:text-white/60 transition-colors shrink-0"
            aria-label="Limpar todos os filtros"
          >
            Limpar tudo
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
});
