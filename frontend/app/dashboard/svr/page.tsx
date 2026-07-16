'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Layers,
  GitBranch,
  ShieldCheck,
  History,
  Play,
  Plus,
  X,
  Search,
  CheckCircle,
  RefreshCw
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { Sidebar } from '@/components/Sidebar'
import { getApiBase } from '@/lib/utils'

interface SVRSummary {
  total_concepts: number
  by_type: Record<string, number>
  by_status: {
    ACTIVE: number
    LEGACY: number
    DEPRECATED: number
    OBSOLETE: number
  }
  recent_activities: Array<{
    id: string
    concept_id: string
    action: string
    user: string
    time: string
    reason: string | null
    details: Record<string, string | number | boolean | null | undefined>
  }>
}

interface ConceptHistory {
  compatibility: Array<{
    semantic_version: string
    mapping_version: string
    status: string
    data_vigencia: string
    motivo?: string | null
    impacto?: string | null
  }>
}

interface SVRConceptItem {
  concept_id: string
  concept_type: string
  semantic_version: string
  mapping_version: string
  status: string
  last_updated: string
}

interface MigrationReport {
  concept_id: string
  target_semantic_version: string
  target_mapping_version: string
  impact_level: 'BAIXO' | 'MEDIO' | 'ALTO'
  affected_blueprints_count: number
  affected_blueprints: Array<{
    id: string
    nome: string
    tipo_analise: string
    versao_atual: number
    autor: string
    motivo_uso: string
  }>
  affected_dashboards_count: number
  affected_dashboards: Array<{
    id: string
    nome: string
    autor: string
  }>
  estimated_cache_invalidation_count: number
  migration_instructions: string
}

