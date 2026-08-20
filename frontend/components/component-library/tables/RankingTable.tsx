'use client';

/**
 * ============================================================
 * LUMINA AI — Ranking Table (ECE Component)
 * ============================================================
 * Displays a ranked list with medals, progress bars and
 * percentage share. Used for top-N analytical rankings.
 * ============================================================
 */

import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { cn, formatNumber, formatCurrency } from '@/lib/utils';

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────

export interface RankingItem {
  rank: number;
  label: string;
  value: number;
  value_formatado?: string;
  percentage?: number;
  unit?: 'BRL' | 'count' | 'percent';
  badge?: string;
}

interface RankingTableProps {
  items: RankingItem[];
  title?: string;
  maxItems?: number;
  showProgressBar?: boolean;
  className?: string;
}

// ─────────────────────────────────────────────
// MEDAL COLORS
// ─────────────────────────────────────────────

const MEDAL_COLORS: Record<number, string> = {
  1: 'text-yellow-400 bg-yellow-400/10',
  2: 'text-slate-300 bg-slate-400/10',
  3: 'text-amber-600 bg-amber-600/10',
};

function getMedalClass(rank: number): string {
  return MEDAL_COLORS[rank] ?? 'bg-[rgb(var(--bg-elevated))] text-[rgb(var(--text-secondary))]';
}

// ─────────────────────────────────────────────
// FORMAT VALUE
// ─────────────────────────────────────────────

function formatValue(item: RankingItem): string {
  if (item.value_formatado) return item.value_formatado;
  switch (item.unit) {
    case 'BRL': return formatCurrency(item.value);
    case 'percent': return `${item.value.toFixed(1)}%`;
    default: return formatNumber(item.value);
  }
}

// ─────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────

export const RankingTable = memo(function RankingTable({
  items,
  title,
  maxItems = 10,
  showProgressBar = true,
  className,
}: RankingTableProps) {
  const visible = items.slice(0, maxItems);
  const maxValue = Math.max(...visible.map((i) => i.value), 1);

  if (!items?.length) {
    return (
      <div className="flex items-center justify-center h-full text-sm" style={{ color: 'rgb(var(--text-muted))' }}>
        Nenhum dado disponível
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-2 w-full', className)} role="table" aria-label={title}>
      {title && (
        <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'rgb(var(--text-muted))' }}>
          {title}
        </p>
      )}

      {visible.map((item, i) => (
        <motion.div
          key={`${item.rank}-${item.label}`}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05, duration: 0.25 }}
          className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-[rgb(var(--bg-elevated)/0.5)]"
          role="row"
          aria-label={`${item.rank}. ${item.label}: ${formatValue(item)}`}
        >
          {/* Rank badge */}
          <div
            className={cn(
              'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold',
              getMedalClass(item.rank),
            )}
            aria-hidden="true"
          >
            {item.rank}
          </div>

          {/* Label + bar */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium truncate" style={{ color: 'rgb(var(--text-primary))' }}>{item.label}</p>
              <div className="flex items-center gap-2 shrink-0">
                {item.badge && (
                  <span className="rounded px-1.5 py-0.5 text-[10px] font-medium bg-[#6C63FF]/20 text-[#9C95FF]">
                    {item.badge}
                  </span>
                )}
                <p className="text-sm font-semibold tabular-nums" style={{ color: 'rgb(var(--text-primary))' }}>
                  {formatValue(item)}
                </p>
                {item.percentage !== undefined && (
                  <p className="text-xs w-10 text-right" style={{ color: 'rgb(var(--text-muted))' }}>
                    {item.percentage.toFixed(1)}%
                  </p>
                )}
              </div>
            </div>

            {/* Progress bar */}
            {showProgressBar && (
              <div className="mt-1 h-1 w-full rounded-full overflow-hidden" style={{ background: 'rgb(var(--bg-elevated))' }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(item.value / maxValue) * 100}%` }}
                  transition={{ delay: i * 0.05 + 0.1, duration: 0.5, ease: 'easeOut' }}
                  className="h-full rounded-full bg-gradient-to-r from-[#6C63FF] to-[#00D2D3]"
                />
              </div>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
});
