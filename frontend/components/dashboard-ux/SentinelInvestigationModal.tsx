'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  ShieldAlert,
  AlertTriangle,
  Flame,
  TrendingDown,
  TrendingUp,
  PackageX,
  FileText,
  UserCheck,
  Calendar,
  Building2,
  PhoneCall,
  CheckCircle2,
  RefreshCw,
  Clock,
  Sparkles,
  ArrowDownRight,
  Receipt,
  Layers,
} from 'lucide-react'
import { cn, getApiBase } from '@/lib/utils'
import { useAuth } from '@/context/AuthContext'

export interface AnomalyItem {
  id: string
  categoria: 'CLIENTE_VIP_CHURN' | 'ESTOQUE_RUPTURA' | 'FILIAL_DESEMPENHO' | 'OPORTUNIDADE_COMERCIAL' | string
  tipo: string
  severidade: 'CRITICAL' | 'WARNING' | 'OPPORTUNITY' | string
  titulo: string
  entidade: string
  codigo: string
  descricao: string
  impacto_financeiro: number
  impacto_formatted: string
  sugestao_acao: string
  data_deteccao: string
  periodo_atual?: string
  periodo_anterior?: string
  data_ultima_compra?: string
  notas_atuais?: number
  notas_anteriores?: number
}

interface SentinelInvestigationModalProps {
  anomaly: AnomalyItem | null
  isOpen: boolean
  onClose: () => void
}

interface InvestigationData {
  tipo_investigacao: string
  cliente?: {
    codigo: string
    razao: string
    rca: string | number
    principal_filial: string
    total_historico_notas: number
    faturamento_vitalicio: number
    faturamento_vitalicio_formatted: string
    ultima_compra_data: string
  }
  comparativo_sazonal?: {
    periodo_atual: string
    periodo_anterior: string
    fat_recente: number
    fat_recente_formatted: string
    fat_anterior: number
    fat_anterior_formatted: string
    variacao_pct: number
    perda_financeira: number
    perda_formatted: string
    notas_recentes: number
    notas_anteriores: number
  }
  produtos_perdidos?: Array<{
    codprod: string
    descricao: string
    fat_ano_passado: number
    fat_recente: number
    fat_ano_passado_formatted: string
    fat_recente_formatted: string
    qtde_ano_passado: number
    qtde_recente: number
    status: string
  }>
  ultimas_notas?: Array<{
    nota: string
    filial: string | number
    data_emissao: string
    valor_total: number
    valor_formatted: string
    total_itens: number
  }>
  produto?: {
    codigo: string
    descricao: string
    estoque_atual: number
    fornecedor: string
  }
  filiais_venda?: Array<{
    filial: string | number
    qtde_vendida: number
    receita_total: number
    receita_formatted: string
    total_notas: number
  }>
  plano_acao?: string[]
}

