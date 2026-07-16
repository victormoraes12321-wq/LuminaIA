'use client'

/**
 * EKPICards — Painel de KPIs com Sparklines ECharts Nativas
 * Substitui recharts por ECharts nas sparklines para consistência e performance.
 * Recursos: animação de contador para valores, sparkline canvas nativa,
 * gradiente de cor baseado no trend, hover effects premium.
 */

import ReactECharts from 'echarts-for-react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import { TrendBadge } from '@/components/ui/Badge'
import type { ChartDataKPI, KPIItem } from '@/types/lumina'
import type { Variants } from 'framer-motion'

// ── Ícones de Métricas ─────────────────────────────────────────

const ICON_GLYPHS: Record<KPIItem['icon'], string> = {
  currency: '💰',
  chart:    '📈',
  users:    '👥',
  star:     '⭐',
  ticket:   '🏷️',
}

const ICON_BG: Record<KPIItem['icon'], string> = {
  currency: 'from-violet-500/20 to-violet-600/10',
  chart:    'from-teal-400/20 to-teal-500/10',
  users:    'from-blue-500/20 to-blue-600/10',
  star:     'from-yellow-400/20 to-orange-400/10',
  ticket:   'from-pink-500/20 to-rose-400/10',
}

// ── Sparkline via ECharts ──────────────────────────────────────

function ESparkline({ data, color }: { data: number[]; color: string }) {
  const option = {
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 1000,
    animationEasing: 'cubicOut' as const,
    grid: { top: 2, right: 2, bottom: 2, left: 2 },
    xAxis: { type: 'category' as const, show: false, boundaryGap: false },
    yAxis: { type: 'value' as const, show: false },
    series: [
      {
        type: 'line',
        data,
        smooth: 0.5,
        symbol: 'none',
        lineStyle: { color, width: 1.5 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: color + '50' },
              { offset: 1, color: color + '05' },
            ],
          },
        },
      },
    ],
  }

  return (
    <ReactECharts
      option={option}
      style={{ height: 36, width: '100%' }}
      opts={{ renderer: 'canvas' }}
      notMerge
    />
  )
}

// ── Animação de Contador ───────────────────────────────────────

function useCountUp(target: number, duration = 900) {
  const [value, setValue] = useState(0)
  const startRef = useRef<number | null>(null)
  const rafRef = useRef<number>(0)

  useEffect(() => {
    startRef.current = null
    const step = (ts: number) => {
      if (!startRef.current) startRef.current = ts
      const progress = Math.min((ts - startRef.current) / duration, 1)
      // easeOutCubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(target * eased)
      if (progress < 1) rafRef.current = requestAnimationFrame(step)
    }
    rafRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, duration])

  return value
}

// ── Card Individual ────────────────────────────────────────────

const cardVariants: Variants = {
  hidden:  { opacity: 0, y: 20, scale: 0.96 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { delay: i * 0.07, duration: 0.45, ease: 'easeOut' },
  }),
}

function KPICard({ item, index }: { item: KPIItem; index: number }) {
  const trendColor =
    item.trend === 'up'   ? '#34d399'
    : item.trend === 'down' ? '#f87171'
    : '#a1a1aa'

  const TrendIcon =
    item.trend === 'up'   ? TrendingUp
    : item.trend === 'down' ? TrendingDown
    : Minus

  // Animate numeric value for currency/number units
  const animated = useCountUp(
    typeof item.value === 'number' ? item.value : 0,
    800
  )

  const formattedAnimated = (() => {
    if (item.unit === 'BRL') {
      return `R$ ${animated.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
    if (item.unit === 'percent') {
      return `${animated.toFixed(1)}%`
    }
    if (item.unit === 'score') {
      return animated.toFixed(1)
    }
    if (item.unit === 'count') {
      return Math.round(animated).toLocaleString('pt-BR')
    }
    return item.value_formatado
  })()

  return (
    <motion.div
      variants={cardVariants}
      custom={index}
      initial="hidden"
      animate="visible"
      className={cn(
        'lumina-card p-5 flex flex-col gap-3 group cursor-default',
        'hover:border-lumina-500/30 transition-all duration-300',
        'hover:shadow-[0_0_24px_rgba(108,99,255,0.12)]',
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div
          className={cn(
            'w-9 h-9 rounded-xl flex items-center justify-center text-base flex-shrink-0',
            'bg-gradient-to-br shadow-inner',
            ICON_BG[item.icon],
          )}
        >
          {ICON_GLYPHS[item.icon]}
        </div>
        <TrendBadge value={item.trend_value} suffix={item.unit === 'percent' ? ' pp' : '%'} />
      </div>

      {/* Valor animado */}
      <div>
        <p
          className="text-2xl font-bold tracking-tight leading-none tabular-nums"
          style={{ color: 'rgb(var(--text-primary))' }}
        >
          {formattedAnimated}
        </p>
        <p className="text-xs mt-1.5 font-medium" style={{ color: 'rgb(var(--text-muted))' }}>
          {item.label}
        </p>
      </div>

      {/* Sparkline ECharts */}
      {item.sparkline && item.sparkline.length > 1 && (
        <div className="opacity-70 group-hover:opacity-100 transition-opacity duration-300 -mx-1">
          <ESparkline data={item.sparkline} color={trendColor} />
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

// ── Grid de KPIs ───────────────────────────────────────────────

interface EKPICardsProps {
  data: ChartDataKPI
}

export function EKPICards({ data }: EKPICardsProps) {
  return (
    <div className="space-y-3">
      {/* Período */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium" style={{ color: 'rgb(var(--text-muted))' }}>
          Período:
        </span>
        <span className="text-xs font-semibold" style={{ color: 'rgb(var(--text-secondary))' }}>
          {data.periodo}
        </span>
        <span
          className="ml-auto text-[10px] font-medium px-2 py-0.5 rounded-full"
          style={{
            background: 'rgba(108,99,255,0.1)',
            color: 'rgb(108,99,255)',
            border: '1px solid rgba(108,99,255,0.2)',
          }}
        >
          Atualizado em {data.gerado_em}
        </span>
      </div>

      {/* Grade responsiva */}
      <div
        className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
      >
        {data.kpis.map((kpi, i) => (
          <KPICard key={kpi.id} item={kpi} index={i} />
        ))}
      </div>
    </div>
  )
}
