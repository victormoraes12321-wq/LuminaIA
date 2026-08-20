'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Pin, PinOff, Trash2, Maximize2, Sparkles, Table2, BarChart3 } from 'lucide-react'
import { DynamicRenderer } from '@/components/DynamicRenderer'
import { cn } from '@/lib/utils'
import type { ChartType } from '@/types/lumina'

export interface PinnedWidget {
  id: string
  title: string
  queryText: string
  chartType: ChartType
  chartData: any
  kpis?: Array<{ titulo: string; valor: string; variacao?: string }>
  summary?: string
  pinnedAt: string
}

export function PinnedWidgetsSection() {
  const [pinnedWidgets, setPinnedWidgets] = useState<PinnedWidget[]>([])

  const loadWidgets = () => {
    if (typeof window === 'undefined') return
    try {
      const stored = localStorage.getItem('lumina_pinned_dashboard_widgets')
      if (stored) {
        setPinnedWidgets(JSON.parse(stored))
      } else {
        setPinnedWidgets([])
      }
    } catch {
      setPinnedWidgets([])
    }
  }

  useEffect(() => {
    loadWidgets()
    const handleStorageChange = () => loadWidgets()
    window.addEventListener('lumina_pinned_widgets_changed', handleStorageChange)
    window.addEventListener('storage', handleStorageChange)
    return () => {
      window.removeEventListener('lumina_pinned_widgets_changed', handleStorageChange)
      window.removeEventListener('storage', handleStorageChange)
    }
  }, [])

  const handleUnpin = (id: string) => {
    try {
      const updated = pinnedWidgets.filter((w) => w.id !== id)
      localStorage.setItem('lumina_pinned_dashboard_widgets', JSON.stringify(updated))
      setPinnedWidgets(updated)
      window.dispatchEvent(new Event('lumina_pinned_widgets_changed'))
    } catch (err) {
      console.warn('[PinnedWidgets] Erro ao desafixar:', err)
    }
  }

  if (pinnedWidgets.length === 0) return null

  return (
    <div className="rounded-3xl border border-cyan-500/30 bg-zinc-950/70 p-5 space-y-4 shadow-xl backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 pb-3 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
            <Pin size={15} />
          </div>
          <div>
            <h3 className="text-xs font-black uppercase tracking-wider text-white">
              Painéis e Consultas Fixadas pelo Usuário
            </h3>
            <p className="text-[11px] text-zinc-400">
              Visualizações personalizadas fixadas a partir de perguntas na IA.
            </p>
          </div>
        </div>

        <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded-full font-bold">
          {pinnedWidgets.length} {pinnedWidgets.length === 1 ? 'Painel' : 'Painéis'}
        </span>
      </div>

      {/* Grid of Pinned Widgets */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {pinnedWidgets.map((widget) => (
          <div
            key={widget.id}
            className="rounded-2xl border border-zinc-800/80 bg-zinc-900/50 p-4 flex flex-col gap-3 shadow-md hover:border-zinc-700 transition-all"
          >
            <div className="flex items-center justify-between gap-2 border-b border-white/5 pb-2.5">
              <div>
                <h4 className="text-xs font-bold text-white">{widget.title}</h4>
                <p className="text-[10px] text-zinc-400 italic line-clamp-1">
                  &quot;{widget.queryText}&quot;
                </p>
              </div>

              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => handleUnpin(widget.id)}
                  className="p-1.5 rounded-lg text-zinc-400 hover:text-rose-400 hover:bg-zinc-800 transition-colors cursor-pointer"
                  title="Desafixar este painel"
                >
                  <PinOff size={13} />
                </button>
              </div>
            </div>

            {/* KPIs if present */}
            {widget.kpis && widget.kpis.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {widget.kpis.slice(0, 3).map((kpi, kIdx) => (
                  <div
                    key={kIdx}
                    className="bg-zinc-950/60 border border-white/5 rounded-xl p-2.5 flex flex-col"
                  >
                    <span className="text-[9px] uppercase tracking-wider text-zinc-400 line-clamp-1">
                      {kpi.titulo}
                    </span>
                    <span className="text-xs font-bold text-white truncate mt-1">
                      {kpi.valor}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Chart / Table View */}
            <div className="w-full min-h-[220px] max-h-[350px] overflow-hidden rounded-xl border border-white/5 bg-zinc-950/40 p-2">
              <DynamicRenderer
                chartType={widget.chartType}
                chartData={widget.chartData}
                title={widget.title}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
