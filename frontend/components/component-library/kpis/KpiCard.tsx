'use client';

/**
 * ============================================================
 * LUMINA AI — Enterprise KPI Card (ECE Component)
 * ============================================================
 * Renders a single KPI from the ADE/ECE payload.
 * Supports: animated counter, sparkline, trend badge,
 * units (BRL, percent, count, score).
 *
 * Uses the existing EKPICards chart infrastructure internally.
 * ============================================================
 */

import React, { useEffect, useRef, useState, memo } from 'react';
import ReactECharts from 'echarts-for-react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus, DollarSign, BarChart2, Users, Star } from 'lucide-react';
import { cn, formatCurrency, formatNumber, formatPercent } from '@/lib/utils';

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────

export interface KPICardData {
  id: string;
  label: string;
  value: number;
  value_formatado?: string;
  unit: 'BRL' | 'percent' | 'count' | 'score';
  trend: 'up' | 'down' | 'stable';
  trend_value: number;
  trend_label?: string;
  icon?: 'currency' | 'chart' | 'users' | 'star' | 'ticket';
  sparkline?: number[];
}

interface KpiCardProps {
  data: KPICardData;
  className?: string;
  animate?: boolean;
}

// ─────────────────────────────────────────────
// ICON MAP
// ─────────────────────────────────────────────

const ICONS: Record<string, React.FC<{ className?: string }>> = {
  currency: DollarSign,
  chart:    BarChart2,
  users:    Users,
  star:     Star,
  ticket:   Star,
};

// ─────────────────────────────────────────────
// ANIMATED COUNTER
// ─────────────────────────────────────────────

function useCountUp(target: number, durationMs = 800): number {
  const [current, setCurrent] = useState(0);
  const startRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    startRef.current = null;
    function step(ts: number) {
      if (startRef.current === null) startRef.current = ts;
      const progress = Math.min((ts - startRef.current) / durationMs, 1);
      // easeOutCubic
      const ease = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(ease * target));
      if (progress < 1) rafRef.current = requestAnimationFrame(step);
    }
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [target, durationMs]);

  return current;
}

// ─────────────────────────────────────────────
// FORMAT VALUE
// ─────────────────────────────────────────────

function formatKPIValue(value: number, unit: KPICardData['unit'], formatado?: string): string {
  if (formatado) return formatado;
  switch (unit) {
    case 'BRL': return formatCurrency(value);
    case 'percent': return formatPercent(value);
    case 'count': return formatNumber(value);
    case 'score': return value.toFixed(1);
    default: return String(value);
  }
}

// ─────────────────────────────────────────────
// SPARKLINE
// ─────────────────────────────────────────────

const SPARKLINE_COLOR_MAP: Record<KPICardData['trend'], string> = {
  up:     '#22c55e',
  down:   '#ef4444',
  stable: '#6C63FF',
};

function KPISparkline({ data, trend }: { data: number[]; trend: KPICardData['trend'] }) {
  const color = SPARKLINE_COLOR_MAP[trend];

  const option = {
    animation: true,
    animationDuration: 800,
    grid: { top: 0, right: 0, bottom: 0, left: 0 },
    xAxis: { type: 'category', show: false, data: data.map((_, i) => i) },
    yAxis: { type: 'value', show: false },
    series: [{
      type: 'line',
      data,
      smooth: true,
      symbol: 'none',
      lineStyle: { color, width: 2 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: `${color}33` },
            { offset: 1, color: `${color}00` },
          ],
        },
      },
    }],
    tooltip: { show: false },
  };

  return (
    <ReactECharts
      option={option}
      style={{ height: 48, width: '100%' }}
      opts={{ renderer: 'canvas' }}
      notMerge
    />
  );
}

// ─────────────────────────────────────────────
// TREND BADGE
// ─────────────────────────────────────────────

const TREND_STYLES: Record<KPICardData['trend'], { text: string; icon: React.FC<{ className?: string }> }> = {
  up:     { text: 'text-green-400', icon: TrendingUp },
  down:   { text: 'text-red-400',   icon: TrendingDown },
  stable: { text: '',  icon: Minus },
};

