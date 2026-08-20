'use client'

import {
  DollarSign,
  Package,
  Users,
  UserCheck,
  Receipt,
  Layers,
  Building2,
  TrendingUp,
  Maximize2,
  ArrowUpRight,
  Sparkles,
  Zap,
  ShieldCheck,
} from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import type { ExecutiveKpiData, MetricType, FocusWidgetState } from './types'

interface InteractiveKpiGridProps {
  data: ExecutiveKpiData
  loading?: boolean
  selectedMetric: MetricType
  onSelectMetric: (metric: MetricType) => void
  onOpenFocusMode?: (widgetState: FocusWidgetState) => void
}

export function InteractiveKpiGrid({
  data,
  loading = false,
  selectedMetric,
  onSelectMetric,
  onOpenFocusMode,
}: InteractiveKpiGridProps) {
  const cards = [
    {
      id: 'faturamento' as const,
      label: 'Faturamento Total',
      value: data.faturamento_formatted,
      secondary: `Ticket Médio: ${data.ticket_medio_formatted}`,
      detail: 'Receita líquida consolidada',
      isHero: true,
      icon: DollarSign,
      color: 'amber',
      borderClass: 'border-amber-500/40 hover:border-amber-400',
      activeBorder: 'border-amber-400 ring-2 ring-amber-500/40 shadow-[0_0_30px_rgba(245,158,11,0.25)]',
      gradientBg: 'from-amber-500/15 via-zinc-900/90 to-zinc-950',
      textAccent: 'text-amber-400',
      iconBg: 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-[0_0_15px_rgba(245,158,11,0.3)]',
      sparklinePoints: [25, 40, 35, 55, 60, 48, 75, 90],
    },
    {
      id: 'quantidade' as const,
      label: 'Volume de Itens',
      value: data.quantidade_formatted,
      secondary: 'Unidades faturadas no período',
      detail: 'Volume físico comercializado',
      isHero: false,
      icon: Package,
      color: 'cyan',
      borderClass: 'border-cyan-500/30 hover:border-cyan-400',
      activeBorder: 'border-cyan-400 ring-2 ring-cyan-500/40 shadow-[0_0_25px_rgba(6,182,212,0.25)]',
      gradientBg: 'from-cyan-500/10 via-zinc-900/90 to-zinc-950',
      textAccent: 'text-cyan-400',
      iconBg: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.3)]',
      sparklinePoints: [30, 45, 40, 60, 55, 65, 70, 85],
    },
    {
      id: 'ticket' as const,
      label: 'Ticket Médio',
      value: data.ticket_medio_formatted,
      secondary: `${data.notas_formatted} Notas Emitidas`,
      detail: 'Média faturada por NF-e',
      isHero: false,
      icon: TrendingUp,
      color: 'emerald',
      borderClass: 'border-emerald-500/30 hover:border-emerald-400',
      activeBorder: 'border-emerald-400 ring-2 ring-emerald-500/40 shadow-[0_0_25px_rgba(16,185,129,0.25)]',
      gradientBg: 'from-emerald-500/10 via-zinc-900/90 to-zinc-950',
      textAccent: 'text-emerald-400',
      iconBg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-[0_0_15px_rgba(16,185,129,0.3)]',
      sparklinePoints: [50, 52, 58, 62, 60, 68, 72, 78],
    },
    {
      id: 'notas' as const,
      label: 'Notas & Pedidos',
      value: `${data.notas_formatted} NF-e`,
      secondary: `${data.pedidos_formatted} Pedidos Registrados`,
      detail: 'Documentos fiscais & pedidos',
      isHero: false,
      icon: Receipt,
      color: 'teal',
      borderClass: 'border-teal-500/30 hover:border-teal-400',
      activeBorder: 'border-teal-400 ring-2 ring-teal-500/40 shadow-[0_0_25px_rgba(20,184,166,0.25)]',
      gradientBg: 'from-teal-500/10 via-zinc-900/90 to-zinc-950',
      textAccent: 'text-teal-400',
      iconBg: 'bg-teal-500/20 text-teal-300 border-teal-500/40 shadow-[0_0_15px_rgba(20,184,166,0.3)]',
      sparklinePoints: [40, 48, 52, 58, 64, 62, 70, 80],
    },
    {
      id: 'vendedores' as const,
      label: 'Equipe Comercial',
      value: `${data.vendedores_ativos} Vendedores`,
      secondary: 'Representantes ativos com vendas',
      detail: 'Cobertura de vendas ativa',
      isHero: false,
      icon: Users,
      color: 'indigo',
      borderClass: 'border-indigo-500/30 hover:border-indigo-400',
      activeBorder: 'border-indigo-400 ring-2 ring-indigo-500/40 shadow-[0_0_25px_rgba(99,102,241,0.25)]',
      gradientBg: 'from-indigo-500/10 via-zinc-900/90 to-zinc-950',
      textAccent: 'text-indigo-400',
      iconBg: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 shadow-[0_0_15px_rgba(99,102,241,0.3)]',
      sparklinePoints: [35, 38, 38, 40, 39, 40, 40, 40],
    },
    {
      id: 'clientes' as const,
      label: 'Clientes Atendidos',
      value: `${data.clientes_ativos} Compradores`,
      secondary: 'Compradores ativos no período',
      detail: 'Base de clientes com compras',
      isHero: false,
      icon: UserCheck,
      color: 'purple',
      borderClass: 'border-purple-500/30 hover:border-purple-400',
      activeBorder: 'border-purple-400 ring-2 ring-purple-500/40 shadow-[0_0_25px_rgba(168,85,247,0.25)]',
      gradientBg: 'from-purple-500/10 via-zinc-900/90 to-zinc-950',
      textAccent: 'text-purple-400',
      iconBg: 'bg-purple-500/20 text-purple-300 border-purple-500/40 shadow-[0_0_15px_rgba(168,85,247,0.3)]',
      sparklinePoints: [45, 55, 60, 68, 72, 80, 85, 92],
    },
    {
      id: 'produtos' as const,
      label: 'Mix de Produtos',
      value: `${data.produtos_distintos} Produtos`,
      secondary: 'SKUs com movimentação',
      detail: 'Variedade do catálogo vendido',
      isHero: false,
      icon: Layers,
      color: 'rose',
      borderClass: 'border-rose-500/30 hover:border-rose-400',
      activeBorder: 'border-rose-400 ring-2 ring-rose-500/40 shadow-[0_0_25px_rgba(244,63,94,0.25)]',
      gradientBg: 'from-rose-500/10 via-zinc-900/90 to-zinc-950',
      textAccent: 'text-rose-400',
      iconBg: 'bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-[0_0_15px_rgba(244,63,94,0.3)]',
      sparklinePoints: [60, 65, 70, 75, 80, 82, 88, 95],
    },
    {
      id: 'filiais' as const,
      label: 'Unidades Ativas',
      value: `${data.filiais_ativas} Filiais`,
      secondary: 'Todas as unidades operacionais',
      detail: 'Rede com movimentação no período',
      isHero: false,
      icon: Building2,
      color: 'blue',
      borderClass: 'border-blue-500/30 hover:border-blue-400',
      activeBorder: 'border-blue-400 ring-2 ring-blue-500/40 shadow-[0_0_25px_rgba(59,130,246,0.25)]',
      gradientBg: 'from-blue-500/10 via-zinc-900/90 to-zinc-950',
      textAccent: 'text-blue-400',
      iconBg: 'bg-blue-500/20 text-blue-300 border-blue-500/40 shadow-[0_0_15px_rgba(59,130,246,0.3)]',
      sparklinePoints: [5, 5, 5, 5, 5, 5, 5, 5],
    },
  ]

  const handleCardClick = (cardId: MetricType, cardLabel: string) => {
    onSelectMetric(cardId)
    if (onOpenFocusMode) {
      onOpenFocusMode({
        widgetId: `kpi-focus-${cardId}`,
        title: `Workspace Analítico: ${cardLabel}`,
        dimension: cardId,
        metric: cardId,
        data: data,
      })
    }
  }

  return (
    <section aria-label="Visão Geral de Indicadores" className="space-y-3">
      {/* Refined Business-Friendly Section Header */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2.5">
          <span className="flex h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[rgb(var(--text-secondary))] flex items-center gap-2">
            <span>Visão Geral</span>
            <span className="text-[11px] font-normal text-[rgb(var(--text-muted))]">
              • Principais Indicadores do Período
            </span>
          </h2>
        </div>
        <span className="text-[11px] text-[rgb(var(--text-muted))] hidden sm:inline-block">
          Clique no card para abrir o detalhamento analítico
        </span>
      </div>

      {/* Balanced 4-Column Grid (Guarantees 2 Rows of 4 cards on Desktop, 4 Rows of 2 cards on Tablet, 0 Orphans) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {cards.map((card) => {
          const isSelected = selectedMetric === card.id
          const Icon = card.icon

          // Generate SVG Sparkline Path
          const maxVal = Math.max(...card.sparklinePoints)
          const minVal = Math.min(...card.sparklinePoints)
          const range = maxVal - minVal || 1
          const pointsStr = card.sparklinePoints
            .map((val, idx) => {
              const x = (idx / (card.sparklinePoints.length - 1)) * 64
              const y = 20 - ((val - minVal) / range) * 16
              return `${x.toFixed(1)},${y.toFixed(1)}`
            })
            .join(' ')

          return (
            <motion.div
              key={card.id}
              role="button"
              tabIndex={0}
              data-testid={`kpi-card-${card.id}`}
              whileHover={{ y: -2, scale: 1.008 }}
              whileTap={{ scale: 0.99 }}
              onClick={() => handleCardClick(card.id, card.label)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  handleCardClick(card.id, card.label)
                }
              }}
              className={cn(
                'group relative flex flex-col justify-between p-4 rounded-2xl border transition-all duration-200 cursor-pointer overflow-hidden backdrop-blur-xl select-none',
                'bg-gradient-to-b',
                card.gradientBg,
                isSelected ? card.activeBorder : card.borderClass,
                'shadow-[0_8px_24px_rgba(0,0,0,0.4)] hover:shadow-[0_12px_32px_rgba(0,0,0,0.6)]'
              )}
            >
              {/* Subtle top edge luminous line */}
              <div
                className={cn(
                  'absolute top-0 left-4 right-4 h-[1.5px] bg-gradient-to-r from-transparent to-transparent opacity-70 transition-opacity',
                  card.id === 'faturamento' && 'via-amber-400',
                  card.id === 'quantidade' && 'via-cyan-400',
                  card.id === 'ticket' && 'via-emerald-400',
                  card.id === 'notas' && 'via-teal-400',
                  card.id === 'vendedores' && 'via-indigo-400',
                  card.id === 'clientes' && 'via-purple-400',
                  card.id === 'produtos' && 'via-rose-400',
                  card.id === 'filiais' && 'via-blue-400',
                  isSelected ? 'opacity-100 h-[2px]' : 'group-hover:opacity-100'
                )}
              />

              {/* Card Header */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <div
                    className={cn(
                      'flex items-center justify-center w-8 h-8 rounded-xl border transition-transform duration-200 group-hover:scale-105',
                      card.iconBg
                    )}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-[rgb(var(--text-secondary))] group-hover:text-white transition-colors block">
                      {card.label}
                    </span>
                    <span className="text-[10px] text-[rgb(var(--text-muted))] block leading-tight">
                      {card.detail}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    aria-label={`Expandir ${card.label}`}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleCardClick(card.id, card.label)
                    }}
                    className="p-1 rounded-lg text-zinc-500 hover:text-white hover:bg-white/10 transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <Maximize2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Metric Value Display with Micro-Sparkline */}
              <div className="my-3 flex items-end justify-between gap-2">
                <div className="space-y-0.5">
                  {loading ? (
                    <div className="h-7 w-28 bg-white/10 animate-pulse rounded-lg" />
                  ) : (
                    <span
                      className={cn(
                        'text-xl sm:text-2xl font-bold tracking-tight text-white block font-mono tabular-nums',
                        card.id === 'faturamento' && 'text-amber-300 font-extrabold text-2xl sm:text-3xl'
                      )}
                    >
                      {card.value}
                    </span>
                  )}
                  <span className="text-[11px] text-zinc-400 block truncate">
                    {card.secondary}
                  </span>
                </div>

                {/* Micro Sparkline Trend Graphic */}
                <div className="w-16 h-6 shrink-0 opacity-70 group-hover:opacity-100 transition-opacity">
                  <svg viewBox="0 0 64 20" className="w-full h-full overflow-visible">
                    <polyline
                      fill="none"
                      stroke={
                        card.id === 'faturamento'
                          ? '#f59e0b'
                          : card.id === 'quantidade'
                            ? '#06b6d4'
                            : card.id === 'ticket'
                              ? '#10b981'
                              : card.id === 'notas'
                                ? '#14b8a6'
                                : card.id === 'vendedores'
                                  ? '#6366f1'
                                  : card.id === 'clientes'
                                    ? '#a855f7'
                                    : card.id === 'produtos'
                                      ? '#f43f5e'
                                      : '#3b82f6'
                      }
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      points={pointsStr}
                    />
                  </svg>
                </div>
              </div>

              {/* Card Footer: Context Action */}
              <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[10px]">
                <span
                  className={cn(
                    'font-medium transition-colors',
                    isSelected ? card.textAccent : 'text-zinc-400 group-hover:text-zinc-200'
                  )}
                >
                  {isSelected ? '● Visualização Selecionada' : 'Explorar dados'}
                </span>
                <span className="flex items-center gap-0.5 text-zinc-500 group-hover:text-white transition-colors">
                  <span>Abrir</span>
                  <ArrowUpRight className="w-3 h-3 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                </span>
              </div>
            </motion.div>
          )
        })}
      </div>
    </section>
  )
}
