'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  ShieldAlert,
  RefreshCw,
  MapPin,
  FileBarChart2,
  ArrowRightLeft,
  CheckCircle2,
  Percent,
} from 'lucide-react'
import { cn, getApiBase } from '@/lib/utils'
import { useAuth } from '@/context/AuthContext'
import { Sidebar } from '@/components/Sidebar'
import { SentinelAnomaliesBanner } from '@/components/dashboard-ux/SentinelAnomaliesBanner'

// ─────────────────────────────────────────────────────────────
// Types matching backend models
// ─────────────────────────────────────────────────────────────
interface RebalancingItem {
  codigo_produto: string
  descricao: string
  filial_origem: string
  filial_destino: string
  qtde_sugerida_transferencia: number
  demanda_destino_90d?: number
  demanda_origem_90d?: number
  estoque_geral?: number
  impacto_estimado_brl?: number
  motivo?: string
  prioridade?: 'ALTA' | 'MEDIA' | 'BAIXA' | string
}

interface MunicipioItem {
  cidade: string
  uf: string
  praca?: string
  total_notas: number
  clientes_distintos: number
  unidades_vendidas: number
  faturamento_total: number
  faturamento_formatted: string
}

interface HeatmapResponse {
  resumo?: {
    total_municipios?: number
    faturamento_global?: number
    faturamento_global_formatted?: string
  }
  ranking_municipios?: MunicipioItem[]
}

interface CfopItem {
  cfop: string
  total_notas: number
  qtde_total: number
  faturamento_total: number
  faturamento_formatted: string
  natureza: string
}

interface CfopResponse {
  total_faturamento_vendas_reais?: number
  total_faturamento_outros_movimentos?: number
  percentual_vendas_reais?: number
  vendas_comerciais?: CfopItem[]
  outras_movimentacoes?: CfopItem[]
}

