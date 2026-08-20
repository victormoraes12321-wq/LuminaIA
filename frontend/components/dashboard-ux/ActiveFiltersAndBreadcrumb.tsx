'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { ChevronRight, Filter, X, RotateCcw, Home } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ActiveFilter, BreadcrumbLevel } from './types'

interface ActiveFiltersAndBreadcrumbProps {
  breadcrumb: BreadcrumbLevel[]
  activeFilters: ActiveFilter[]
  onNavigateBreadcrumb: (index: number) => void
  onRemoveFilter: (filterId: string) => void
  onClearAllFilters: () => void
}

export function ActiveFiltersAndBreadcrumb({
  breadcrumb,
  activeFilters,
  onNavigateBreadcrumb,
  onRemoveFilter,
  onClearAllFilters,
}: ActiveFiltersAndBreadcrumbProps) {
  return (
    <div className="flex flex-col gap-2.5 py-1">
      {/* ── 1. Analytical Breadcrumb ── */}
      <nav data-testid="dashboard-breadcrumb" aria-label="Navegação Analítica" className="flex items-center gap-1.5 text-xs text-zinc-400 overflow-x-auto py-0.5">
        <button
          type="button"
          data-testid="breadcrumb-level-0"
          onClick={() => onNavigateBreadcrumb(0)}
          className={cn(
            'flex items-center gap-1 px-2 py-1 rounded-md transition-colors',
            breadcrumb.length === 1
              ? 'bg-zinc-800 text-white font-semibold'
              : 'hover:bg-zinc-800/60 hover:text-zinc-200'
          )}
        >
          <Home size={12} className="text-lumina-400" />
          <span>Visão Geral</span>
        </button>

        {breadcrumb.slice(1).map((lvl, index) => {
          const isLast = index === breadcrumb.length - 2
          const targetIndex = index + 1

          return (
            <div key={lvl.id} className="flex items-center gap-1.5">
              <ChevronRight size={12} className="text-zinc-600 shrink-0" />
              <button
                type="button"
                data-testid={`breadcrumb-level-${targetIndex}`}
                onClick={() => onNavigateBreadcrumb(targetIndex)}
                className={cn(
                  'px-2 py-1 rounded-md transition-colors max-w-[200px] truncate',
                  isLast
                    ? 'bg-lumina-500/15 text-lumina-300 font-semibold border border-lumina-500/30'
                    : 'hover:bg-zinc-800/60 hover:text-zinc-200'
                )}
                title={lvl.label}
              >
                {lvl.label}
              </button>
            </div>
          )
        })}
      </nav>

      {/* ── 2. Active Filter Chips ── */}
      <AnimatePresence>
        {activeFilters.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap items-center gap-2 pt-1 border-t border-zinc-800/50"
            data-testid="active-filters-container"
          >
            <div className="flex items-center gap-1 text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
              <Filter size={11} />
              <span>Filtros Ativos:</span>
            </div>

            {activeFilters.map(filter => (
              <motion.span
                layout
                key={filter.id}
                initial={{ scale: 0.85, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.85, opacity: 0 }}
                data-testid={`active-filter-${filter.id}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-zinc-700 bg-zinc-900/90 px-2.5 py-0.5 text-xs text-zinc-200 shadow-sm"
              >
                <span className="text-[10px] text-zinc-500 uppercase font-mono">{filter.dimension}:</span>
                <span className="font-medium text-white">{filter.label}</span>
                <button
                  type="button"
                  data-testid={`remove-filter-${filter.id}`}
                  onClick={() => onRemoveFilter(filter.id)}
                  className="rounded-full p-0.5 text-zinc-400 hover:bg-zinc-800 hover:text-white transition"
                  aria-label={`Remover filtro ${filter.label}`}
                >
                  <X size={12} />
                </button>
              </motion.span>
            ))}

            <button
              type="button"
              data-testid="clear-all-filters"
              onClick={onClearAllFilters}
              className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-lumina-300 transition-colors ml-1"
            >
              <RotateCcw size={11} />
              <span>Limpar filtros</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
