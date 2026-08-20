'use client';

/**
 * ============================================================
 * LUMINA AI — Component Library Status Components
 * ============================================================
 * Skeleton loaders, empty states, and error states used
 * throughout the Dashboard Runtime Engine.
 * ============================================================
 */

import React from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, BarChart3, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─────────────────────────────────────────────
// SKELETON LOADER
// ─────────────────────────────────────────────

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ className, style }: SkeletonProps) {
  return (
    <div
      className={cn('animate-pulse rounded-lg', className)}
      style={{ background: 'rgb(var(--bg-elevated) / 0.8)', ...style }}
      aria-hidden="true"
    />
  );
}

interface SkeletonCardProps {
  /** Grid rows height (1 row = 100px) */
  rows?: number;
  className?: string;
}

export function SkeletonCard({ rows = 4, className }: SkeletonCardProps) {
  const heightPx = rows * 100 + (rows - 1) * 16;

  return (
    <div
      className={cn(
        'rounded-xl border p-4 overflow-hidden',
        className,
      )}
      style={{
        minHeight: heightPx,
        background: 'rgb(var(--bg-surface) / 0.75)',
        borderColor: 'rgb(var(--border) / 0.55)',
      }}
      aria-busy="true"
      aria-label="Carregando componente..."
      role="status"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-16 ml-auto" />
      </div>
      {/* Body */}
      <Skeleton className="w-full" style={{ height: heightPx - 80 }} />
      {/* Footer */}
      <div className="flex gap-2 mt-3">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-3 w-12" />
      </div>
    </div>
  );
}

/**
 * Full grid skeleton while dashboard is loading.
 */
export function SkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div
      className="grid grid-cols-12 gap-4 w-full"
      aria-busy="true"
      aria-label="Carregando dashboard..."
      role="status"
    >
      {/* KPI row: 4 cards × 3 cols */}
      {[3, 3, 3, 3].map((cols, i) => (
        <div key={`kpi-${i}`} style={{ gridColumn: `span ${cols}` }}>
          <SkeletonCard rows={2} />
        </div>
      ))}
      {/* Chart row */}
      {count > 4 && (
        <>
          <div style={{ gridColumn: 'span 6' }}>
            <SkeletonCard rows={4} />
          </div>
          <div style={{ gridColumn: 'span 6' }}>
            <SkeletonCard rows={4} />
          </div>
        </>
      )}
      {/* Table row */}
      {count > 6 && (
        <div style={{ gridColumn: 'span 12' }}>
          <SkeletonCard rows={5} />
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// EMPTY STATE
// ─────────────────────────────────────────────

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title = 'Nenhum dado disponível',
  description = 'Não há informações para exibir neste momento.',
  action,
  className,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex flex-col items-center justify-center gap-4 rounded-xl',
        'border p-8 text-center',
        className,
      )}
      style={{
        background: 'rgb(var(--bg-surface) / 0.72)',
        borderColor: 'rgb(var(--border) / 0.55)',
      }}
      role="status"
      aria-label={title}
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-full" style={{ background: 'rgb(var(--bg-elevated) / 0.75)' }}>
        <BarChart3 className="h-7 w-7" style={{ color: 'rgb(var(--text-muted))' }} />
      </div>
      <div>
        <p className="text-sm font-medium" style={{ color: 'rgb(var(--text-secondary))' }}>{title}</p>
        {description && (
          <p className="mt-1 text-xs" style={{ color: 'rgb(var(--text-muted))' }}>{description}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </motion.div>
  );
}

// ─────────────────────────────────────────────
// ERROR STATE
// ─────────────────────────────────────────────

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = 'Erro ao carregar componente',
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        'flex flex-col items-center justify-center gap-4 rounded-xl',
        'border border-red-500/20 bg-red-500/[0.06] p-8 text-center',
        className,
      )}
      role="alert"
      aria-label={title}
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10">
        <AlertCircle className="h-7 w-7 text-red-400" />
      </div>
      <div>
        <p className="text-sm font-medium text-red-300">{title}</p>
        {message && (
          <p className="mt-1 text-xs text-red-400/70">{message}</p>
        )}
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-medium
            text-red-300 border border-red-500/30 hover:bg-red-500/10 transition-colors"
          aria-label="Tentar novamente"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Tentar novamente
        </button>
      )}
    </motion.div>
  );
}

// ─────────────────────────────────────────────
// LOADING SPINNER
// ─────────────────────────────────────────────

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  className?: string;
}

const SPINNER_SIZES = {
  sm: 'h-4 w-4 border-2',
  md: 'h-8 w-8 border-2',
  lg: 'h-12 w-12 border-[3px]',
};

export function LoadingSpinner({
  size = 'md',
  label = 'Carregando...',
  className,
}: LoadingSpinnerProps) {
  return (
    <div
      className={cn('flex flex-col items-center justify-center gap-3', className)}
      role="status"
      aria-label={label}
    >
      <div
        className={cn(
          'animate-spin rounded-full border-white/10 border-t-[#6C63FF]',
          SPINNER_SIZES[size],
        )}
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}