export default function VersionCenterPage() {
  const { token, loading: authLoading } = useAuth()
  
  // States
  const [summary, setSummary] = useState<SVRSummary | null>(null)
  const [concepts, setConcepts] = useState<SVRConceptItem[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  
  // Modal states
  const [activeModal, setActiveModal] = useState<'history' | 'migration' | 'register' | null>(null)
  const [selectedConcept, setSelectedConcept] = useState<string | null>(null)
  const [conceptHistory, setConceptHistory] = useState<ConceptHistory | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  
  // Migration simulation state
  const [simulatedConcept, setSimulatedConcept] = useState('')
  const [targetSemantic, setTargetSemantic] = useState('2.0')
  const [targetMapping, setTargetMapping] = useState('2')
  const [migrationReport, setMigrationReport] = useState<MigrationReport | null>(null)
  const [migrationLoading, setMigrationLoading] = useState(false)

  // Registration form state
  const [regConceptId, setRegConceptId] = useState('')
  const [regType, setRegType] = useState('METRIC')
  const [regSemantic, setRegSemantic] = useState('2.0')
  const [regMapping, setRegMapping] = useState('2')
  const [regSnapshot, setRegSnapshot] = useState('{\n  "name": "Faturamento Líquido",\n  "label": "Faturamento Líquido sem devoluções",\n  "physical_col": "vl_total_venda"\n}')
  const [regReason, setRegReason] = useState('')
  const [regImpact, setRegImpact] = useState('')
  const [regSuccess, setRegSuccess] = useState(false)

  // Fetch initial data
  const fetchData = useCallback(async () => {
    if (!token) return
    try {
      setRefreshing(true)
      // GET summary
      const resSum = await fetch(`${getApiBase()}/api/v1/svr/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (resSum.ok) {
        const sumData = await resSum.json()
        setSummary(sumData)
      }

      const conceptList: SVRConceptItem[] = [
        { concept_id: 'MET_001', concept_type: 'METRIC', semantic_version: '1.0', mapping_version: '1', status: 'ACTIVE', last_updated: '2026-07-09T10:00:00Z' },
        { concept_id: 'MET_002', concept_type: 'METRIC', semantic_version: '1.0', mapping_version: '1', status: 'ACTIVE', last_updated: '2026-07-09T10:00:00Z' },
        { concept_id: 'MET_003', concept_type: 'METRIC', semantic_version: '1.0', mapping_version: '1', status: 'ACTIVE', last_updated: '2026-07-09T10:00:00Z' },
        { concept_id: 'DIM_001', concept_type: 'DIMENSION', semantic_version: '1.0', mapping_version: '1', status: 'ACTIVE', last_updated: '2026-07-09T10:00:00Z' },
        { concept_id: 'DIM_002', concept_type: 'DIMENSION', semantic_version: '1.0', mapping_version: '1', status: 'ACTIVE', last_updated: '2026-07-09T10:00:00Z' },
        { concept_id: 'PER_CURRENT_MONTH', concept_type: 'PERIOD', semantic_version: '1.0', mapping_version: '1', status: 'ACTIVE', last_updated: '2026-07-09T10:00:00Z' },
      ]
      
      setConcepts(conceptList)
      setLoading(false)
      setRefreshing(false)
    } catch (err) {
      console.error('Error fetching SVR data', err)
      setLoading(false)
      setRefreshing(false)
    }
  }, [token])

  useEffect(() => {
    if (!token) return
    const timer = window.setTimeout(() => {
      void fetchData()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [fetchData, token])

  // Open history modal
  const handleOpenHistory = async (conceptId: string) => {
    setSelectedConcept(conceptId)
    setActiveModal('history')
    setHistoryLoading(true)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/svr/concepts/${conceptId}/history`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const histData = await res.json()
        setConceptHistory(histData)
      }
    } catch (err) {
      console.error('Error loading history', err)
    } finally {
      setHistoryLoading(false)
    }
  }

  // Open migration modal
  const handleOpenMigration = (conceptId: string) => {
    setSimulatedConcept(conceptId)
    setMigrationReport(null)
    setActiveModal('migration')
  }

  // Simulate migration
  const handleSimulateMigration = async () => {
    setMigrationLoading(true)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/svr/migration/evaluate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          concept_id: simulatedConcept,
          new_semantic_version: targetSemantic,
          new_mapping_version: targetMapping
        })
      })
      if (res.ok) {
        const report = await res.json()
        setMigrationReport(report)
      }
    } catch (err) {
      console.error('Error evaluating migration', err)
    } finally {
      setMigrationLoading(false)
    }
  }

  // Register concept
  const handleRegisterConcept = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      let snapObj = {}
      try {
        snapObj = JSON.parse(regSnapshot)
      } catch {
        alert('Snapshot JSON inválido!')
        return
      }

      const res = await fetch(`${getApiBase()}/api/v1/svr/concepts/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          concept_id: regConceptId,
          concept_type: regType,
          semantic_version: regSemantic,
          mapping_version: regMapping,
          snapshot: snapObj,
          motivo: regReason,
          impacto: regImpact
        })
      })
      if (res.ok) {
        setRegSuccess(true)
        setTimeout(() => {
          setRegSuccess(false)
          setActiveModal(null)
          fetchData()
        }, 1500)
      }
    } catch (err) {
      console.error('Error registering concept', err)
    }
  }

  // Change active status
  const handleChangeStatus = async (conceptId: string, semanticVer: string, mappingVer: string, newStatus: string) => {
    if (!confirm(`Tem certeza que deseja marcar a versão S:${semanticVer} | M:${mappingVer} do conceito ${conceptId} como ${newStatus}?`)) {
      return
    }
    try {
      const res = await fetch(`${getApiBase()}/api/v1/svr/concepts/deprecate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          concept_id: conceptId,
          semantic_version: semanticVer,
          mapping_version: mappingVer,
          status: newStatus,
          motivo: 'Alteração manual no Version Center'
        })
      })
      if (res.ok) {
        fetchData()
        if (selectedConcept === conceptId) {
          handleOpenHistory(conceptId)
        }
      }
    } catch (err) {
      console.error('Error changing status', err)
    }
  }

  if (authLoading || loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-3 text-cyan-400">
          <RefreshCw className="h-10 w-10 animate-spin" />
          <span className="text-sm font-semibold tracking-wider">Carregando Version Center...</span>
        </div>
      </div>
    )
  }

  const filteredConcepts = concepts.filter(c =>
    c.concept_id.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      {/* Sidebar de navegação */}
      <Sidebar />

      {/* Main Panel */}
      <main
        className="flex-1 flex flex-col overflow-y-auto p-8 relative min-w-0"
        style={{ marginLeft: 'var(--sidebar-w)' }}
      >
        {/* Background glow elements */}
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-10 left-1/3 w-[30rem] h-[30rem] bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

        {/* Header */}
        <div className="flex justify-between items-center mb-8 z-10">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent flex items-center gap-2">
              <Layers className="h-8 w-8 text-cyan-400" />
              Semantic Version Registry (SVR)
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Governança semântica de regras de negócios, mapeamentos físicos e versionamento do LuminaAI.
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setRegConceptId('')
                setRegReason('')
                setRegImpact('')
                setActiveModal('register')
              }}
              className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-cyan-500/20 transition-all duration-300 transform hover:scale-[1.02]"
            >
              <Plus className="h-4 w-4" />
              Nova Versão
            </button>
            <button
              onClick={fetchData}
              disabled={refreshing}
              className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl hover:bg-slate-800 transition-all"
            >
              <RefreshCw className={`h-4 w-4 text-slate-400 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Estatísticas / KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8 z-10">
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-850 p-6 rounded-2xl flex flex-col justify-between">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">Total de Conceitos</span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-extrabold text-slate-100">{summary?.total_concepts ?? 0}</span>
              <span className="text-xs text-cyan-400">Ativos no SVR</span>
            </div>
            <div className="h-1 bg-cyan-500/20 rounded-full mt-4 overflow-hidden">
              <div className="h-full bg-cyan-400 w-full" />
            </div>
          </div>

          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-850 p-6 rounded-2xl flex flex-col justify-between">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">Versões Ativas (Vigentes)</span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-extrabold text-emerald-400">{summary?.by_status.ACTIVE ?? 0}</span>
              <span className="text-xs text-slate-400">Produção</span>
            </div>
            <div className="h-1 bg-emerald-500/20 rounded-full mt-4 overflow-hidden">
              <div className="h-full bg-emerald-400 w-full" />
            </div>
          </div>

          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-850 p-6 rounded-2xl flex flex-col justify-between">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">Versões Legadas / Depreciadas</span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-extrabold text-amber-500">{(summary?.by_status.LEGACY ?? 0) + (summary?.by_status.DEPRECATED ?? 0)}</span>
              <span className="text-xs text-slate-400">Em transição</span>
            </div>
            <div className="h-1 bg-amber-500/20 rounded-full mt-4 overflow-hidden">
              <div className="h-full bg-amber-400 w-full" />
            </div>
          </div>

          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-850 p-6 rounded-2xl flex flex-col justify-between">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">Objetos Obsoletos</span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-extrabold text-red-500">{summary?.by_status.OBSOLETE ?? 0}</span>
              <span className="text-xs text-slate-400">Descontinuados</span>
            </div>
            <div className="h-1 bg-red-500/20 rounded-full mt-4 overflow-hidden">
              <div className="h-full bg-red-400 w-full" />
            </div>
          </div>
        </div>

        {/* Tabela de Conceitos & Auditoria Recente */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 z-10 flex-1">
          {/* Lista de Conceitos */}
          <div className="lg:col-span-2 bg-slate-900/40 backdrop-blur-md border border-slate-850 rounded-2xl p-6 flex flex-col h-full">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold text-slate-200">Matriz de Conceitos Versionados</h2>
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                <input
                  type="text"
                  placeholder="Pesquisar ID..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="pl-9 pr-4 py-2 text-xs bg-slate-950 border border-slate-800 rounded-xl focus:border-cyan-500 focus:outline-none w-52 text-slate-200"
                />
              </div>
            </div>

            <div className="overflow-x-auto flex-1">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400">
                    <th className="pb-3">ID Corporativo</th>
                    <th className="pb-3">Tipo</th>
                    <th className="pb-3 text-center">Semantic Ver.</th>
                    <th className="pb-3 text-center">Mapping Ver.</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-850 text-sm">
                  {filteredConcepts.map(c => (
                    <tr key={c.concept_id} className="hover:bg-slate-900/20 transition-all">
                      <td className="py-4 font-mono font-semibold text-cyan-400">{c.concept_id}</td>
                      <td className="py-4">
                        <span className="text-xs px-2.5 py-1 bg-slate-800/80 border border-slate-700 text-slate-300 rounded-md font-medium">
                          {c.concept_type}
                        </span>
                      </td>
                      <td className="py-4 text-center font-mono">v{c.semantic_version}</td>
                      <td className="py-4 text-center font-mono">{c.mapping_version}</td>
                      <td className="py-4">
                        <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          ACTIVE
                        </span>
                      </td>
                      <td className="py-4 text-right flex justify-end gap-2">
                        <button
                          onClick={() => handleOpenHistory(c.concept_id)}
                          className="p-1.5 bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 rounded-lg text-xs flex items-center gap-1 transition-all"
                          title="Histórico e Auditoria"
                        >
                          <History className="h-3.5 w-3.5" />
                          Linha do Tempo
                        </button>
                        <button
                          onClick={() => handleOpenMigration(c.concept_id)}
                          className="p-1.5 bg-slate-950 border border-slate-800 hover:border-slate-700 text-cyan-400 rounded-lg text-xs flex items-center gap-1 transition-all"
                          title="Simular Impacto"
                        >
                          <Play className="h-3.5 w-3.5 fill-cyan-400" />
                          Simular
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Atividades Recentes e Auditoria */}
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-850 rounded-2xl p-6 flex flex-col h-full">
            <h2 className="text-lg font-bold text-slate-200 mb-6 flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-indigo-400" />
              Auditoria e Evolução
            </h2>

            <div className="flex-1 overflow-y-auto space-y-4 max-h-[480px] pr-2">
              {summary?.recent_activities.map(a => (
                <div key={a.id} className="p-4 bg-slate-950/60 border border-slate-850 rounded-xl relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500" />
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-mono font-bold text-xs text-cyan-400">{a.concept_id}</span>
                    <span className="text-[10px] text-slate-500">{new Date(a.time).toLocaleTimeString()}</span>
                  </div>
                  <div className="text-xs font-semibold text-slate-300">{a.action === 'REGISTER' ? 'Nova versão registrada' : 'Alteração de status'}</div>
                  <div className="text-[11px] text-slate-400 mt-1 italic">&quot;{a.reason || 'Sem descrição'}&quot;</div>
                  <div className="flex justify-between items-center mt-3 text-[10px] text-slate-500">
                    <span>Autor: {a.user.split('@')[0]}</span>
                    <span className="font-mono">{a.details.version || 'v1.0'}</span>
                  </div>
                </div>
              ))}
              {!summary?.recent_activities.length && (
                <div className="flex flex-col items-center justify-center h-full text-slate-500">
                  <History className="h-8 w-8 mb-2" />
                  <span className="text-xs">Nenhuma atividade recente registrada</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── MODAL: HISTÓRICO & AUDITORIA ── */}
        <AnimatePresence>
          {activeModal === 'history' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4"
            >
              <motion.div
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.95 }}
                className="w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-3xl p-8 relative overflow-hidden shadow-2xl"
              >
                <button
                  onClick={() => setActiveModal(null)}
                  className="absolute top-6 right-6 p-2 bg-slate-950 border border-slate-850 hover:bg-slate-800 rounded-xl text-slate-400 hover:text-slate-200 transition-all"
                >
                  <X className="h-4 w-4" />
                </button>

                <h3 className="text-xl font-extrabold text-gradient flex items-center gap-2 mb-2">
                  <History className="h-5 w-5 text-cyan-400" />
                  Linha do Tempo de Governança: {selectedConcept}
                </h3>
                <p className="text-xs text-slate-400 mb-6">Registro de snapshots imutáveis e matriz de compatibilidade.</p>

                {historyLoading ? (
                  <div className="flex justify-center py-12">
                    <RefreshCw className="h-8 w-8 text-cyan-400 animate-spin" />
                  </div>
                ) : (
                  <div className="space-y-6 max-h-[400px] overflow-y-auto pr-2">
                    {conceptHistory?.compatibility.map((m, idx: number) => (
                      <div key={idx} className="relative pl-6 border-l border-slate-800 pb-4 last:pb-0">
                        <div className="absolute left-[-5px] top-1.5 w-2.5 h-2.5 rounded-full bg-cyan-400" />
                        <div className="flex items-center gap-3">
                          <span className="font-mono font-bold text-xs bg-slate-950 border border-slate-800 px-2 py-0.5 rounded text-cyan-400">
                            S: v{m.semantic_version} | M: {m.mapping_version}
                          </span>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                            m.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'
                          }`}>
                            {m.status}
                          </span>
                          <span className="text-xs text-slate-500">Vigência: {new Date(m.data_vigencia).toLocaleDateString()}</span>
                        </div>
                        <div className="text-xs text-slate-300 mt-2 font-semibold italic">&quot;{m.motivo || 'Bootstrap inicial'}&quot;</div>
                        <div className="text-[11px] text-slate-400 mt-1">Impacto previsto: {m.impacto || 'Nenhum'}</div>
                        
                        {m.status === 'ACTIVE' && (
                          <div className="flex gap-2 mt-3">
                            <button
                              onClick={() => handleChangeStatus(selectedConcept!, m.semantic_version, m.mapping_version, 'LEGACY')}
                              className="text-[10px] px-2 py-1 bg-slate-950 border border-slate-850 hover:bg-slate-800 rounded text-slate-400"
                            >
                              Depreciar para LEGACY
                            </button>
                            <button
                              onClick={() => handleChangeStatus(selectedConcept!, m.semantic_version, m.mapping_version, 'DEPRECATED')}
                              className="text-[10px] px-2 py-1 bg-slate-950 border border-slate-850 hover:bg-slate-800 rounded text-amber-500/80"
                            >
                              Marcar DEPRECATED
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── MODAL: SIMULAÇÃO DE MIGRAÇÃO ── */}
        <AnimatePresence>
          {activeModal === 'migration' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4"
            >
              <motion.div
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.95 }}
                className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl p-8 relative overflow-hidden shadow-2xl"
              >
                <button
                  onClick={() => setActiveModal(null)}
                  className="absolute top-6 right-6 p-2 bg-slate-950 border border-slate-850 hover:bg-slate-800 rounded-xl text-slate-400 hover:text-slate-200 transition-all"
                >
                  <X className="h-4 w-4" />
                </button>

                <h3 className="text-xl font-extrabold text-gradient flex items-center gap-2 mb-2">
                  <Play className="h-5 w-5 fill-cyan-400 text-cyan-400" />
                  Simulador de Impacto de Migração
                </h3>
                <p className="text-xs text-slate-400 mb-6">Analisa a árvore de dependências do LuminaAI antes de publicar uma alteração.</p>

                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Conceito Alvo</label>
                    <input
                      type="text"
                      value={simulatedConcept}
                      disabled
                      className="w-full p-2.5 bg-slate-950 border border-slate-850 rounded-xl text-xs text-slate-400 font-mono focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Destino: Semantic Ver.</label>
                    <input
                      type="text"
                      value={targetSemantic}
                      onChange={e => setTargetSemantic(e.target.value)}
                      className="w-full p-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Destino: Mapping Ver.</label>
                    <input
                      type="text"
                      value={targetMapping}
                      onChange={e => setTargetMapping(e.target.value)}
                      className="w-full p-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                </div>

                <button
                  onClick={handleSimulateMigration}
                  disabled={migrationLoading}
                  className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2"
                >
                  {migrationLoading ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <GitBranch className="h-4 w-4" />
                      Avaliar Dependências e Cache
                    </>
                  )}
                </button>

                {/* Report Section */}
                {migrationReport && (
                  <div className="mt-6 p-5 bg-slate-950 border border-slate-850 rounded-2xl overflow-y-auto max-h-[220px]">
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-xs font-bold text-slate-400">Nível de Risco do Impacto</span>
                      <span className={`text-[10px] font-extrabold px-3 py-1 rounded-full border ${
                        migrationReport.impact_level === 'ALTO' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 
                        migrationReport.impact_level === 'MEDIO' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                        'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      }`}>
                        {migrationReport.impact_level}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-4 text-xs text-slate-300">
                      <div>Blueprints Afetados: <span className="font-bold text-white font-mono">{migrationReport.affected_blueprints_count}</span></div>
                      <div>Caches Invalidados: <span className="font-bold text-white font-mono">{migrationReport.estimated_cache_invalidation_count}</span></div>
                    </div>

                    {migrationReport.affected_blueprints.length > 0 && (
                      <div className="space-y-2 mt-3">
                        <span className="text-[10px] font-bold uppercase text-slate-500">Relação de Blueprints Afetados</span>
                        {migrationReport.affected_blueprints.map((bp, i) => (
                          <div key={i} className="flex justify-between items-center text-xs p-2 bg-slate-900 border border-slate-850 rounded-lg">
                            <span className="font-semibold text-slate-200">{bp.nome}</span>
                            <span className="text-[10px] px-2 py-0.5 bg-slate-800 rounded font-mono text-cyan-400">v{bp.versao_atual}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── MODAL: REGISTRO DE CONCEITO ── */}
        <AnimatePresence>
          {activeModal === 'register' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4"
            >
              <motion.div
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.95 }}
                className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl p-8 relative overflow-hidden shadow-2xl"
              >
                <button
                  onClick={() => setActiveModal(null)}
                  className="absolute top-6 right-6 p-2 bg-slate-950 border border-slate-850 hover:bg-slate-800 rounded-xl text-slate-400 hover:text-slate-200 transition-all"
                >
                  <X className="h-4 w-4" />
                </button>

                <h3 className="text-xl font-extrabold text-gradient flex items-center gap-2 mb-2">
                  <Plus className="h-5 w-5 text-cyan-400" />
                  Evoluir Conceito / Registrar Nova Versão
                </h3>
                <p className="text-xs text-slate-400 mb-6">Adicione uma regra de negócio ou mapeamento sem quebrar compatibilidade histórica.</p>

                {regSuccess ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center text-emerald-400">
                    <CheckCircle className="h-16 w-16 mb-4 animate-bounce" />
                    <span className="font-extrabold text-lg">Versão Registrada com Sucesso!</span>
                    <span className="text-xs text-slate-400 mt-2">Atualizando painel do Version Center...</span>
                  </div>
                ) : (
                  <form onSubmit={handleRegisterConcept} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">ID do Conceito</label>
                        <input
                          type="text"
                          placeholder="Ex: MET_001"
                          value={regConceptId}
                          onChange={e => setRegConceptId(e.target.value)}
                          required
                          className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Tipo</label>
                        <select
                          value={regType}
                          onChange={e => setRegType(e.target.value)}
                          className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
                        >
                          <option value="METRIC">METRIC (Métrica)</option>
                          <option value="DIMENSION">DIMENSION (Dimensão)</option>
                          <option value="PERIOD">PERIOD (Período)</option>
                          <option value="BLUEPRINT">BLUEPRINT (Plano estruturado)</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Semantic Version</label>
                        <input
                          type="text"
                          placeholder="Ex: 2.0"
                          value={regSemantic}
                          onChange={e => setRegSemantic(e.target.value)}
                          required
                          className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Mapping Version (Físico)</label>
                        <input
                          type="text"
                          placeholder="Ex: 2"
                          value={regMapping}
                          onChange={e => setRegMapping(e.target.value)}
                          required
                          className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Definition Snapshot (JSON)</label>
                      <textarea
                        rows={4}
                        value={regSnapshot}
                        onChange={e => setRegSnapshot(e.target.value)}
                        required
                        className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Motivo da Alteração</label>
                        <input
                          type="text"
                          placeholder="Ex: Nova regra fiscal corporativa"
                          value={regReason}
                          onChange={e => setRegReason(e.target.value)}
                          className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Impacto Previsto</label>
                        <input
                          type="text"
                          placeholder="Ex: Alteração de colunas em faturamento"
                          value={regImpact}
                          onChange={e => setRegImpact(e.target.value)}
                          className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      className="w-full py-3 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white rounded-xl text-xs font-extrabold shadow-lg shadow-cyan-500/20 transition-all duration-300"
                    >
                      Publicar Versão no SVR
                    </button>
                  </form>
                )}
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}