export function SentinelInvestigationModal({
  anomaly,
  isOpen,
  onClose,
}: SentinelInvestigationModalProps) {
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<'geral' | 'produtos' | 'notas' | 'acao'>('geral')
  const [data, setData] = useState<InvestigationData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  const fetchDetail = useCallback(async () => {
    if (!anomaly) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${getApiBase()}/api/v1/sentinel/investigate?categoria=${encodeURIComponent(
          anomaly.categoria
        )}&codigo=${encodeURIComponent(anomaly.codigo)}`,
        {
          headers: authHeaders(),
          credentials: 'include',
        }
      )
      const json = await res.json()
      if (json.success && json.data) {
        setData(json.data)
      } else {
        setError(json.error || 'Não foi possível carregar os detalhes desta anomalia.')
      }
    } catch (e) {
      console.warn('[SentinelInvestigationModal] erro:', e)
      setError('Falha de conexão com a réplica analítica.')
    } finally {
      setLoading(false)
    }
  }, [anomaly, authHeaders])

  useEffect(() => {
    if (isOpen && anomaly) {
      setActiveTab('geral')
      fetchDetail()
    } else {
      setData(null)
    }
  }, [isOpen, anomaly, fetchDetail])

  // ESC key listener to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen || !anomaly) return null

  const isCritical = anomaly.severidade === 'CRITICAL'
  const isOpportunity = anomaly.severidade === 'OPPORTUNITY'
  const comp = data?.comparativo_sazonal
  const cli = data?.cliente
  const prods = data?.produtos_perdidos || []
  const notas = data?.ultimas_notas || []
  const planoAcao = data?.plano_acao || []

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 md:p-6 bg-black/80 backdrop-blur-md">
        {/* Backdrop click */}
        <div className="absolute inset-0" onClick={onClose} />

        {/* Modal Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-zinc-900 border border-zinc-700/60 rounded-2xl shadow-2xl shadow-black/80 overflow-hidden text-white z-10"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800 bg-zinc-950/70 shrink-0">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  'flex h-10 w-10 items-center justify-center rounded-xl border shrink-0',
                  isCritical
                    ? 'bg-rose-500/20 text-rose-400 border-rose-500/30 shadow-lg shadow-rose-950/50'
                    : isOpportunity
                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                    : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                )}
              >
                {isCritical ? (
                  <Flame size={20} className="animate-pulse" />
                ) : isOpportunity ? (
                  <TrendingUp size={20} />
                ) : (
                  <ShieldAlert size={20} />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border',
                      isCritical
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                        : isOpportunity
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    )}
                  >
                    {anomaly.severidade}
                  </span>
                  <span className="text-[11px] font-mono text-zinc-400">
                    Cód: #{anomaly.codigo}
                  </span>
                </div>
                <h2 className="text-base font-black text-white tracking-tight pt-0.5 line-clamp-1">
                  Investigação Sentinela: {anomaly.entidade}
                </h2>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-xl text-zinc-400 hover:text-white bg-zinc-800/80 hover:bg-zinc-700 border border-zinc-700 transition-colors cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          {/* Nav Tabs */}
          <div className="flex items-center gap-2 px-5 py-2.5 border-b border-zinc-800 bg-zinc-900/80 shrink-0 overflow-x-auto text-xs">
            <button
              type="button"
              onClick={() => setActiveTab('geral')}
              className={cn(
                'px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1.5',
                activeTab === 'geral'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
              )}
            >
              <FileText size={13} />
              <span>Dossiê & Comparativo Sazonal</span>
            </button>

            {prods.length > 0 && (
              <button
                type="button"
                onClick={() => setActiveTab('produtos')}
                className={cn(
                  'px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1.5',
                  activeTab === 'produtos'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                )}
              >
                <PackageX size={13} />
                <span>Produtos Abandonados ({prods.length})</span>
              </button>
            )}

            {notas.length > 0 && (
              <button
                type="button"
                onClick={() => setActiveTab('notas')}
                className={cn(
                  'px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1.5',
                  activeTab === 'notas'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                )}
              >
                <Receipt size={13} />
                <span>Últimas Notas Fiscais ({notas.length})</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => setActiveTab('acao')}
              className={cn(
                'px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1.5',
                activeTab === 'acao'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
              )}
            >
              <CheckCircle2 size={13} />
              <span>Plano de Ação Recomendado</span>
            </button>
          </div>

          {/* Modal Body */}
          <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-5">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-400">
                <RefreshCw size={24} className="animate-spin text-rose-400" />
                <span className="text-xs font-semibold">
                  Carregando dossiê transacional e histórico sazonal...
                </span>
              </div>
            ) : error ? (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                {error}
              </div>
            ) : (
              <>
                {/* ── TAB 1: VISÃO GERAL & COMPARATIVO SAZONAL ── */}
                {activeTab === 'geral' && (
                  <div className="space-y-4">
                    {/* Top KPI row */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                      <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-3.5 flex flex-col justify-between">
                        <span className="text-[10px] font-bold text-rose-300 uppercase tracking-wider">
                          Perda Financeira YoY
                        </span>
                        <div className="text-xl font-black text-rose-400 font-mono pt-1">
                          {comp?.perda_formatted || anomaly.impacto_formatted}
                        </div>
                        <span className="text-[10px] text-zinc-400 pt-0.5">
                          {comp?.variacao_pct}% no mesmo período
                        </span>
                      </div>

                      <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3.5 flex flex-col justify-between">
                        <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                          Período Recente
                        </span>
                        <div className="text-lg font-black text-white font-mono pt-1">
                          {comp?.fat_recente_formatted || 'R$ 0,00'}
                        </div>
                        <span className="text-[10px] text-zinc-500 pt-0.5">
                          {comp?.periodo_atual || anomaly.periodo_atual || 'Últimos 60 dias'} ({comp?.notas_recentes || anomaly.notas_atuais || 0} notas)
                        </span>
                      </div>

                      <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3.5 flex flex-col justify-between">
                        <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                          Mesmo Período Ano Anterior
                        </span>
                        <div className="text-lg font-black text-white font-mono pt-1">
                          {comp?.fat_anterior_formatted || 'R$ 0,00'}
                        </div>
                        <span className="text-[10px] text-zinc-500 pt-0.5">
                          {comp?.periodo_anterior || anomaly.periodo_anterior || 'Ano passado'} ({comp?.notas_anteriores || anomaly.notas_anteriores || 0} notas)
                        </span>
                      </div>

                      <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3.5 flex flex-col justify-between">
                        <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                          Última Compra
                        </span>
                        <div className="text-lg font-black text-amber-300 font-mono pt-1">
                          {cli?.ultima_compra_data || anomaly.data_ultima_compra || 'N/D'}
                        </div>
                        <span className="text-[10px] text-zinc-500 pt-0.5">
                          Filial Principal: Filial {cli?.principal_filial || '1'}
                        </span>
                      </div>
                    </div>

                    {/* Client Dossier Card */}
                    {cli && (
                      <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4 space-y-3">
                        <h3 className="text-xs font-black text-white uppercase tracking-wider flex items-center gap-1.5">
                          <UserCheck size={14} className="text-cyan-400" />
                          <span>Dossiê Comercial do Cliente</span>
                        </h3>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                          <div>
                            <span className="text-zinc-500 text-[10px] block">Razão Social / Nome:</span>
                            <span className="font-bold text-white">{cli.razao}</span>
                          </div>
                          <div>
                            <span className="text-zinc-500 text-[10px] block">RCA / Vendedor Responsável:</span>
                            <span className="font-bold text-cyan-300">RCA {cli.rca}</span>
                          </div>
                          <div>
                            <span className="text-zinc-500 text-[10px] block">Faturamento Vitalício (LTV):</span>
                            <span className="font-bold font-mono text-emerald-300">
                              {cli.faturamento_vitalicio_formatted}
                            </span>
                          </div>
                          <div>
                            <span className="text-zinc-500 text-[10px] block">Total de Notas na História:</span>
                            <span className="font-bold font-mono text-white">
                              {cli.total_historico_notas} notas
                            </span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Anomaly Description Banner */}
                    <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/10 text-xs text-amber-200 leading-relaxed">
                      <strong>Diagnóstico do Sentinela:</strong> {anomaly.descricao}
                    </div>
                  </div>
                )}

                {/* ── TAB 2: PRODUTOS ABANDONADOS ── */}
                {activeTab === 'produtos' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs text-zinc-400">
                      <span>
                        Produtos que o cliente comprava no mesmo período do ano passado e parou ou reduziu drasticamente as compras:
                      </span>
                    </div>

                    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 overflow-hidden">
                      <table className="w-full text-xs text-left">
                        <thead>
                          <tr className="border-b border-zinc-800 bg-zinc-800/40 text-zinc-400 font-bold uppercase text-[10px]">
                            <th className="px-3.5 py-2.5">Código / Produto</th>
                            <th className="px-3.5 py-2.5 text-right">Comprado Ano Passado</th>
                            <th className="px-3.5 py-2.5 text-right">Comprado Este Ano</th>
                            <th className="px-3.5 py-2.5 text-center">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/50">
                          {prods.map((p, i) => (
                            <tr key={`${p.codprod}-${i}`} className="hover:bg-zinc-800/30 transition-colors">
                              <td className="px-3.5 py-2.5">
                                <div className="font-bold text-white line-clamp-1">{p.descricao}</div>
                                <span className="font-mono text-[10px] text-zinc-500">#{p.codprod}</span>
                              </td>
                              <td className="px-3.5 py-2.5 text-right font-mono font-bold text-zinc-300">
                                {p.fat_ano_passado_formatted}
                                <span className="block text-[10px] text-zinc-500 font-normal">
                                  ({p.qtde_ano_passado} un)
                                </span>
                              </td>
                              <td className="px-3.5 py-2.5 text-right font-mono font-bold text-white">
                                {p.fat_recente_formatted}
                                <span className="block text-[10px] text-zinc-500 font-normal">
                                  ({p.qtde_recente} un)
                                </span>
                              </td>
                              <td className="px-3.5 py-2.5 text-center">
                                <span
                                  className={cn(
                                    'px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border',
                                    p.status === 'ABANDONADO'
                                      ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                                      : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                                  )}
                                >
                                  {p.status === 'ABANDONADO' ? 'Zerou Compra' : 'Queda Forte'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* ── TAB 3: ÚLTIMAS NOTAS FISCAIS ── */}
                {activeTab === 'notas' && (
                  <div className="space-y-3">
                    <div className="text-xs text-zinc-400">
                      Últimas notas fiscais emitidas para este cliente na base transacional:
                    </div>

                    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 overflow-hidden">
                      <table className="w-full text-xs text-left">
                        <thead>
                          <tr className="border-b border-zinc-800 bg-zinc-800/40 text-zinc-400 font-bold uppercase text-[10px]">
                            <th className="px-3.5 py-2.5">Nota Fiscal</th>
                            <th className="px-3.5 py-2.5">Filial</th>
                            <th className="px-3.5 py-2.5">Data de Emissão</th>
                            <th className="px-3.5 py-2.5 text-right">Qtd Itens</th>
                            <th className="px-3.5 py-2.5 text-right">Valor da Nota</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/50">
                          {notas.map((n, i) => (
                            <tr key={`${n.nota}-${i}`} className="hover:bg-zinc-800/30 transition-colors">
                              <td className="px-3.5 py-2.5 font-mono font-bold text-cyan-300">
                                NF #{n.nota}
                              </td>
                              <td className="px-3.5 py-2.5 text-zinc-300">
                                Filial {n.filial}
                              </td>
                              <td className="px-3.5 py-2.5 text-zinc-400 font-mono">
                                {n.data_emissao}
                              </td>
                              <td className="px-3.5 py-2.5 text-right font-mono text-zinc-400">
                                {n.total_itens} itens
                              </td>
                              <td className="px-3.5 py-2.5 text-right font-mono font-bold text-white">
                                {n.valor_formatted}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* ── TAB 4: PLANO DE AÇÃO ── */}
                {activeTab === 'acao' && (
                  <div className="space-y-4">
                    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 space-y-3">
                      <h3 className="text-xs font-black uppercase tracking-wider text-emerald-300 flex items-center gap-2">
                        <Sparkles size={15} />
                        <span>Ações Táticas Recomendadas pela IA para Retenção Imediata</span>
                      </h3>
                      <div className="space-y-2.5">
                        {planoAcao.map((acao, i) => (
                          <div key={i} className="flex items-start gap-2.5 text-xs text-zinc-200">
                            <div className="flex h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">
                              {i + 1}
                            </div>
                            <span className="leading-relaxed">{acao}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="p-3.5 rounded-xl border border-zinc-800 bg-zinc-950/60 text-xs text-zinc-400 space-y-1">
                      <span className="font-bold text-white block">Orientação Executiva:</span>
                      <p>
                        Clientes da Curva A com perda sazonal acentuada representam alto risco de migração para concorrência. Uma intervenção nos primeiros 15 dias da detecção aumenta a chance de recuperação da conta em até 78%.
                      </p>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Modal Footer */}
          <div className="flex items-center justify-between px-5 py-3 border-t border-zinc-800 bg-zinc-950/80 shrink-0 text-xs">
            <span className="text-[11px] text-zinc-500">
              LuminaAI Sentinela Autônomo • Base PostgreSQL Réplica Oficial
            </span>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 rounded-xl font-bold bg-zinc-800 hover:bg-zinc-700 text-zinc-200 hover:text-white border border-zinc-700 transition-colors cursor-pointer"
            >
              Fechar Investigação
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
