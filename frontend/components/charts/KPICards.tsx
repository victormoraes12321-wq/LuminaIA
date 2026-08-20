'use client'

import { motion } from 'framer-motion'
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { TrendBadge } from '@/components/ui/Badge'
import type { ChartDataKPI, KPIItem } from '@/types/lumina'

// ── Icon Map ──────────────────────────────────────────────────

const ICON_GLYPHS: Record<KPIItem['icon'], string> = {
  currency: '₿',
  chart:    '📊',
  users:    '👥',
  star:     '⭐',
  ticket:   '🎫',
}

const ICON_BG: Record<KPIItem['icon'], string> = {
  currency: 'from-violet-500/20 to-violet-600/10',
  chart:    'from-teal-400/20 to-teal-500/10',
  users:    'from-blue-500/20 to-blue-600/10',
  star:     'from-yellow-400/20 to-orange-400/10',
  ticket:   'from-pink-500/20 to-rose-400/10',
}

// ── Sparkline ─────────────────────────────────────────────────

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const pts = data.map((v) => ({ v }))
  return (
    <ResponsiveContainer width="100%" height={36}>
      <LineChart data={pts} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <Tooltip content={() => null} />
        <Line
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive
          animationDuration={800}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Single KPI Card ───────────────────────────────────────────

import type { Variants } from 'framer-motion'

const cardVariants: Variants = {
  hidden:  { opacity: 0, y: 20, scale: 0.96 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      delay: (i as number) * 0.07,
      duration: 0.45,
      ease: 'easeOut' as const,
    },
  }),
}

function KPICard({ item, index }: { item: KPIItem; index: number }) {
  const trendColor =
    item.trend === 'up'
      ? '#34d399'
      : item.trend === 'down'
        ? '#f87171'
        : '#a1a1aa'

  const TrendIcon =
    item.trend === 'up'
      ? TrendingUp
      : item.trend === 'down'
        ? TrendingDown
        : Minus

  return (
    <motion.div
      variants={cardVariants}
      custom={index}
      initial="hidden"
      animate="visible"
      className={cn(
        'lumina-card p-5 flex flex-col gap-3 group cursor-default',
        'hover:border-lumina-500/30',
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div
          className={cn(
            'w-9 h-9 rounded-xl flex items-center justify-center',
            'bg-gradient-to-br text-base flex-shrink-0 shadow-inner-white',
            ICON_BG[item.icon],
          )}
        >
          {ICON_GLYPHS[item.icon]}
        </div>
        <TrendBadge value={item.trend_value} suffix={item.unit === 'percent' ? ' pp' : '%'} />
      </div>

      {/* Value */}
      <div>
        <p
          className="text-2xl font-bold tracking-tight leading-none"
          style={{ color: 'rgb(var(--text-primary))' }}
        >
          {item.value_formatado}
        </p>
        <p className="text-xs mt-1.5 font-medium" style={{ color: 'rgb(var(--text-muted))' }}>
          {item.label}
        </p>
      </div>

      {/* Sparkline */}
      {item.sparkline && item.sparkline.length > 1 && (
        <div className="opacity-80 group-hover:opacity-100 transition-opacity duration-300">
          <Sparkline data={item.sparkline} color={trendColor} />
        </div>
      )}

      {/* Trend label */}
      <div className="flex items-center gap-1.5 mt-auto">
        <TrendIcon size={11} style={{ color: trendColor }} />
        <p className="text-[11px]" style={{ color: 'rgb(var(--text-muted))' }}>
          {item.trend_label}
        </p>
      </div>
    </motion.div>
  )
}

// ── KPI Cards Grid ────────────────────────────────────────────

interface KPICardsProps {
  data: ChartDataKPI
}

export function KPICards({ data }: KPICardsProps) {
  return (
    <div className="space-y-3">
      {/* Period label */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium" style={{ color: 'rgb(var(--text-muted))' }}>
          Período:
        </span>
        <span className="text-xs font-semibold" style={{ color: 'rgb(var(--text-secondary))' }}>
          {data.periodo}
        </span>
      </div>

      {/* Responsive grid */}
      <div
        className="grid gap-3.5"
        style={{
          gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, 200px), 1fr))`,
        }}
      >
        {data.kpis.map((kpi, i) => (
          <KPICard key={kpi.id} item={kpi} index={i} />
        ))}
      </div>
    </div>
  )
}
