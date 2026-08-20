'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  ShieldAlert,
  RefreshCw,
  PackageSearch,
  MapPin,
  FileBarChart2,
  ArrowRightLeft,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Flame,
  Sparkles,
  CheckCircle2,
} from 'lucide-react'
import { cn, getApiBase } from '@/lib/utils'
import { useAuth } from '@/context/AuthContext'
import { SentinelAnomaliesBanner } from '@/components/dashboard-ux/SentinelAnomaliesBanner'

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────
interface RebalancingItem {
  codprod: string
  descricao: string
  filial_excesso: string
  estoque_excesso: number
  filial_ruptura: string
  estoque_ruptura: number
  qtde_sugerida_transferencia: number
  receita_estimada_salva: number
  receita_formatted: string
}

interface HeatmapItem {
  municipio: string
  uf: string
  fat_total: number
  fat_formatted: string
  num_pedidos: number
  participacao_pct: number
}

interface CfopItem {
  cfop: string
  descricao_cfop: string
  fat_total: number
  fat_formatted: string
  num_notas: number
  participacao_pct: number
  tipo: string
}

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────
export default function OperacoesPage() {
  const { token } = useAuth()
  const [rebalancing, setRebalancing] = useState<RebalancingItem[]>([])
  const [heatmap, setHeatmap] = useState<HeatmapItem[]>([])
  const [cfop, setCfop] = useState<CfopItem[]>([])
  const [loadingReb, setLoadingReb] = useState(true)
  const [loadingHeat, setLoadingHeat] = useState(true)
  const [loadingCfop, setLoadingCfop] = useState(true)

  const authHeaders = useCallback((): Record<string, string> => {
    const t = token && token !== '__lumina_cookie_session__'
      ? token
      : typeof window !== 'undefined' ? localStorage.getItem('lumina_jwt_token') : null
    if (t) return { Authorization: `Bearer ${t}` }
    return {}
  }, [token])

  const fetchRebalancing = useCallback(async () => {
    setLoadingReb(true)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/logistics/rebalancing?limit=20`, {
        headers: authHeaders(),
        credentials: 'include',
      })
      const data = await res.json()
      if (data.success) setRebalancing(data.data || [])
    } catch (e) { console.warn('[Operacoes] rebalancing error', e) }
    finally { setLoadingReb(false) }
  }, [authHeaders])

  const fetchHeatmap = useCallback(async () => {
    setLoadingHeat(true)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/logistics/regional-heatmap?limit=30`, {
        headers: authHeaders(),
        credentials: 'include',
      })
      const data = await res.json()
      if (data.success) setHeatmap(data.data || [])
    } catch (e) { console.warn('[Operacoes] heatmap error', e) }
    finally { setLoadingHeat(false) }
  }, [authHeaders])

  const fetchCfop = useCallback(async () => {
    setLoadingCfop(true)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/logistics/cfop-distribution`, {
        headers: authHeaders(),
        credentials: 'include',
      })
      const data = await res.json()
      if (data.success) setCfop(data.data || [])
    } catch (e) { console.warn('[Operacoes] cfop error', e) }
    finally { setLoadingCfop(false) }
  }, [authHeaders])

  useEffect(() => {
    fetchRebalancing()
    fetchHeatmap()
    fetchCfop()
  }, [fetchRebalancing, fetchHeatmap, fetchCfop])

  const refreshAll = () => {
    fetchRebalancing()
    fetchHeatmap()
    fetchCfop()
  }

  const isLoading = loadingReb || loadingHeat || loadingCfop

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-4 md:p-6 space-y-6">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-500/20 border border-rose-500/30">
            <ShieldAlert className="text-rose-400" size={20} />
          </div>
          <div>
            <h1 className="text-lg font-black text-white tracking-tight">
              Operações & Sentinela LuminaAI
            </h1>
            <p className="text-xs text-zinc-400">
              Monitor autônomo de riscos, logística, heatmap regional e análise de CFOP
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={refreshAll}
          disabled={isLoading}
          className="flex items-center gap-2 text-xs font-semibold text-zinc-300 hover:text-white bg-zinc-800 hover:bg-zinc-700 px-3 py-2 rounded-lg border border-zinc-700 transition-all cursor-pointer disabled:opacity-50"
        >
          <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          <span>Atualizar Tudo</span>
        </button>
      </div>

      {/* ── Section 1: Sentinel Anomalies (full view) ── */}
      <section className="space-y-2">
        <SectionTitle icon={<ShieldAlert size={15} />} title="Alertas Sentinela Autônomo" color="rose" />
        <SentinelAnomaliesBanner />
      </section>

      {/* ── Section 2: Branch Rebalancing ── */}
      <section className="space-y-3">
        <SectionTitle icon={<ArrowRightLeft size={15} />} title="Rebalanceamento de Estoque entre Filiais" color="amber" />
        <div className="rounded-xl border border-amber-500/20 bg-zinc-900/60 backdrop-blur overflow-hidden">
          {loadingReb ? (
            <LoadingState />
          ) : rebalancing.length === 0 ? (
            <EmptyState message="Nenhuma oportunidade de rebalanceamento detectada no momento." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-zinc-800 bg-zinc-800/40">
                    <th className="text-left px-4 py-3 text-zinc-400 font-semibold">Produto</th>
                    <th className="text-center px-4 py-3 text-zinc-400 font-semibold">Filial Excesso</th>
                    <th className="text-right px-4 py-3 text-zinc-400 font-semibold">Estoque</th>
                    <th className="text-center px-4 py-3 text-zinc-400 font-semibold">Filial Ruptura</th>
                    <th className="text-right px-4 py-3 text-zinc-400 font-semibold">Qtde Sugerida</th>
                    <th className="text-right px-4 py-3 text-amber-400 font-semibold">Receita Salva</th>
                  </tr>
                </thead>
                <tbody>
                  {rebalancing.map((r, i) => (
                    <tr key={`${r.codprod}-${i}`} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                      <td className="px-4 py-2.5">
                        <div className="font-medium text-white line-clamp-1">{r.descricao}</div>
                        <div className="text-zinc-500 text-[10px]">#{r.codprod}</div>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[10px] font-bold">
                          Filial {r.filial_excesso}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right text-emerald-300 font-mono">{r.estoque_excesso} un</td>
                      <td className="px-4 py-2.5 text-center">
                        <span className="px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-300 border border-rose-500/20 text-[10px] font-bold">
                          Filial {r.filial_ruptura}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-bold text-amber-300">{r.qtde_sugerida_transferencia} un</td>
                      <td className="px-4 py-2.5 text-right font-bold text-white">{r.receita_formatted}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="px-4 py-2 border-t border-zinc-800 text-[10px] text-zinc-500 flex items-center gap-1">
                <CheckCircle2 size={11} className="text-emerald-400" />
                <span>
                  {rebalancing.length} oportunidades de transferência detectadas —
                  total potencial de receita protegida:{' '}
                  <span className="font-bold text-amber-300">
                    {rebalancing.reduce((s, r) => s + r.receita_estimada_salva, 0)
                      .toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </span>
                </span>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ── Section 3: Regional Heatmap ── */}
      <section className="space-y-3">
        <SectionTitle icon={<MapPin size={15} />} title="Análise Geográfica de Vendas (Top Municípios)" color="cyan" />
        <div className="rounded-xl border border-cyan-500/20 bg-zinc-900/60 backdrop-blur overflow-hidden">
          {loadingHeat ? (
            <LoadingState />
          ) : heatmap.length === 0 ? (
            <EmptyState message="Nenhum dado geográfico disponível." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-zinc-800 bg-zinc-800/40">
                    <th className="text-left px-4 py-3 text-zinc-400 font-semibold">#</th>
                    <th className="text-left px-4 py-3 text-zinc-400 font-semibold">Município / UF</th>
                    <th className="text-right px-4 py-3 text-zinc-400 font-semibold">Faturamento</th>
                    <th className="text-right px-4 py-3 text-zinc-400 font-semibold">Pedidos</th>
                    <th className="text-right px-4 py-3 text-cyan-400 font-semibold">Part. %</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {heatmap.map((h, i) => (
                    <tr key={`${h.municipio}-${h.uf}`} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                      <td className="px-4 py-2.5 text-zinc-500 font-mono">{i + 1}</td>
                      <td className="px-4 py-2.5">
                        <span className="font-medium text-white">{h.municipio}</span>
                        <span className="ml-1.5 text-zinc-500 text-[10px]">/ {h.uf}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-bold text-white">{h.fat_formatted}</td>
                      <td className="px-4 py-2.5 text-right text-zinc-300">{h.num_pedidos.toLocaleString('pt-BR')}</td>
                      <td className="px-4 py-2.5 text-right font-bold text-cyan-300">{h.participacao_pct?.toFixed(1)}%</td>
                      <td className="px-4 py-2.5 w-28">
                        <div className="w-full bg-zinc-800 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full bg-gradient-to-r from-cyan-500 to-blue-500"
                            style={{ width: `${Math.min(100, h.participacao_pct * 5)}%` }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* ── Section 4: CFOP Distribution ── */}
      <section className="space-y-3">
        <SectionTitle icon={<FileBarChart2 size={15} />} title="Segregação Analítica de Movimentos (CFOP)" color="violet" />
        <div className="rounded-xl border border-violet-500/20 bg-zinc-900/60 backdrop-blur overflow-hidden">
          {loadingCfop ? (
            <LoadingState />
          ) : cfop.length === 0 ? (
            <EmptyState message="Nenhum dado de CFOP disponível." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-zinc-800 bg-zinc-800/40">
                    <th className="text-left px-4 py-3 text-zinc-400 font-semibold">CFOP</th>
                    <th className="text-left px-4 py-3 text-zinc-400 font-semibold">Descrição</th>
                    <th className="text-center px-4 py-3 text-zinc-400 font-semibold">Tipo</th>
                    <th className="text-right px-4 py-3 text-zinc-400 font-semibold">Faturamento</th>
                    <th className="text-right px-4 py-3 text-zinc-400 font-semibold">Notas</th>
                    <th className="text-right px-4 py-3 text-violet-400 font-semibold">Part. %</th>
                  </tr>
                </thead>
                <tbody>
                  {cfop.map((c, i) => {
                    const isVenda = c.tipo === 'VENDA_REAL'
                    return (
                      <tr key={`${c.cfop}-${i}`} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                        <td className="px-4 py-2.5 font-mono font-bold text-white">{c.cfop}</td>
                        <td className="px-4 py-2.5 text-zinc-300 line-clamp-1">{c.descricao_cfop}</td>
                        <td className="px-4 py-2.5 text-center">
                          <span className={cn(
                            'px-2 py-0.5 rounded-full text-[10px] font-bold border',
                            isVenda
                              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                              : 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20'
                          )}>
                            {isVenda ? 'Venda Real' : c.tipo.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-right font-bold text-white">{c.fat_formatted}</td>
                        <td className="px-4 py-2.5 text-right text-zinc-300">{c.num_notas.toLocaleString('pt-BR')}</td>
                        <td className="px-4 py-2.5 text-right font-bold text-violet-300">{c.participacao_pct?.toFixed(1)}%</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <div className="px-4 py-2 border-t border-zinc-800 text-[10px] text-zinc-500 flex flex-wrap gap-4">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                  Vendas Reais:{' '}
                  <span className="font-bold text-emerald-300 ml-1">
                    {cfop.filter(c => c.tipo === 'VENDA_REAL').reduce((s, c) => s + c.fat_total, 0)
                      .toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-zinc-400 inline-block" />
                  Remessas/Transferências:{' '}
                  <span className="font-bold text-zinc-300 ml-1">
                    {cfop.filter(c => c.tipo !== 'VENDA_REAL').reduce((s, c) => s + c.fat_total, 0)
                      .toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </span>
                </span>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────
function SectionTitle({
  icon,
  title,
  color,
}: {
  icon: React.ReactNode
  title: string
  color: 'rose' | 'amber' | 'cyan' | 'violet'
}) {
  const colors = {
    rose: 'text-rose-300 border-rose-500/30 bg-rose-500/10',
    amber: 'text-amber-300 border-amber-500/30 bg-amber-500/10',
    cyan: 'text-cyan-300 border-cyan-500/30 bg-cyan-500/10',
    violet: 'text-violet-300 border-violet-500/30 bg-violet-500/10',
  }
  return (
    <div className={cn('flex items-center gap-2 px-3 py-1.5 rounded-lg border w-fit', colors[color])}>
      {icon}
      <span className="text-xs font-black uppercase tracking-wider">{title}</span>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-zinc-500 text-sm">
      <RefreshCw size={14} className="animate-spin" />
      <span>Carregando dados...</span>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-zinc-500 text-sm">
      <CheckCircle2 size={14} className="text-emerald-400" />
      <span>{message}</span>
    </div>
  )
}