function TrendBadge({ trend, trend_value, trend_label }: Pick<KPICardData, 'trend' | 'trend_value' | 'trend_label'>) {
  const normalizedTrend = (trend || 'stable').toLowerCase() as KPICardData['trend'];
  const style = TREND_STYLES[normalizedTrend] || TREND_STYLES.stable;
  const { text, icon: Icon } = style;
  const sign = normalizedTrend === 'up' ? '+' : normalizedTrend === 'down' ? '-' : '';
  const displayValue = typeof trend_value === 'number' ? trend_value : 0;
  return (
    <div
      className={cn('flex items-center gap-1 text-xs font-medium', text)}
      style={normalizedTrend === 'stable' ? { color: 'rgb(var(--text-muted))' } : undefined}
    >
      <Icon className="h-3.5 w-3.5" />
      <span>{sign}{Math.abs(displayValue).toFixed(1)}%</span>
      {trend_label && <span className="font-normal" style={{ color: 'rgb(var(--text-muted))' }}>{trend_label}</span>}
    </div>
  );
}

// ─────────────────────────────────────────────
// KPI CARD
// ─────────────────────────────────────────────

export const KpiCard = memo(function KpiCard({
  data,
  className,
  animate = true,
}: KpiCardProps) {
  const safeValue = Number.isFinite(Number(data?.value)) ? Number(data.value) : 0;
  const safeUnit = ['BRL', 'percent', 'count', 'score'].includes(data?.unit)
    ? data.unit
    : 'count';
  const safeTrend = ['up', 'down', 'stable'].includes(data?.trend)
    ? data.trend
    : 'stable';
  const safeTrendValue = Number.isFinite(Number(data?.trend_value)) ? Number(data.trend_value) : 0;
  const safeLabel = typeof data?.label === 'string' && data.label.trim()
    ? data.label
    : 'Indicador';

  const animatedValue = useCountUp(animate ? safeValue : 0);
  const displayValue = animate
    ? formatKPIValue(animatedValue, safeUnit)
    : formatKPIValue(safeValue, safeUnit, data?.value_formatado);

  const IconComponent = data?.icon ? ICONS[data.icon] : null;

  return (
    <motion.div
      initial={animate ? { opacity: 0, y: 8 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        'flex flex-col justify-between rounded-xl h-full',
        'border',
        'p-4 overflow-hidden',
        className,
      )}
      style={{
        background: 'rgb(var(--bg-elevated) / 0.35)',
        borderColor: 'rgb(var(--border) / 0.5)',
      }}
      role="article"
      aria-label={`KPI: ${safeLabel}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wider line-clamp-2" style={{ color: 'rgb(var(--text-muted))' }}>
          {safeLabel}
        </p>
        {IconComponent && (
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#6C63FF]/10">
            <IconComponent className="h-3.5 w-3.5 text-[#6C63FF]" />
          </div>
        )}
      </div>

      {/* Value */}
      <div className="my-2">
        <p
          className="text-2xl font-bold tracking-tight tabular-nums"
          style={{ color: 'rgb(var(--text-primary))' }}
          aria-live="polite"
        >
          {displayValue}
        </p>
      </div>

      {/* Sparkline */}
      {data?.sparkline && data.sparkline.length > 1 && (
        <div className="mb-1 -mx-1">
          <KPISparkline data={data.sparkline} trend={safeTrend} />
        </div>
      )}

      {/* Trend */}
      <TrendBadge
        trend={safeTrend}
        trend_value={safeTrendValue}
        trend_label={data?.trend_label}
      />
    </motion.div>
  );
});

// ─────────────────────────────────────────────
// KPI GRID (multiple KPI cards)
// ─────────────────────────────────────────────

interface KpiGridProps {
  kpis: KPICardData[];
  className?: string;
}

export function KpiGrid({ kpis, className }: KpiGridProps) {
  if (!kpis?.length) return null;

  // Adaptive columns: 1→2→3→5 based on count
  const colClass =
    kpis.length === 1 ? 'grid-cols-1' :
    kpis.length === 2 ? 'grid-cols-2' :
    kpis.length <= 4 ? 'grid-cols-2 sm:grid-cols-4' :
    'grid-cols-2 sm:grid-cols-3 lg:grid-cols-5';

  return (
    <div className={cn('grid gap-4 w-full', colClass, className)}>
      {kpis.map((kpi, i) => (
        <motion.div
          key={kpi.id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.07, duration: 0.3 }}
          className="h-full"
        >
          <KpiCard data={kpi} />
        </motion.div>
      ))}
    </div>
  );
}