// ─────────────────────────────────────────────────────────────
// Main Page Component
// ─────────────────────────────────────────────────────────────
export default function OperacoesPage() {
  const { token, loading: authLoading } = useAuth()
  const [rebalancing, setRebalancing] = useState<RebalancingItem[]>([])
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null)
  const [cfop, setCfop] = useState<CfopResponse | null>(null)
  const [loadingReb, setLoadingReb] = useState(true)
  const [loadingHeat, setLoadingHeat] = useState(true)
  const [loadingCfop, setLoadingCfop] = useState(true)

  const authHeaders = useCallback((): Record<string, string> => {
    const t =
      token && token !== '__lumina_cookie_session__'
        ? token
        : typeof window !== 'undefined'
          ? localStorage.getItem('lumina_jwt_token')
          : null
    if (t && t !== '__lumina_cookie_session__') return { Authorization: `Bearer ${t}` }
    return {}
  }, [token])

  const fetchRebalancing = useCallback(async () => {
    setLoadingReb(true)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/logistics/rebalancing?limit=30`, {
        headers: authHeaders(),
        credentials: 'include',
      })
      const json = await res.json()
      if (json.success && Array.isArray(json.data)) {
        setRebalancing(json.data)
      } else {
        setRebalancing([])
      }
    } catch (e) {
      console.warn('[Operacoes] Erro ao buscar rebalanceamento:', e)
      setRebalancing([])
    } finally {
      setLoadingReb(false)
    }
  }, [authHeaders])

  const fetchHeatmap = useCallback(async () => {
    setLoadingHeat(true)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/logistics/regional-heatmap?limit=50`, {
        headers: authHeaders(),
        credentials: 'include',
      })
      const json = await res.json()
      if (json.success && json.data) {
        setHeatmap(json.data)
      } else {
        setHeatmap(null)
      }
    } catch (e) {
      console.warn('[Operacoes] Erro ao buscar heatmap regional:', e)
      setHeatmap(null)
    } finally {
      setLoadingHeat(false)
    }
  }, [authHeaders])

  const fetchCfop = useCallback(async () => {
    setLoadingCfop(true)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/logistics/cfop-distribution`, {
        headers: authHeaders(),
        credentials: 'include',
      })
      const json = await res.json()
      if (json.success && json.data) {
        setCfop(json.data)
      } else {
        setCfop(null)
      }
    } catch (e) {
      console.warn('[Operacoes] Erro ao buscar distribuicao CFOP:', e)
      setCfop(null)
    } finally {
      setLoadingCfop(false)
    }
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

  if (authLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-zinc-950">
        <div className="flex flex-col items-center gap-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-8 h-8 rounded-full border-2 border-t-transparent border-rose-400"
          />
          <span className="text-sm font-medium text-zinc-400">
            Carregando Central de Operações...
          </span>
        </div>
      </div>
    )
  }

  const rankingMunicipios = heatmap?.ranking_municipios || []
  const totalFaturamentoGlobal = rankingMunicipios.reduce((s, m) => s + (m.faturamento_total || 0), 0)
  const vendasComerciais = cfop?.vendas_comerciais || []
  const outrasMovimentacoes = cfop?.outras_movimentacoes || []
  const totalReceitaRebalanceamento = rebalancing.reduce(
    (s, r) => s + (r.impacto_estimado_brl || 0),
    0
  )

  return (
    <div className="flex h-dvh overflow-hidden bg-zinc-950 text-white">
      {/* ── Global Sidebar ── */}
      <Sidebar />

      {/* ── Main Scrollable Content ── */}
      <main className="flex-1 min-w-0 overflow-y-auto p-4 md:p-6 lg:p-8 space-y-6">
        {/* ── Page Header ── */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-rose-500/20 to-amber-500/10 border border-rose-500/30 text-rose-300 shadow-lg shadow-rose-950/40">
              <ShieldAlert size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-black text-white tracking-tight">
                  Operações, Logística & Sentinela
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-500/30">
                  LuminaAI Live
                </span>
              </div>
              <p className="text-xs text-zinc-400">
                Detecção autônoma de anomalias, balanceamento entre filiais, geografia comercial e segregação fiscal.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={refreshAll}
              disabled={isLoading}
              className="flex items-center gap-2 text-xs font-bold text-zinc-200 hover:text-white bg-zinc-900 hover:bg-zinc-800 px-3.5 py-2 rounded-xl border border-zinc-800 hover:border-zinc-700 transition-all cursor-pointer disabled:opacity-50 shadow-sm"
            >
              <RefreshCw size={14} className={isLoading ? 'animate-spin text-rose-400' : ''} />
              <span>{isLoading ? 'Atualizando...' : 'Recalcular Métricas'}</span>
            </button>
          </div>
        </div>

        {/* ── Executive Operations KPI Cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {/* Card 1: Rebalanceamento */}
          <div className="rounded-2xl border border-amber-500/20 bg-zinc-900/60 p-4 backdrop-blur shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Transferências Sugeridas
              </span>
              <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <ArrowRightLeft size={16} />
              </div>
            </div>
            <div className="pt-2">
              <div className="text-2xl font-black text-white font-mono">
                {rebalancing.length}
              </div>
              <p className="text-[11px] text-amber-300/90 font-medium pt-0.5">
                R$ {totalReceitaRebalanceamento.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} em risco protegido
              </p>
            </div>
          </div>

          {/* Card 2: Cobertura Geográfica */}
          <div className="rounded-2xl border border-cyan-500/20 bg-zinc-900/60 p-4 backdrop-blur shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Municípios Atendidos
              </span>
              <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <MapPin size={16} />
              </div>
            </div>
            <div className="pt-2">
              <div className="text-2xl font-black text-white font-mono">
                {rankingMunicipios.length}
              </div>
              <p className="text-[11px] text-cyan-300/90 font-medium pt-0.5">
                Líder: {rankingMunicipios[0]?.cidade || 'N/D'} ({rankingMunicipios[0]?.faturamento_formatted || 'R$ 0'})
              </p>
            </div>
          </div>

          {/* Card 3: % Vendas Reais */}
          <div className="rounded-2xl border border-emerald-500/20 bg-zinc-900/60 p-4 backdrop-blur shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Vendas Comerciais Reais
              </span>
              <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Percent size={16} />
              </div>
            </div>
            <div className="pt-2">
              <div className="text-2xl font-black text-white font-mono">
                {(cfop?.percentual_vendas_reais || 0).toFixed(1)}%
              </div>
              <p className="text-[11px] text-emerald-300/90 font-medium pt-0.5">
                R$ {(cfop?.total_faturamento_vendas_reais || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} faturados
              </p>
            </div>
          </div>

          {/* Card 4: Remessas & Transferências */}
          <div className="rounded-2xl border border-violet-500/20 bg-zinc-900/60 p-4 backdrop-blur shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Outras Movimentações (CFOP)
              </span>
              <div className="p-2 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20">
                <FileBarChart2 size={16} />
              </div>
            </div>
            <div className="pt-2">
              <div className="text-2xl font-black text-white font-mono">
                R$ {(cfop?.total_faturamento_outros_movimentos || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <p className="text-[11px] text-violet-300/90 font-medium pt-0.5">
                Transferências, remessas e bonificações
              </p>
            </div>
          </div>
        </div>

        {/* ── Section 1: Sentinel Autonomous Anomalies ── */}
        <section className="space-y-3">
          <SectionBadge icon={<ShieldAlert size={15} />} title="Sentinela Proativo de Anomalias" color="rose" />
          <SentinelAnomaliesBanner />
        </section>

        {/* ── Section 2: Branch Inventory Rebalancing ── */}
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SectionBadge icon={<ArrowRightLeft size={15} />} title="Rebalanceamento de Estoque entre Filiais" color="amber" />
            <span className="text-xs text-zinc-400">
              Oportunidades de transferência para evitar ruptura sem nova compra
            </span>
          </div>

          <div className="rounded-2xl border border-amber-500/20 bg-zinc-900/50 backdrop-blur overflow-hidden shadow-lg">
            {loadingReb ? (
              <LoadingState />
            ) : rebalancing.length === 0 ? (
              <EmptyState message="Nenhuma oportunidade de rebalanceamento detectada — estoque equilibrado entre as filiais." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-zinc-800 bg-zinc-800/40 text-zinc-400 font-bold uppercase tracking-wider text-[10px]">
                      <th className="px-4 py-3">Produto</th>
                      <th className="px-4 py-3 text-center">Origem (Excesso)</th>
                      <th className="px-4 py-3 text-center">Destino (Ruptura)</th>
                      <th className="px-4 py-3 text-right">Qtde Sugerida</th>
                      <th className="px-4 py-3 text-right">Demanda 90d Destino</th>
                      <th className="px-4 py-3 text-right text-amber-400">Impacto / Receita</th>
                      <th className="px-4 py-3 text-center">Prioridade</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/50">
                    {rebalancing.map((r, i) => {
                      const isHigh = r.prioridade === 'ALTA'
                      return (
                        <tr key={`${r.codigo_produto}-${i}`} className="hover:bg-zinc-800/40 transition-colors">
                          <td className="px-4 py-3">
                            <div className="font-bold text-white line-clamp-1">{r.descricao}</div>
                            <div className="text-[10px] font-mono text-zinc-500">Cód: #{r.codigo_produto}</div>
                            {r.motivo && (
                              <div className="text-[10px] text-zinc-400 italic pt-0.5 line-clamp-1">{r.motivo}</div>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-black text-[11px]">
                              Filial {r.filial_origem}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="px-2.5 py-1 rounded-lg bg-rose-500/10 text-rose-300 border border-rose-500/20 font-black text-[11px]">
                              Filial {r.filial_destino}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right font-mono font-black text-amber-300 text-sm">
                            {r.qtde_sugerida_transferencia?.toLocaleString('pt-BR') || 0} un
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-zinc-400">
                            {r.demanda_destino_90d?.toLocaleString('pt-BR') || 0} un
                          </td>
                          <td className="px-4 py-3 text-right font-mono font-bold text-white">
                            R$ {(r.impacto_estimado_brl || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={cn(
                              'px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border',
                              isHigh
                                ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                                : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                            )}>
                              {r.prioridade || 'MÉDIA'}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
                <div className="px-4 py-2.5 border-t border-zinc-800 bg-zinc-950/40 text-[11px] text-zinc-400 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2 size={13} className="text-emerald-400" />
                    <span>Total de <strong>{rebalancing.length}</strong> oportunidades detectadas.</span>
                  </div>
                  <div className="text-zinc-300">
                    Potencial de receita preservada:{' '}
                    <strong className="text-amber-300 font-mono">
                      R$ {totalReceitaRebalanceamento.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ── Section 3: Regional Sales Heatmap ── */}
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SectionBadge icon={<MapPin size={15} />} title="Análise Geográfica de Vendas (Ranking por Município)" color="cyan" />
            <span className="text-xs text-zinc-400">
              Concentração comercial mapeada por Município, UF e Praça
            </span>
          </div>

          <div className="rounded-2xl border border-cyan-500/20 bg-zinc-900/50 backdrop-blur overflow-hidden shadow-lg">
            {loadingHeat ? (
              <LoadingState />
            ) : rankingMunicipios.length === 0 ? (
              <EmptyState message="Nenhum dado geográfico disponível na base analítica." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-zinc-800 bg-zinc-800/40 text-zinc-400 font-bold uppercase tracking-wider text-[10px]">
                      <th className="px-4 py-3 text-center w-12">#</th>
                      <th className="px-4 py-3">Município / UF</th>
                      <th className="px-4 py-3">Praça</th>
                      <th className="px-4 py-3 text-right">Faturamento</th>
                      <th className="px-4 py-3 text-right">Notas Emitidas</th>
                      <th className="px-4 py-3 text-right">Clientes Únicos</th>
                      <th className="px-4 py-3 text-right text-cyan-400">Participação %</th>
                      <th className="px-4 py-3 w-32">Distribuição</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/50">
                    {rankingMunicipios.map((m, i) => {
                      const partPct = totalFaturamentoGlobal > 0
                        ? ((m.faturamento_total || 0) / totalFaturamentoGlobal) * 100
                        : 0
                      return (
                        <tr key={`${m.cidade}-${m.uf}-${i}`} className="hover:bg-zinc-800/40 transition-colors">
                          <td className="px-4 py-3 text-center text-zinc-500 font-mono font-bold">
                            {i + 1}
                          </td>
                          <td className="px-4 py-3">
                            <span className="font-bold text-white">{m.cidade}</span>
                            <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-zinc-800 text-zinc-300">
                              {m.uf}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-zinc-400 text-[11px]">
                            {m.praca || 'Padrão'}
                          </td>
                          <td className="px-4 py-3 text-right font-mono font-bold text-white">
                            {m.faturamento_formatted || `R$ ${(m.faturamento_total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-zinc-300">
                            {(m.total_notas || 0).toLocaleString('pt-BR')}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-zinc-300">
                            {(m.clientes_distintos || 0).toLocaleString('pt-BR')}
                          </td>
                          <td className="px-4 py-3 text-right font-mono font-bold text-cyan-300">
                            {partPct.toFixed(1)}%
                          </td>
                          <td className="px-4 py-3">
                            <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                              <div
                                className="h-1.5 rounded-full bg-gradient-to-r from-cyan-500 to-blue-500"
                                style={{ width: `${Math.min(100, Math.max(3, partPct * 2.5))}%` }}
                              />
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        {/* ── Section 4: CFOP Movement Segregation ── */}
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SectionBadge icon={<FileBarChart2 size={15} />} title="Segregação Analítica de Movimentos (CFOP)" color="violet" />
            <span className="text-xs text-zinc-400">
              Separação rigorosa de vendas comerciais reais vs. simples remessas e transferências
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Tabela 1: Vendas Comerciais */}
            <div className="rounded-2xl border border-emerald-500/20 bg-zinc-900/50 backdrop-blur p-4 space-y-3 shadow-lg">
              <div className="flex items-center justify-between pb-2 border-b border-emerald-500/20">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <h3 className="text-xs font-black uppercase tracking-wider text-emerald-300">
                    Vendas Comerciais (Faturamento Efetivo)
                  </h3>
                </div>
                <span className="text-xs font-mono font-bold text-white">
                  R$ {(cfop?.total_faturamento_vendas_reais || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>

              {loadingCfop ? (
                <LoadingState />
              ) : vendasComerciais.length === 0 ? (
                <EmptyState message="Nenhuma venda comercial registrada." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-zinc-800 text-zinc-400 font-bold uppercase tracking-wider text-[10px]">
                        <th className="py-2 px-2">CFOP</th>
                        <th className="py-2 px-2">Natureza</th>
                        <th className="py-2 px-2 text-right">Notas</th>
                        <th className="py-2 px-2 text-right text-emerald-400">Faturamento</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/40">
                      {vendasComerciais.map((c, i) => (
                        <tr key={`${c.cfop}-${i}`} className="hover:bg-zinc-800/30 transition-colors">
                          <td className="py-2 px-2 font-mono font-bold text-emerald-300">{c.cfop}</td>
                          <td className="py-2 px-2 text-zinc-300 text-[11px] line-clamp-1">{c.natureza}</td>
                          <td className="py-2 px-2 text-right font-mono text-zinc-400">
                            {(c.total_notas || 0).toLocaleString('pt-BR')}
                          </td>
                          <td className="py-2 px-2 text-right font-mono font-bold text-white">
                            {c.faturamento_formatted || `R$ ${(c.faturamento_total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Tabela 2: Outras Movimentações */}
            <div className="rounded-2xl border border-violet-500/20 bg-zinc-900/50 backdrop-blur p-4 space-y-3 shadow-lg">
              <div className="flex items-center justify-between pb-2 border-b border-violet-500/20">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-violet-400" />
                  <h3 className="text-xs font-black uppercase tracking-wider text-violet-300">
                    Outras Saídas (Transferências / Remessas)
                  </h3>
                </div>
                <span className="text-xs font-mono font-bold text-white">
                  R$ {(cfop?.total_faturamento_outros_movimentos || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>

              {loadingCfop ? (
                <LoadingState />
              ) : outrasMovimentacoes.length === 0 ? (
                <EmptyState message="Nenhuma movimentação de remessa registrada." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-zinc-800 text-zinc-400 font-bold uppercase tracking-wider text-[10px]">
                        <th className="py-2 px-2">CFOP</th>
                        <th className="py-2 px-2">Natureza</th>
                        <th className="py-2 px-2 text-right">Notas</th>
                        <th className="py-2 px-2 text-right text-violet-400">Faturamento</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/40">
                      {outrasMovimentacoes.map((c, i) => (
                        <tr key={`${c.cfop}-${i}`} className="hover:bg-zinc-800/30 transition-colors">
                          <td className="py-2 px-2 font-mono font-bold text-violet-300">{c.cfop}</td>
                          <td className="py-2 px-2 text-zinc-300 text-[11px] line-clamp-1">{c.natureza}</td>
                          <td className="py-2 px-2 text-right font-mono text-zinc-400">
                            {(c.total_notas || 0).toLocaleString('pt-BR')}
                          </td>
                          <td className="py-2 px-2 text-right font-mono font-bold text-white">
                            {c.faturamento_formatted || `R$ ${(c.faturamento_total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────
function SectionBadge({
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
    <div className={cn('inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-black uppercase tracking-wider', colors[color])}>
      {icon}
      <span>{title}</span>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-zinc-500 text-xs">
      <RefreshCw size={15} className="animate-spin text-rose-400" />
      <span>Carregando dados da réplica analítica...</span>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-zinc-500 text-xs">
      <CheckCircle2 size={15} className="text-emerald-400" />
      <span>{message}</span>
    </div>
  )
}

