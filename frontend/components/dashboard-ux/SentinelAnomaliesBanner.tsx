'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ShieldAlert,
  AlertTriangle,
  Flame,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  TrendingDown,
  PackageX,
  Sparkles,
  RefreshCw,
} from 'lucide-react'
import { cn, getApiBase } from '@/lib/utils'
import { useAuth } from '@/context/AuthContext'
import { SentinelInvestigationModal, AnomalyItem } from './SentinelInvestigationModal'

interface SentinelAnomaliesBannerProps {
  onInvestigate?: (query: string) => void
}

export function SentinelAnomaliesBanner({ onInvestigate }: SentinelAnomaliesBannerProps) {
  const { token } = useAuth()
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const [investigatingAnomaly, setInvestigatingAnomaly] = useState<AnomalyItem | null>(null)

  const fetchAnomalies = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${getApiBase()}/api/v1/sentinel/anomalies`, {
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
        },
      })
      const data = await res.json()
      if (data.success && Array.isArray(data.data)) {
        setAnomalies(data.data)
      }
    } catch (err) {
      console.warn('[SentinelBanner] Erro ao buscar anomalias:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnomalies()
  }, [token])

  if (dismissed || (!loading && anomalies.length === 0)) return null

  const criticalCount = anomalies.filter((a) => a.severidade === 'CRITICAL').length
  const topAnomalies = expanded ? anomalies : anomalies.slice(0, 3)

  return (
    <div className="rounded-2xl border border-rose-500/30 bg-gradient-to-r from-rose-950/40 via-zinc-950/80 to-zinc-950/90 p-4 shadow-xl backdrop-blur-xl transition-all duration-300">
      {/* Top Banner Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-rose-500/20">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-300 shadow-sm animate-pulse">
            <ShieldAlert size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-black uppercase tracking-wider text-rose-300">
                Sentinela LuminaAI • Monitor Autônomo de Riscos
              </span>
              {criticalCount > 0 && (
                <span className="px-2 py-0.2 rounded-full bg-rose-500/30 text-rose-200 border border-rose-500/50 text-[10px] font-black">
                  {criticalCount} Críticos
                </span>
              )}
            </div>
            <p className="text-[11px] text-zinc-400">
              Análise em tempo real de retenção de clientes VIP, risco de ruptura e desvios de filiais.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchAnomalies}
            className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
            title="Recalcular Anomalias"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          </button>

          {anomalies.length > 3 && (
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs font-semibold text-rose-300 hover:text-rose-200 bg-rose-500/10 hover:bg-rose-500/20 px-2.5 py-1 rounded-lg border border-rose-500/30 transition-all cursor-pointer"
            >
              <span>{expanded ? 'Recolher' : `Ver todas (${anomalies.length})`}</span>
              {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}

          <button
            type="button"
            onClick={() => setDismissed(true)}
            className="text-[10px] text-zinc-500 hover:text-zinc-300 px-2 py-1 transition-colors cursor-pointer"
          >
            Ocultar
          </button>
        </div>
      </div>

      {/* Anomalies List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-3">
        {topAnomalies.map((item) => {
          const isCritical = item.severidade === 'CRITICAL'
          const isOpportunity = item.severidade === 'OPPORTUNITY'
          return (
            <div
              key={item.id}
              className={cn(
                'rounded-xl p-3 flex flex-col justify-between gap-2 border transition-all duration-200 shadow-sm',
                isCritical
                  ? 'bg-rose-950/20 border-rose-500/30 hover:border-rose-500/60'
                  : isOpportunity
                  ? 'bg-emerald-950/20 border-emerald-500/30 hover:border-emerald-500/60'
                  : 'bg-amber-950/20 border-amber-500/30 hover:border-amber-500/60'
              )}
            >
              <div className="space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={cn(
                      'text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded',
                      isCritical
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                        : isOpportunity
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    )}
                  >
                    {item.categoria.replace(/_/g, ' ')}
                  </span>
                  {item.impacto_formatted && (
                    <span className="text-[10px] font-mono font-bold text-zinc-300">
                      Impacto: {item.impacto_formatted}
                    </span>
                  )}
                </div>

                <h4 className="text-xs font-bold text-white line-clamp-1">{item.titulo}</h4>
                <p className="text-[11px] text-zinc-300 line-clamp-2 leading-relaxed">
                  {item.descricao}
                </p>
              </div>

              <div className="flex items-center justify-between gap-2 pt-1 border-t border-white/5">
                <span className="text-[10px] text-zinc-400 italic line-clamp-1">
                  {item.sugestao_acao}
                </span>

                <button
                  type="button"
                  onClick={() => setInvestigatingAnomaly(item)}
                  className="shrink-0 flex items-center gap-1 text-[10px] font-bold text-cyan-300 hover:text-cyan-200 bg-cyan-500/10 hover:bg-cyan-500/20 px-2.5 py-1 rounded-lg border border-cyan-500/30 transition-all cursor-pointer shadow-sm"
                >
                  <Sparkles size={11} />
                  <span>Investigar Dossiê</span>
                  <ArrowRight size={10} />
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Deep-Dive Investigation Modal */}
      <SentinelInvestigationModal
        anomaly={investigatingAnomaly}
        isOpen={!!investigatingAnomaly}
        onClose={() => setInvestigatingAnomaly(null)}
      />
    </div>
  )
}
