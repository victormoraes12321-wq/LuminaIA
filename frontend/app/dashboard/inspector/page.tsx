'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  Database,
  Code,
  Table,
  Cpu,
  RefreshCw,
  Play,
  CheckCircle,
  XCircle,
  FileText,
  Clock,
  Layout,
  Layers,
  ArrowRight,
  LineChart,
} from 'lucide-react'
import { Sidebar } from '@/components/Sidebar'
import { useAuth } from '@/context/AuthContext'
import { getApiBase } from '@/lib/utils'
import { DynamicRenderer } from '@/components/DynamicRenderer'

interface TraceItem {
  trace_id: string
  pergunta: string
  intent: string
  status: string
  execution_time_ms: number
  created_at: number
}

export default function InspectorPage() {
  const { loading: authLoading, user } = useAuth()
  const [traces, setTraces] = useState<TraceItem[]>([])
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null)
  const [traceDetail, setTraceDetail] = useState<any | null>(null)
  const [loadingTraces, setLoadingTraces] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  
  // Controles de Replay
  const [replayStartStep, setReplayStartStep] = useState('resolver')
  const [replayCallAi, setReplayCallAi] = useState(false)
  const [replayLoading, setReplayLoading] = useState(false)
  const [replayError, setReplayError] = useState<string | null>(null)
  const [replaySuccess, setReplaySuccess] = useState(false)
  
  // Abas de detalhes do inspector
  const [activeTab, setActiveTab] = useState<'visual' | 'nlu' | 'planning' | 'sql' | 'dataset' | 'transformer' | 'explanation'>('visual')
  const [showJsonInspector, setShowJsonInspector] = useState<string | null>(null)

  // Carrega lista de traces
  const fetchTraces = async () => {
    setLoadingTraces(true)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/query/inspector/traces`)
      if (res.ok) {
        const data = await res.json()
        setTraces(data)
      }
    } catch (e) {
      console.error("Error fetching traces", e)
    } finally {
      setLoadingTraces(false)
    }
  }

  // Carrega detalhes de um trace
  const fetchTraceDetail = async (id: string) => {
    setSelectedTraceId(id)
    setLoadingDetail(true)
    setReplayError(null)
    setReplaySuccess(false)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/query/inspector/trace/${id}`)
      if (res.ok) {
        const data = await res.json()
        setTraceDetail(data)
      }
    } catch (e) {
      console.error("Error fetching trace detail", e)
    } finally {
      setLoadingDetail(false)
    }
  }

  // Executa replay
  const runReplay = async () => {
    if (!selectedTraceId) return
    setReplayLoading(true)
    setReplayError(null)
    setReplaySuccess(false)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/query/inspector/replay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trace_id: selectedTraceId,
          start_step: replayStartStep,
          call_ai: replayCallAi
        })
      })
      
      const result = await res.json()
      if (res.ok && result.status === 'SUCCESS') {
        setReplaySuccess(true)
        // Atualiza a tela mesclando os novos dados de replay no detalhe do trace atual
        setTraceDetail((prev: any) => ({
          ...prev,
          semantic_plan: result.semantic_plan || prev.semantic_plan,
          canonical_plan: result.canonical_plan || prev.canonical_plan,
          execution_plan: result.execution_plan || prev.execution_plan,
          sql: result.sql || prev.sql,
          sample_rows: result.sample_rows || prev.sample_rows,
          transformer: result.transformer || prev.transformer,
          execution_time_ms: result.execution_time_ms || prev.execution_time_ms
        }))
      } else {
        const errMsg = result.detail?.error || result.detail || "Erro desconhecido no Replay"
        const errTb = result.detail?.traceback || ""
        setReplayError(`${errMsg}\n${errTb}`)
      }
    } catch (e: any) {
      setReplayError(e.message || "Erro de rede no Replay")
    } finally {
      setReplayLoading(false)
    }
  }

  useEffect(() => {
    fetchTraces()
  }, [])

  if (authLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center" style={{ background: 'rgb(var(--bg-base))' }}>
        <RefreshCw className="animate-spin text-lumina-500" size={32} />
      </div>
    )
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden" style={{ background: 'rgb(var(--bg-base))', color: 'rgb(var(--text-primary))' }}>
      {/* Sidebar Principal */}
      <Sidebar activePage="admin" />

      {/* Conteúdo Principal do Inspector */}
      <div className="flex flex-1 h-full min-w-0 overflow-hidden">
        {/* Painel Esquerdo: Lista de Traces */}
        <div className="w-[340px] h-full flex flex-col border-r border-zinc-200/50 dark:border-zinc-800/40 bg-zinc-50/10 dark:bg-zinc-950/10 flex-shrink-0">
          <div className="p-4 border-b border-zinc-200/50 dark:border-zinc-800/40 flex justify-between items-center">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-lumina-400">Inspector</h2>
              <p className="text-[10px] text-zinc-400">Traces analíticos de runtime</p>
            </div>
            <button
              onClick={fetchTraces}
              disabled={loadingTraces}
              className="p-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors disabled:opacity-40"
              title="Recarregar"
            >
              <RefreshCw size={14} className={loadingTraces ? "animate-spin" : ""} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
            {loadingTraces && traces.length === 0 ? (
              <div className="flex justify-center py-8">
                <RefreshCw className="animate-spin text-zinc-400" size={20} />
              </div>
            ) : traces.length === 0 ? (
              <div className="text-center py-12 text-zinc-400 text-xs">
                Nenhum trace analítico registrado.
              </div>
            ) : (
              traces.map((t) => (
                <button
                  key={t.trace_id}
                  onClick={() => fetchTraceDetail(t.trace_id)}
                  className={`w-full text-left p-3 rounded-xl border transition-all ${
                    selectedTraceId === t.trace_id
                      ? 'border-lumina-500 bg-lumina-500/5 shadow-sm'
                      : 'border-zinc-200/60 dark:border-zinc-800/50 bg-zinc-50/20 dark:bg-zinc-950/20 hover:border-zinc-300 dark:hover:border-zinc-700'
                  }`}
                >
                  <div className="flex justify-between items-start gap-2 mb-1.5">
                    <span className="text-[9px] font-mono text-zinc-400">
                      {t.trace_id.slice(0, 8)}
                    </span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold ${
                      t.status === 'READY' || t.status === 'SUCCESS' || t.status === 'FULL_RENDERING'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-rose-500/10 text-rose-400'
                    }`}>
                      {t.status}
                    </span>
                  </div>
                  <p className="text-xs font-semibold line-clamp-2 text-zinc-800 dark:text-zinc-200 mb-2">
                    {t.pergunta}
                  </p>
                  <div className="flex justify-between items-center text-[10px] text-zinc-400">
                    <span className="bg-zinc-100 dark:bg-zinc-800/80 px-1.5 py-0.5 rounded text-[9px] font-medium uppercase">
                      {t.intent}
                    </span>
                    <div className="flex items-center gap-1">
                      <Clock size={10} />
                      <span>{t.execution_time_ms ? `${Math.round(t.execution_time_ms)}ms` : 'N/A'}</span>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Painel Direito: Detalhes e Linhagem do Trace */}
        <div className="flex-1 h-full flex flex-col min-w-0 bg-zinc-100/10 dark:bg-zinc-900/10">
          {loadingDetail ? (
            <div className="flex-1 flex items-center justify-center">
              <RefreshCw className="animate-spin text-lumina-500" size={32} />
            </div>
          ) : !traceDetail ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center gap-3">
              <Layers size={48} className="text-zinc-300 dark:text-zinc-700 animate-pulse" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400">Nenhum trace selecionado</h3>
              <p className="text-xs text-zinc-500 max-w-sm">
                Selecione um trace analítico na barra lateral para inspecionar os planos de consulta, SQL e resultados físicos.
              </p>
            </div>
          ) : (
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
              {/* Cabeçalho do Trace */}
              <div className="p-4 border-b border-zinc-200/50 dark:border-zinc-800/40 bg-zinc-50/20 dark:bg-zinc-950/20 flex flex-col gap-3">
                <div className="flex justify-between items-start gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-200/60 dark:bg-zinc-800 text-zinc-500">
                        TRACE: {traceDetail.trace_id || selectedTraceId}
                      </span>
                      {traceDetail.execution_time_ms && (
                        <span className="text-[10px] text-zinc-400 flex items-center gap-1">
                          <Clock size={11} />
                          {Math.round(traceDetail.execution_time_ms)}ms de latência
                        </span>
                      )}
                    </div>
                    <h1 className="text-base font-bold text-zinc-800 dark:text-zinc-100">
                      "{traceDetail.pergunta}"
                    </h1>
                  </div>
                  
                  {/* Controles de Replay */}
                  <div className="flex flex-wrap items-center gap-2 bg-zinc-50 dark:bg-zinc-950 p-2 rounded-xl border border-zinc-200/50 dark:border-zinc-800/50">
                    <span className="text-[10px] font-bold text-zinc-400 uppercase px-1">Replay:</span>
                    <select
                      value={replayStartStep}
                      onChange={(e) => setReplayStartStep(e.target.value)}
                      className="text-xs px-2 py-1 rounded bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 font-semibold"
                    >
                      <option value="semantic">Passo 1: Semantic Plan</option>
                      <option value="canonical">Passo 2: Canonical Plan</option>
                      <option value="resolver">Passo 3: Resolver Plan</option>
                      <option value="sql">Passo 4: SQL Compile</option>
                      <option value="banco">Passo 5: Banco Clone</option>
                      <option value="transformer">Passo 6: Transformer</option>
                    </select>

                    <label className="flex items-center gap-1.5 text-[11px] font-semibold text-zinc-600 dark:text-zinc-400 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={replayCallAi}
                        onChange={(e) => setReplayCallAi(e.target.checked)}
                        className="rounded border-zinc-300 dark:border-zinc-700"
                      />
                      OpenAI (IA)
                    </label>

                    <button
                      onClick={runReplay}
                      disabled={replayLoading}
                      className="flex items-center gap-1 text-[11px] font-bold py-1 px-3 rounded-lg bg-lumina-gradient text-white shadow-sm hover:brightness-110 transition-all disabled:opacity-40"
                    >
                      {replayLoading ? <RefreshCw size={11} className="animate-spin" /> : <Play size={11} />}
                      <span>Rodar</span>
                    </button>
                  </div>
                </div>

                {/* Exibição de Mensagens de Replay */}
                {replaySuccess && (
                  <div className="flex items-center gap-2 p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
                    <CheckCircle size={14} />
                    <span>Replay analítico concluído e Hydrated na tela de forma perfeita!</span>
                  </div>
                )}
                {replayError && (
                  <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-mono whitespace-pre-wrap max-h-[160px] overflow-y-auto">
                    <div className="flex items-center gap-2 font-bold mb-1">
                      <XCircle size={14} />
                      <span>Falha de Execução no Replay</span>
                    </div>
                    {replayError}
                  </div>
                )}

                {/* Abas */}
                <div className="flex gap-1 border-b border-zinc-200/30 dark:border-zinc-800/30 pt-1">
                  {[
                    { id: 'visual', label: 'Dashboard', icon: Layout },
                    { id: 'nlu', label: 'Semantic & Canonical', icon: Sparkles },
                    { id: 'planning', label: 'Joins & Views', icon: Layers },
                    { id: 'sql', label: 'SQL Compilado', icon: Code },
                    { id: 'dataset', label: 'Resultado Banco', icon: Table },
                    { id: 'transformer', label: 'Transformer', icon: Cpu },
                    { id: 'explanation', label: 'Explicação IA', icon: FileText }
                  ].map(tab => {
                    const Icon = tab.icon
                    return (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-t-lg transition-all border-b-2 ${
                          activeTab === tab.id
                            ? 'border-lumina-500 text-lumina-400 bg-lumina-500/5'
                            : 'border-transparent text-zinc-400 hover:text-zinc-300'
                        }`}
                      >
                        <Icon size={12} />
                        <span>{tab.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Corpo de Conteúdo da Aba */}
              <div className="flex-1 overflow-y-auto p-6 min-h-0">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.2 }}
                    className="h-full"
                  >
                    {/* ABA 1: VISUAL (Dashboard final vivo!) */}
                    {activeTab === 'visual' && (
                      <div className="h-full flex flex-col gap-6">
                        {/* Linhagem Visual do Pipeline */}
                        <div className="bg-zinc-50/40 dark:bg-zinc-950/20 border border-zinc-200/50 dark:border-zinc-800/50 p-4 rounded-2xl">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3">Linhagem de Execução (Traceflow)</h3>
                          <div className="flex flex-wrap items-center gap-2 justify-between">
                            {[
                              { label: "Pergunta", desc: traceDetail.pergunta ? "Recebido" : "Faltando" },
                              { label: "Semantic Plan", desc: traceDetail.semantic_plan ? "NLU OK" : "Pulo" },
                              { label: "Canonical Plan", desc: traceDetail.canonical_plan ? "CKG OK" : "Pulo" },
                              { label: "Views", desc: traceDetail.execution_plan?.selected_views?.join(", ") || "Vazio" },
                              { label: "SQL Generator", desc: traceDetail.sql?.raw_sql ? "Compilado" : "Nulo" },
                              { label: "PG Clone", desc: traceDetail.sample_rows ? `${traceDetail.sample_rows.length} registros` : "Nulo" },
                              { label: "Transformer", desc: traceDetail.transformer?.output ? "Formatado" : "Nulo" },
                              { label: "Dashboard", desc: "Renderizado" }
                            ].map((step, idx) => (
                              <div key={step.label} className="flex items-center gap-2">
                                <div className="bg-zinc-100 dark:bg-zinc-800/80 p-2.5 rounded-xl border border-zinc-200/50 dark:border-zinc-800/50 min-w-[110px] text-center">
                                  <p className="text-[10px] font-bold text-zinc-800 dark:text-zinc-200">{step.label}</p>
                                  <p className="text-[9px] text-lumina-400 font-mono mt-0.5 truncate max-w-[100px]">{step.desc}</p>
                                </div>
                                {idx < 7 && <ArrowRight size={14} className="text-zinc-400 opacity-60 flex-shrink-0" />}
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Renderizador de Gráfico Dinâmico */}
                        <div className="flex-1 bg-zinc-50 dark:bg-zinc-950 p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col min-h-[360px]">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-4 flex items-center gap-1.5">
                            <LineChart size={14} className="text-lumina-400" />
                            <span>Visualização Final no Dashboard</span>
                          </h3>
                          <div className="flex-1 min-h-0">
                            {traceDetail.transformer?.output ? (
                              <DynamicRenderer
                                chartType={traceDetail.chart_type || traceDetail.chart?.type || 'TABLE'}
                                chartData={traceDetail.transformer?.output || traceDetail.chart?.data}
                                title={traceDetail.pergunta}
                              />
                            ) : (
                              <div className="flex flex-col items-center justify-center h-full text-zinc-400 gap-2 opacity-50">
                                <Layout size={32} />
                                <span className="text-xs">Dados do transformer ausentes ou vazios.</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* ABA 2: SEMANTIC & CANONICAL */}
                    {activeTab === 'nlu' && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-full">
                        {/* Semantic Plan Card */}
                        <div className="bg-zinc-50 dark:bg-zinc-950 p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 flex flex-col">
                          <div className="flex justify-between items-center mb-3">
                            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">1. Semantic Plan (Plano Conceitual IA)</h3>
                            <button
                              onClick={() => setShowJsonInspector(showJsonInspector === 'semantic' ? null : 'semantic')}
                              className="text-[10px] font-bold text-lumina-400 uppercase"
                            >
                              {showJsonInspector === 'semantic' ? 'Ocultar JSON' : 'Ver JSON'}
                            </button>
                          </div>
                          
                          {showJsonInspector === 'semantic' ? (
                            <pre className="flex-1 overflow-auto text-[10px] font-mono p-3 rounded bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                              {JSON.stringify(traceDetail.semantic_plan, null, 2)}
                            </pre>
                          ) : traceDetail.semantic_plan ? (
                            <div className="flex flex-col gap-4 text-xs">
                              <div>
                                <span className="text-zinc-400 font-bold block mb-1">Objetivo:</span>
                                <p className="font-semibold text-zinc-800 dark:text-zinc-200">{traceDetail.semantic_plan.goal}</p>
                              </div>
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <span className="text-zinc-400 font-bold block mb-1">Intenção:</span>
                                  <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-900 font-mono">{traceDetail.semantic_plan.intent}</span>
                                </div>
                                <div>
                                  <span className="text-zinc-400 font-bold block mb-1">Limite:</span>
                                  <span className="font-semibold">{traceDetail.semantic_plan.limit || 100}</span>
                                </div>
                              </div>
                              <div>
                                <span className="text-zinc-400 font-bold block mb-1">Entidades Selecionadas:</span>
                                <div className="flex flex-wrap gap-1">
                                  {traceDetail.semantic_plan.entities?.map((e: string) => (
                                    <span key={e} className="px-2 py-0.5 rounded bg-lumina-500/10 text-lumina-400 font-semibold">{e}</span>
                                  )) || <span className="text-zinc-400 italic">Nenhuma</span>}
                                </div>
                              </div>
                              <div>
                                <span className="text-zinc-400 font-bold block mb-1">Métricas Solicitadas:</span>
                                <div className="flex flex-wrap gap-1">
                                  {traceDetail.semantic_plan.metrics?.map((m: string) => (
                                    <span key={m} className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800/80 text-zinc-600 dark:text-zinc-300 font-semibold">{m}</span>
                                  )) || <span className="text-zinc-400 italic">Nenhuma</span>}
                                </div>
                              </div>
                              <div>
                                <span className="text-zinc-400 font-bold block mb-1">Dimensões Solicitadas:</span>
                                <div className="flex flex-wrap gap-1">
                                  {traceDetail.semantic_plan.dimensions?.map((d: string) => (
                                    <span key={d} className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800/80 text-zinc-600 dark:text-zinc-300 font-semibold">{d}</span>
                                  )) || <span className="text-zinc-400 italic">Nenhuma</span>}
                                </div>
                              </div>
                            </div>
                          ) : (
                            <p className="text-zinc-400 italic text-xs">Dados do plano semântico vazios.</p>
                          )}
                        </div>

                        {/* Canonical Plan Card */}
                        <div className="bg-zinc-50 dark:bg-zinc-950 p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 flex flex-col">
                          <div className="flex justify-between items-center mb-3">
                            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">2. Canonical Plan (Plano Traduzido CKG)</h3>
                            <button
                              onClick={() => setShowJsonInspector(showJsonInspector === 'canonical' ? null : 'canonical')}
                              className="text-[10px] font-bold text-lumina-400 uppercase"
                            >
                              {showJsonInspector === 'canonical' ? 'Ocultar JSON' : 'Ver JSON'}
                            </button>
                          </div>
                          
                          {showJsonInspector === 'canonical' ? (
                            <pre className="flex-1 overflow-auto text-[10px] font-mono p-3 rounded bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                              {JSON.stringify(traceDetail.canonical_plan, null, 2)}
                            </pre>
                          ) : traceDetail.canonical_plan ? (
                            <div className="flex flex-col gap-4 text-xs flex-1">
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <span className="text-zinc-400 font-bold block mb-1">Status de Resolução:</span>
                                  <span className={`px-2 py-0.5 rounded font-mono font-semibold ${
                                    traceDetail.canonical_plan.status === 'READY' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                                  }`}>{traceDetail.canonical_plan.status}</span>
                                </div>
                                <div>
                                  <span className="text-zinc-400 font-bold block mb-1">Visualização:</span>
                                  <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-900 font-semibold">{traceDetail.canonical_plan.suggested_visualization}</span>
                                </div>
                              </div>
                              
                              {/* Histórico detalhado de Mapeamento de Aliases */}
                              <div>
                                <span className="text-zinc-400 font-bold block mb-2">Histórico de Mapeamento (Aliases):</span>
                                <div className="flex flex-col gap-2 max-h-[220px] overflow-y-auto pr-1">
                                  {traceDetail.canonical_plan.canonicalization_trace && traceDetail.canonical_plan.canonicalization_trace.length > 0 ? (
                                    traceDetail.canonical_plan.canonicalization_trace.map((item: any, idx: number) => (
                                      <div key={idx} className="p-2 rounded bg-zinc-100/50 dark:bg-zinc-900 border border-zinc-200/50 dark:border-zinc-800/80 flex flex-col gap-1">
                                        <div className="flex justify-between items-center">
                                          <span className="font-bold text-[10px] text-zinc-500 font-mono">
                                            Termo: '{item.semantic_term}'
                                          </span>
                                          <span className="bg-lumina-500/10 text-lumina-400 text-[9px] px-1 py-0.2 rounded font-semibold uppercase">
                                            {item.type}
                                          </span>
                                        </div>
                                        <p className="font-semibold text-xs text-zinc-800 dark:text-zinc-200">
                                          Mapeado para: <span className="font-mono text-lumina-400">{item.canonical_name}</span>
                                        </p>
                                        <div className="flex justify-between items-center text-[9px] text-zinc-400 mt-0.5">
                                          <span>Confiança: <span className="text-emerald-400 font-bold">{item.confidence}</span></span>
                                          <span>Fonte: {item.source}</span>
                                        </div>
                                      </div>
                                    ))
                                  ) : (
                                    <p className="text-zinc-400 italic text-[11px]">Nenhum mapeamento de alias ou heurística aplicada.</p>
                                  )}
                                </div>
                              </div>
                            </div>
                          ) : (
                            <p className="text-zinc-400 italic text-xs">Dados do plano canônico vazios.</p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* ABA 3: PLANNING (Views Escolhidas & Joins) */}
                    {activeTab === 'planning' && (
                      <div className="bg-zinc-50 dark:bg-zinc-950 p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 flex flex-col h-full">
                        <div className="flex justify-between items-center mb-4">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">Metadata Resolver (Passo Físico e Joins)</h3>
                          <button
                            onClick={() => setShowJsonInspector(showJsonInspector === 'execution' ? null : 'execution')}
                            className="text-[10px] font-bold text-lumina-400 uppercase"
                          >
                            {showJsonInspector === 'execution' ? 'Ocultar JSON' : 'Ver JSON'}
                          </button>
                        </div>

                        {showJsonInspector === 'execution' ? (
                          <pre className="flex-1 overflow-auto text-[10px] font-mono p-3 rounded bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                            {JSON.stringify(traceDetail.execution_plan, null, 2)}
                          </pre>
                        ) : traceDetail.execution_plan ? (
                          <div className="flex flex-col gap-6 text-xs flex-1">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                              {/* Views Selecionadas */}
                              <div className="p-4 rounded-xl border border-zinc-200/50 dark:border-zinc-800 bg-zinc-100/50 dark:bg-zinc-900">
                                <h4 className="font-bold text-zinc-400 uppercase text-[10px] mb-2">Views Físicas Mapeadas</h4>
                                <div className="flex flex-col gap-2">
                                  {traceDetail.execution_plan.selected_views && traceDetail.execution_plan.selected_views.length > 0 ? (
                                    traceDetail.execution_plan.selected_views.map((v: string) => (
                                      <div key={v} className="flex items-center gap-2 p-2 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                                        <Database size={12} className="text-lumina-400" />
                                        <span className="font-mono font-bold text-zinc-800 dark:text-zinc-200">{v}</span>
                                      </div>
                                    ))
                                  ) : (
                                    <p className="text-zinc-400 italic">Nenhuma view selecionada no plano.</p>
                                  )}
                                </div>
                              </div>

                              {/* Caminho de Joins */}
                              <div className="p-4 rounded-xl border border-zinc-200/50 dark:border-zinc-800 bg-zinc-100/50 dark:bg-zinc-900">
                                <h4 className="font-bold text-zinc-400 uppercase text-[10px] mb-2">Relacionamentos e Junções Físicas (ON)</h4>
                                <div className="flex flex-col gap-2 max-h-[220px] overflow-y-auto">
                                  {traceDetail.joins && traceDetail.joins.length > 0 ? (
                                    traceDetail.joins.map((join: any, idx: number) => (
                                      <div key={idx} className="p-2 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-1">
                                        <span className="font-bold text-[10px] text-zinc-500 font-mono">JOIN {idx + 1}</span>
                                        <p className="font-mono text-zinc-800 dark:text-zinc-200 text-xs">
                                          <span className="text-lumina-400">{join.left_table}</span> ON {join.left_column} = <span className="text-lumina-400">{join.right_table}</span>.{join.right_column}
                                        </p>
                                      </div>
                                    ))
                                  ) : (
                                    <p className="text-zinc-400 italic">Nenhum JOIN necessário (View única na consulta).</p>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Justificativa e Scores das Views Candidatas */}
                            {traceDetail.execution_plan.resolution_justification && (
                              <div className="p-4 rounded-xl border border-zinc-200/50 dark:border-zinc-800 bg-zinc-100/50 dark:bg-zinc-900">
                                <h4 className="font-bold text-zinc-400 uppercase text-[10px] mb-2">Pontuação de Relevância de Mapeamento de Views</h4>
                                <pre className="text-[10px] font-mono bg-zinc-50 dark:bg-zinc-950 p-3 rounded border border-zinc-200 dark:border-zinc-800 overflow-x-auto max-h-[160px]">
                                  {typeof traceDetail.execution_plan.resolution_justification === 'string'
                                    ? traceDetail.execution_plan.resolution_justification
                                    : JSON.stringify(traceDetail.execution_plan.resolution_justification, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        ) : (
                          <p className="text-zinc-400 italic text-xs">Dados de execução e planejamento físicos indisponíveis.</p>
                        )}
                      </div>
                    )}

                    {/* ABA 4: SQL & PARAMETERS */}
                    {activeTab === 'sql' && (
                      <div className="bg-zinc-50 dark:bg-zinc-950 p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 flex flex-col h-full">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3 flex items-center gap-1.5">
                          <Code size={14} className="text-lumina-400" />
                          <span>SQL Compilado Físico</span>
                        </h3>
                        {traceDetail.sql?.raw_sql ? (
                          <div className="flex flex-col gap-4 flex-1 min-h-0">
                            {/* Bloco SQL formatado */}
                            <pre className="flex-1 overflow-auto text-xs font-mono p-4 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-100 whitespace-pre-wrap max-h-[300px]">
                              {traceDetail.sql.raw_sql}
                            </pre>
                            
                            {/* Parâmetros Binds */}
                            <div className="p-4 rounded-xl border border-zinc-200/50 dark:border-zinc-800 bg-zinc-100/50 dark:bg-zinc-900">
                              <h4 className="font-bold text-zinc-400 uppercase text-[10px] mb-2">Parâmetros Parametrizados (Binds)</h4>
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                {Object.entries(traceDetail.sql.parameters || {}).map(([key, val]: any) => (
                                  <div key={key} className="p-2 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                                    <span className="text-[9px] font-mono text-zinc-400 block mb-0.5">{key}</span>
                                    <span className="text-xs font-bold font-mono text-lumina-400">{String(val)}</span>
                                  </div>
                                ))}
                                {Object.keys(traceDetail.sql.parameters || {}).length === 0 && (
                                  <span className="text-zinc-400 italic text-xs col-span-4">Nenhum parâmetro injetado.</span>
                                )}
                              </div>
                            </div>
                          </div>
                        ) : (
                          <p className="text-zinc-400 italic text-xs">Sintaxe SQL ausente.</p>
                        )}
                      </div>
                    )}

                    {/* ABA 5: RESULTADO DO BANCO (Sample Rows) */}
                    {activeTab === 'dataset' && (
                      <div className="bg-zinc-50 dark:bg-zinc-950 p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 flex flex-col h-full">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3 flex items-center gap-1.5">
                          <Table size={14} className="text-lumina-400" />
                          <span>Registros Físicos Retornados do Banco Clone</span>
                        </h3>
                        {traceDetail.sample_rows && traceDetail.sample_rows.length > 0 ? (
                          <div className="flex-1 overflow-auto max-h-[360px] rounded-xl border border-zinc-200 dark:border-zinc-800/80 bg-zinc-100/20 dark:bg-zinc-900/30">
                            <table className="w-full text-left border-collapse text-xs">
                              <thead>
                                <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-100/50 dark:bg-zinc-950/80">
                                  {Object.keys(traceDetail.sample_rows[0]).map(key => (
                                    <th key={key} className="p-3 font-mono font-bold uppercase tracking-wider text-zinc-500 text-[10px]">
                                      {key}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {traceDetail.sample_rows.map((row: any, rIdx: number) => (
                                  <tr key={rIdx} className="border-b border-zinc-200/50 dark:border-zinc-800/40 hover:bg-zinc-50 dark:hover:bg-zinc-850/30">
                                    {Object.values(row).map((val: any, cIdx: number) => (
                                      <td key={cIdx} className="p-3 text-zinc-700 dark:text-zinc-300 font-medium">
                                        {val === null || val === undefined
                                          ? <span className="text-zinc-500 font-mono">null</span>
                                          : typeof val === 'number'
                                          ? val.toLocaleString('pt-BR')
                                          : String(val)}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center justify-center p-12 text-zinc-400 gap-1 opacity-50">
                            <Table size={24} />
                            <span className="text-xs">Nenhum registro retornado do banco ou dataset vazio.</span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* ABA 6: TRANSFORMER */}
                    {activeTab === 'transformer' && (
                      <div className="bg-zinc-50 dark:bg-zinc-950 p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 flex flex-col h-full">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3 flex items-center gap-1.5">
                          <Cpu size={14} className="text-lumina-400" />
                          <span>Payload de Saída do Transformer (Estrutura do Gráfico)</span>
                        </h3>
                        {traceDetail.transformer?.output ? (
                          <pre className="flex-1 overflow-auto text-xs font-mono p-4 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-100 max-h-[360px]">
                            {JSON.stringify(traceDetail.transformer.output, null, 2)}
                          </pre>
                        ) : (
                          <p className="text-zinc-400 italic text-xs">Dados do transformer vazios.</p>
                        )}
                      </div>
                    )}

                    {/* ABA 7: EXPLAINABILITY (IA) */}
                    {activeTab === 'explanation' && (
                      <div className="bg-zinc-50 dark:bg-zinc-950 p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 flex flex-col h-full">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3 flex items-center gap-1.5">
                          <FileText size={14} className="text-lumina-400" />
                          <span>Resumo Explicativo da IA (Explainability)</span>
                        </h3>
                        {traceDetail.llm_response ? (
                          <div className="flex-1 flex flex-col gap-4">
                            <div className="p-4 rounded-xl bg-zinc-100/50 dark:bg-zinc-900/60 border border-zinc-200/50 dark:border-zinc-800/80 text-zinc-800 dark:text-zinc-200 text-sm leading-relaxed whitespace-pre-wrap max-h-[220px] overflow-y-auto">
                              {traceDetail.llm_response}
                            </div>
                            
                            {/* Prompt enviado para a IA */}
                            {traceDetail.llm_prompt && (
                              <div className="flex-1 flex flex-col min-h-0">
                                <span className="text-[10px] font-bold text-zinc-400 uppercase mb-2">Prompt completo enviado para a OpenAI:</span>
                                <pre className="flex-1 overflow-auto text-[10px] font-mono p-3 rounded bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 whitespace-pre-wrap max-h-[160px]">
                                  {traceDetail.llm_prompt}
                                </pre>
                              </div>
                            )}
                          </div>
                        ) : (
                          <p className="text-zinc-400 italic text-xs">Resposta do explainability vazia ou não gerada.</p>
                        )}
                      </div>
                    )}
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
