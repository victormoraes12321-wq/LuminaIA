'use client'

/**
 * LuminaAI — Painel de Dicionário de Views (Catálogo)
 * --------------------------------------------------
 * Página para gerenciamento das views Oracle catalogadas no tenant.
 * Permite cadastrar, atualizar e remover views, incluindo a especificação
 * detalhada dos parâmetros que a IA pode preencher dinamicamente.
 * 
 * Regra de Segurança (RBAC):
 * - Acesso restrito a usuários com papel 'ADMIN' ou 'GESTOR'.
 * - Caso um usuário sem permissão acesse, exibe uma tela elegante de Acesso Negado.
 */

import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  Trash2,
  Edit2,
  Table2,
  ShieldAlert,
  ArrowLeft,
  Loader2,
  AlertCircle,
  FolderOpen,
  Info,
  Layers,
  X,
  Search
} from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '@/context/AuthContext'
import { Badge } from '@/components/ui/Badge'
import { GlassCard } from '@/components/ui/GlassCard'
import { cn, getApiBase } from '@/lib/utils'
import type { ChartType } from '@/types/lumina'
import { TooltipHelp } from '@/components/ui/TooltipHelp'
import { Sidebar } from '@/components/Sidebar'

// Interface que define a estrutura de um parâmetro no formulário
const PARAMETER_TYPES = ['string', 'number', 'date', 'boolean'] as const
type ParameterType = typeof PARAMETER_TYPES[number]

function isParameterType(value: string): value is ParameterType {
  return PARAMETER_TYPES.includes(value as ParameterType)
}

interface FormParameter {
  key: string
  type: ParameterType
  required: boolean
  description: string
  example: string
}

type ParameterSchema = Record<string, {
  type: ParameterType
  required: boolean
  description: string
  example: string
}>

// Interface que espelha ViewCatalogResponse do backend
interface CatalogViewItem {
  id: string
  nome_view_oracle: string
  descricao_para_ia: string
  tipo_grafico_padrao: ChartType
  parametros_schema: ParameterSchema
  ativo: boolean
  criado_em: string
  atualizado_em: string
}

export default function AdminCatalogPage() {
  const { user, token } = useAuth()
  
  // Estado de dados
  const [views, setViews] = useState<CatalogViewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Estado do formulário de criação/edição
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const [editingViewId, setEditingViewId] = useState<string | null>(null)
  
  // Campos do formulário
  const [oracleName, setOracleName] = useState('')
  const [descriptionIA, setDescriptionIA] = useState('')
  const [defaultChart, setDefaultChart] = useState<ChartType>('BAR')
  const [parameters, setParameters] = useState<FormParameter[]>([])
  
  // Controle de submissão e carregamento secundário
  const [submitting, setSubmitting] = useState(false)
  const [deletingViewId, setDeletingViewId] = useState<string | null>(null)

  const API_BASE = getApiBase()
  const canManageCatalog = user?.role === 'ADMIN' || user?.role === 'GESTOR'

  // Busca views catalogadas no banco PostgreSQL do tenant
  const fetchViews = useCallback(async () => {
    if (!token || !canManageCatalog) return
    try {
      setLoading(true)
      setError(null)
      const res = await fetch(`${API_BASE}/api/v1/catalog/`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao buscar catálogo de views.')
      }
      const data = await res.json()
      setViews(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro na requisição das views.')
    } finally {
      setLoading(false)
    }
  }, [API_BASE, canManageCatalog, token])

  useEffect(() => {
    if (user && !canManageCatalog) {
      queueMicrotask(() => setLoading(false))
    } else if (token && canManageCatalog) {
      void Promise.resolve().then(fetchViews)
    }
  }, [canManageCatalog, fetchViews, token, user])

  // Abre formulário para criação
  const handleOpenCreate = () => {
    setEditingViewId(null)
    setOracleName('')
    setDescriptionIA('')
    setDefaultChart('BAR')
    setParameters([])
    setError(null)
    setIsPanelOpen(true)
  }

  // Abre formulário para edição de view existente
  const handleOpenEdit = (v: CatalogViewItem) => {
    setEditingViewId(v.id)
    setOracleName(v.nome_view_oracle)
    setDescriptionIA(v.descricao_para_ia)
    setDefaultChart(v.tipo_grafico_padrao)
    
    // Converte parametros_schema de objeto/dict para array do formulário
    const formParams: FormParameter[] = Object.entries(v.parametros_schema || {}).map(([key, details]) => ({
      key,
      type: isParameterType(details.type) ? details.type : 'string',
      required: !!details.required,
      description: details.description || '',
      example: String(details.example || '')
    }))
    setParameters(formParams)
    setError(null)
    setIsPanelOpen(true)
  }

  // Adiciona linha de parâmetro vazia no formulário
  const handleAddParameter = () => {
    setParameters(prev => [
      ...prev,
      { key: '', type: 'string', required: false, description: '', example: '' }
    ])
  }

  // Remove linha de parâmetro no formulário
  const handleRemoveParameter = (index: number) => {
    setParameters(prev => prev.filter((_, i) => i !== index))
  }

  // Atualiza um campo de parâmetro específico no formulário
  const handleParamChange = <K extends keyof FormParameter>(index: number, field: K, value: FormParameter[K]) => {
    setParameters(prev =>
      prev.map((param, i) => (i === index ? { ...param, [field]: value } : param))
    )
  }

  // Envia criação ou edição para o backend
  const handleSubmitView = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!oracleName.trim()) return
    if (descriptionIA.length < 20) {
      setError('A descrição para a IA precisa ter no mínimo 20 caracteres para garantir um bom matching.')
      return
    }

    // Valida se há chaves duplicadas ou vazias nos parâmetros
    const paramKeys = parameters.map(p => p.key.trim().toUpperCase())
    if (paramKeys.some(k => !k)) {
      setError('Todos os parâmetros informados precisam ter um nome (chave).')
      return
    }
    if (new Set(paramKeys).size !== paramKeys.length) {
      setError('Não é permitido nomes de parâmetros duplicados.')
      return
    }

    // Reconverte array do formulário de volta para o dict esperado pelo backend
    const parametros_schema: ParameterSchema = {}
    parameters.forEach(p => {
      parametros_schema[p.key.trim().toUpperCase()] = {
        type: p.type,
        required: p.required,
        description: p.description.trim(),
        example: p.example.trim()
      }
    })

    try {
      setSubmitting(true)
      setError(null)
      
      const payload = {
        nome_view_oracle: oracleName.trim().toUpperCase(),
        descricao_para_ia: descriptionIA.trim(),
        tipo_grafico_padrao: defaultChart,
        parametros_schema
      }

      const url = editingViewId 
        ? `${API_BASE}/api/v1/catalog/${editingViewId}`
        : `${API_BASE}/api/v1/catalog/`
      
      const method = editingViewId ? 'PUT' : 'POST'

      const res = await fetch(url, {
        method,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao salvar alteração da view.')
      }

      const savedView = await res.json()
      
      if (editingViewId) {
        setViews(prev => prev.map(v => (v.id === savedView.id ? savedView : v)))
      } else {
        setViews(prev => [...prev, savedView])
      }

      setIsPanelOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao persistir catálogo.')
    } finally {
      setSubmitting(false)
    }
  }

  // Alterna ativação (ativo = true/false)
  const handleToggleActive = async (view: CatalogViewItem) => {
    try {
      setError(null)
      const res = await fetch(`${API_BASE}/api/v1/catalog/${view.id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ativo: !view.ativo
        })
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao alterar status da view.')
      }
      const updatedView = await res.json()
      setViews(prev => prev.map(v => (v.id === updatedView.id ? updatedView : v)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao alterar status.')
    }
  }

  // Deleta view do catálogo
  const handleDeleteView = async (targetId: string) => {
    try {
      setError(null)
      const res = await fetch(`${API_BASE}/api/v1/catalog/${targetId}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao deletar view.')
      }
      setViews(prev => prev.filter(v => v.id !== targetId))
      setDeletingViewId(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao deletar.')
    }
  }

  // ── Proteção RBAC / Acesso Negado ──────────────────────────────
  if (!loading && user?.role !== 'ADMIN' && user?.role !== 'GESTOR') {
    return (
      <div className="flex h-dvh w-screen items-center justify-center p-6" style={{ background: 'rgb(var(--bg-base))' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md w-full text-center"
        >
          <GlassCard padding="lg" className="flex flex-col items-center gap-6 border-red-500/25">
            <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center text-red-500">
              <ShieldAlert size={36} />
            </div>
            <div>
              <h2 className="text-xl font-bold mb-2" style={{ color: 'rgb(var(--text-primary))' }}>
                Acesso Restrito
              </h2>
              <p className="text-sm leading-relaxed" style={{ color: 'rgb(var(--text-secondary))' }}>
                Desculpe, a área de dicionário de catálogo é restrita para administradores e gestores de dados do LuminaAI.
              </p>
            </div>
            <Link href="/dashboard" className="w-full">
              <button
                className="w-full flex items-center justify-center gap-2 text-xs font-semibold py-3 px-4 rounded-xl transition-all interactive hover:bg-zinc-800"
                style={{
                  background: 'rgb(var(--bg-elevated))',
                  border: '1px solid rgb(var(--border) / 0.6)',
                  color: 'rgb(var(--text-secondary))',
                }}
              >
                <ArrowLeft size={14} />
                <span>Voltar ao Dashboard</span>
              </button>
            </Link>
          </GlassCard>
        </motion.div>
      </div>
    )
  }

  // Filtragem local das views
  const filteredViews = views.filter(v =>
    v.nome_view_oracle.toLowerCase().includes(searchQuery.toLowerCase()) ||
    v.descricao_para_ia.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex h-dvh overflow-hidden" style={{ background: 'rgb(var(--bg-base))' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0 dashboard-main-content">
        
        {/* Top Header */}
        <header
          className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 px-8 py-6 flex-shrink-0"
          style={{ borderBottom: '1px solid rgb(var(--border) / 0.5)' }}
        >
          <div>
            <h1 className="text-xl font-bold text-gradient">
              Dicionário de Views (Catálogo)
            </h1>
            <p className="text-xs mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
              Mapeie views físicas do Oracle Database e ensine à Inteligência Artificial como acessá-las com filtros adequados.
            </p>
          </div>
          
          <button
            onClick={handleOpenCreate}
            className="flex items-center justify-center gap-2 text-xs font-semibold px-4 py-2.5 rounded-xl bg-lumina-gradient text-white shadow-lumina-lg transition-all hover:scale-102 interactive"
          >
            <Plus size={14} />
            <span>Cadastrar Nova View</span>
          </button>
        </header>

        {/* Corpo Principal da Tela */}
        <main className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
          
          {/* Exibição de Erro Global */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-xl border border-red-500/20 bg-red-500/10 flex items-start gap-3"
            >
              <AlertCircle className="text-red-400 mt-0.5 flex-shrink-0" size={16} />
              <div>
                <p className="text-xs font-semibold text-red-400">Mensagem do Sistema</p>
                <p className="text-xs leading-normal mt-0.5" style={{ color: 'rgb(var(--text-secondary))' }}>
                  {error}
                </p>
              </div>
            </motion.div>
          )}

          {/* Filtro e Busca */}
          <div className="flex items-center gap-3 w-full max-w-md">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500" size={15} />
              <input
                type="text"
                placeholder="Filtrar views por nome ou contexto semântico..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-xs lumina-input"
              />
            </div>
          </div>

          {/* Listagem em Grid */}
          {loading ? (
            <div className="flex items-center justify-center h-64 gap-3">
              <Loader2 className="text-lumina-400 animate-spin" size={24} />
              <span className="text-xs" style={{ color: 'rgb(var(--text-muted))' }}>Sincronizando dicionário de dados...</span>
            </div>
          ) : filteredViews.length === 0 ? (
            <GlassCard className="flex flex-col items-center justify-center py-16 text-center border-dashed border-zinc-300 dark:border-zinc-700/50">
              <FolderOpen size={36} className="text-zinc-400 dark:text-zinc-600 mb-3" />
              <h3 className="text-sm font-semibold mb-1" style={{ color: 'rgb(var(--text-primary))' }}>
                Nenhuma view cadastrada
              </h3>
              <p className="text-xs leading-relaxed max-w-xs" style={{ color: 'rgb(var(--text-muted))' }}>
                {searchQuery ? 'Tente buscar por outro termo.' : 'Adicione sua primeira view Oracle para expor a IA e iniciar as consultas.'}
              </p>
            </GlassCard>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              {filteredViews.map(v => {
                const paramCount = Object.keys(v.parametros_schema || {}).length
                return (
                  <GlassCard
                    key={v.id}
                    padding="md"
                    className={cn(
                      'flex flex-col justify-between gap-5 transition-all border-zinc-200 dark:border-zinc-800/40',
                      !v.ativo && 'opacity-65 grayscale-[30%]'
                    )}
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Table2 size={14} className="text-lumina-400" />
                          <h3 className="text-sm font-extrabold font-mono tracking-tight text-zinc-900 dark:text-white uppercase truncate">
                            {v.nome_view_oracle}
                          </h3>
                        </div>
                        <p className="text-xs line-clamp-2 mt-2 leading-relaxed" style={{ color: 'rgb(var(--text-secondary))' }}>
                          {v.descricao_para_ia}
                        </p>
                      </div>
                      
                      <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                        <Badge variant={v.ativo ? 'success' : 'neutral'} size="xs">
                          {v.ativo ? 'Sincronizada' : 'Inativa'}
                        </Badge>
                        <Badge variant="lumina" size="xs">
                          {v.tipo_grafico_padrao}
                        </Badge>
                      </div>
                    </div>

                    {/* Conteúdo Parâmetros */}
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="text-[10px] font-semibold uppercase tracking-wide text-zinc-650 dark:text-zinc-500 mr-1.5">
                        Filtros Suportados ({paramCount}):
                      </span>
                      {paramCount === 0 ? (
                        <span className="text-[10px] italic text-zinc-600">Sem parâmetros dinâmicos (estática)</span>
                      ) : (
                        Object.keys(v.parametros_schema).map(key => (
                          <span
                            key={key}
                            className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800/60 border border-zinc-300 dark:border-zinc-700/50 text-zinc-700 dark:text-zinc-300"
                          >
                            {key}
                          </span>
                        ))
                      )}
                    </div>

                    {/* Ações */}
                    <div className="flex items-center justify-between border-t border-zinc-200 dark:border-zinc-800/50 pt-3.5">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleToggleActive(v)}
                          className={cn(
                            'text-[11px] font-semibold px-3 py-1.5 rounded-lg border transition-colors',
                            v.ativo
                              ? 'text-zinc-600 dark:text-zinc-400 border-zinc-300 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                              : 'text-emerald-500 dark:text-emerald-400 border-zinc-300 dark:border-zinc-800 hover:bg-emerald-500/10'
                          )}
                        >
                          {v.ativo ? 'Desativar matching' : 'Ativar matching'}
                        </button>
                        <button
                          onClick={() => handleOpenEdit(v)}
                          className="flex items-center gap-1 text-[11px] font-semibold px-3 py-1.5 rounded-lg border border-zinc-300 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                        >
                          <Edit2 size={10} />
                          <span>Editar</span>
                        </button>
                      </div>

                      <button
                        onClick={() => setDeletingViewId(v.id)}
                        className="flex items-center justify-center w-8 h-8 rounded-lg border border-zinc-300 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                        title="Deletar view do catálogo"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </GlassCard>
                )
              })}
            </div>
          )}
        </main>
      </div>

      {/* ── MODAL / SLIDE-PANEL: CADASTRO E EDIÇÃO DE VIEW ───────────────── */}
      <AnimatePresence>
        {isPanelOpen && (
          <div className="fixed inset-0 z-50 flex justify-end">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsPanelOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 260 }}
              className="relative w-full max-w-2xl h-full bg-white dark:bg-zinc-955 border-l border-zinc-300 dark:border-zinc-800 shadow-2xl z-10 flex flex-col"
            >
              {/* Header do Painel */}
              <div className="flex items-center justify-between px-6 py-5 border-b border-zinc-200 dark:border-zinc-800">
                <div>
                  <h3 className="text-base font-bold text-zinc-900 dark:text-white">
                    {editingViewId ? 'Editar View do Catálogo' : 'Cadastrar Nova View'}
                  </h3>
                  <p className="text-[10px]" style={{ color: 'rgb(var(--text-muted))' }}>
                    Defina metadados semânticos para o motor de IA mapear e filtrar as queries.
                  </p>
                </div>
                <button
                  onClick={() => setIsPanelOpen(false)}
                  className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-zinc-100 dark:hover:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400"
                >
                  <X size={15} />
                </button>
              </div>

              {/* Corpo com Scroll do Painel */}
              <form onSubmit={handleSubmitView} className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
                
                {/* Alerta de erro do formulário */}
                {error && (
                  <div className="p-3.5 rounded-xl border border-red-500/20 bg-red-500/10 flex items-start gap-2.5">
                    <AlertCircle className="text-red-400 mt-0.5 flex-shrink-0" size={14} />
                    <span className="text-[11px] leading-normal text-red-400">{error}</span>
                  </div>
                )}

                {/* 1. Nome da View */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                    Nome Físico no Oracle
                    <TooltipHelp content="Nome exato da view física criada no seu banco de dados Oracle para leitura (ex: VW_FUNDO_FATOR)." />
                  </label>
                  <input
                    type="text"
                    required
                    disabled={!!editingViewId} // impede mudar o nome no update para evitar quebras
                    value={oracleName}
                    onChange={e => setOracleName(e.target.value.toUpperCase())}
                    placeholder="Ex: VW_FUNDO_FATOR"
                    className="py-2.5 px-3.5 text-xs lumina-input uppercase font-mono disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <p className="text-[10px] text-zinc-500 dark:text-zinc-400 font-medium">
                    Nome exato da view de leitura criada no seu banco de dados Oracle.
                  </p>
                </div>

                {/* 2. Tipo de Gráfico Padrão */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                    Componente Visual Padrão
                    <TooltipHelp content="O componente visual (gráfico de barras, tabela, linhas, etc.) que o Lumina utilizará por padrão para renderizar o resultado desta consulta." />
                  </label>
                  <select
                    value={defaultChart}
                    onChange={e => setDefaultChart(e.target.value as ChartType)}
                    className="py-2.5 px-3.5 text-xs lumina-input"
                  >
                    <option value="BAR">📊 Gráfico de Barras (BAR)</option>
                    <option value="LINE">📈 Gráfico de Linhas (LINE)</option>
                    <option value="AREA">📉 Gráfico de Área (AREA)</option>
                    <option value="PIE">🍕 Gráfico de Pizza (PIE)</option>
                    <option value="KPI">🔢 Indicadores Numéricos (KPI)</option>
                    <option value="TABLE">📋 Tabela de Dados (TABLE)</option>
                    <option value="SCATTER">🔵 Gráfico de Dispersão (SCATTER)</option>
                  </select>
                </div>

                {/* 3. Descrição para a IA */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between items-center">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                      Descrição Semântica para IA
                      <TooltipHelp content="Descreva detalhadamente para que serve esta view, quais perguntas ela responde e quais termos são sinônimos. Isso ajuda o motor de NLP a selecionar a view correta." />
                    </label>
                    <span className={cn('text-[10px]', descriptionIA.length < 20 ? 'text-yellow-400 font-semibold' : 'text-zinc-600')}>
                      {descriptionIA.length}/20 min.
                    </span>
                  </div>
                  <textarea
                    required
                    rows={4}
                    value={descriptionIA}
                    onChange={e => setDescriptionIA(e.target.value)}
                    placeholder="Escreva aqui detalhadamente quais perguntas essa view responde, quais campos ela contém e quais termos são sinônimos. Ex: 'Análise de faturamento e volume total de vendas mensais de produtos corporativos...'"
                    className="py-2.5 px-3.5 text-xs lumina-input leading-relaxed resize-none"
                  />
                  <div className="p-3 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800/60 flex items-start gap-2">
                    <Info size={13} className="text-lumina-400 mt-0.5 flex-shrink-0" />
                    <p className="text-[10px] text-zinc-600 dark:text-zinc-400 leading-normal">
                      <strong>Dica de Prompting:</strong> A IA utiliza essa descrição para cruzar com a pergunta do usuário. Inclua métricas calculadas e sinônimos comuns (ex: faturamento = receita = vendas).
                    </p>
                  </div>
                </div>

                {/* 4. Parâmetros / Filtros Schema */}
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                      <Layers size={13} className="text-zinc-400" />
                      Parâmetros Aceitos ({parameters.length})
                    </span>
                    <button
                      type="button"
                      onClick={handleAddParameter}
                      className="flex items-center gap-1 text-[10px] font-bold py-1 px-2.5 rounded bg-zinc-100 dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 text-lumina-500 dark:text-lumina-400 hover:bg-zinc-200 dark:hover:bg-zinc-800"
                    >
                      <Plus size={10} />
                      <span>Adicionar Parâmetro</span>
                    </button>
                  </div>

                  {parameters.length === 0 ? (
                    <div className="py-8 text-center border border-dashed border-zinc-300 dark:border-zinc-800 rounded-xl">
                      <p className="text-[11px] italic text-zinc-500 dark:text-zinc-400">Sem filtros. A view será chamada sem cláusula WHERE parametrizada.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {parameters.map((param, index) => (
                        <div
                          key={index}
                          className="p-4 rounded-xl border border-zinc-250 dark:border-zinc-800/80 bg-zinc-100 dark:bg-zinc-900/30 flex flex-col gap-3 relative"
                        >
                          {/* Excluir Parâmetro */}
                          <button
                            type="button"
                            onClick={() => handleRemoveParameter(index)}
                            className="absolute top-3 right-3 text-zinc-550 dark:text-zinc-500 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                            title="Remover parâmetro"
                          >
                            <X size={14} />
                          </button>

                          {/* Inputs de chave e tipo */}
                          <div className="grid grid-cols-2 gap-3 pr-6">
                            <div className="flex flex-col gap-1">
                              <span className="text-[9px] font-bold uppercase text-zinc-600 flex items-center">
                                Nome do Parâmetro (Oracle Column)
                                <TooltipHelp content="Nome exato da coluna da view que receberá o filtro (ex: ANO, MES, UF)." />
                              </span>
                              <input
                                type="text"
                                required
                                value={param.key}
                                onChange={e => handleParamChange(index, 'key', e.target.value.toUpperCase())}
                                placeholder="Ex: ANO"
                                className="py-1.5 px-2.5 text-xs lumina-input uppercase font-mono"
                              />
                            </div>
                            <div className="flex flex-col gap-1">
                              <span className="text-[9px] font-bold uppercase text-zinc-600 flex items-center">
                                Tipo do Dado
                                <TooltipHelp content="Tipo de dado do parâmetro para conversão e binding corretos na query Oracle." />
                              </span>
                              <select
                                value={param.type}
                                onChange={e => handleParamChange(index, 'type', e.target.value as ParameterType)}
                                className="py-1.5 px-2.5 text-xs lumina-input"
                              >
                                <option value="string">Texto (string)</option>
                                <option value="number">Numérico (number)</option>
                                <option value="date">Data (date)</option>
                                <option value="boolean">Booleano (boolean)</option>
                              </select>
                            </div>
                          </div>

                          {/* Descrição e exemplo */}
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <div className="md:col-span-2 flex flex-col gap-1">
                              <span className="text-[9px] font-bold uppercase text-zinc-600 flex items-center">
                                Descrição do Filtro para IA
                                <TooltipHelp content="Explicação em linguagem natural ensinando à IA o que este filtro representa. Ex: 'O ano fiscal desejado para faturamento'." />
                              </span>
                              <input
                                type="text"
                                required
                                value={param.description}
                                onChange={e => handleParamChange(index, 'description', e.target.value)}
                                placeholder="O ano fiscal para filtragem (ex: 2026)"
                                className="py-1.5 px-2.5 text-xs lumina-input"
                              />
                            </div>
                            <div className="flex flex-col gap-1">
                              <span className="text-[9px] font-bold uppercase text-zinc-600 flex items-center">
                                Exemplo
                                <TooltipHelp content="Um exemplo de valor aceito por este parâmetro (ex: 2026, SP, 2026-06-15)." />
                              </span>
                              <input
                                type="text"
                                required
                                value={param.example}
                                onChange={e => handleParamChange(index, 'example', e.target.value)}
                                placeholder="Ex: 2026"
                                className="py-1.5 px-2.5 text-xs lumina-input"
                              />
                            </div>
                          </div>

                          {/* Obrigatório toggle */}
                          <div className="flex items-center gap-2 mt-1">
                            <input
                              type="checkbox"
                              id={`req-${index}`}
                              checked={param.required}
                              onChange={e => handleParamChange(index, 'required', e.target.checked)}
                              className="w-3.5 h-3.5 rounded border-zinc-350 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-900 accent-violet-500"
                            />
                            <label htmlFor={`req-${index}`} className="text-[10px] text-zinc-650 dark:text-zinc-400 font-semibold select-none cursor-pointer flex items-center">
                              Este filtro é obrigatório na query (Required)
                              <TooltipHelp content="Se marcado, a IA só ativará esta view se conseguir extrair este parâmetro com sucesso da pergunta do usuário." />
                            </label>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Botões do Rodapé do SlidePanel */}
                <div className="flex gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-850">
                  <button
                    type="button"
                    onClick={() => setIsPanelOpen(false)}
                    className="flex-1 py-2.5 rounded-xl border border-zinc-300 dark:border-zinc-800 text-xs font-semibold text-zinc-550 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
                  >
                    Descartar
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 py-2.5 rounded-xl bg-lumina-gradient text-white text-xs font-semibold shadow-lumina transition-all hover:scale-102 flex items-center justify-center gap-1.5 disabled:opacity-50"
                  >
                    {submitting ? (
                      <Loader2 className="animate-spin" size={14} />
                    ) : (
                      <span>Salvar e Sincronizar</span>
                    )}
                  </button>
                </div>

              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ── MODAL: CONFIRMAÇÃO DE DELEÇÃO DE VIEW ────────────────────── */}
      <AnimatePresence>
        {deletingViewId && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDeletingViewId(null)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-sm glass-strong rounded-2xl p-6 shadow-2xl z-10"
            >
              <div className="flex flex-col items-center text-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center text-red-400">
                  <ShieldAlert size={24} />
                </div>
                <div>
                  <h3 className="text-base font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
                    Deseja remover do dicionário?
                  </h3>
                  <p className="text-xs mt-2 leading-relaxed" style={{ color: 'rgb(var(--text-secondary))' }}>
                    Esta ação removerá a view do catálogo e a IA não poderá mais utilizá-la. Isso não altera as views físicas do banco Oracle.
                  </p>
                </div>
                <div className="flex gap-2 w-full mt-2">
                  <button
                    onClick={() => setDeletingViewId(null)}
                    className="flex-1 py-2 px-3 rounded-lg text-xs font-semibold border border-zinc-300 dark:border-zinc-800 transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    style={{ color: 'rgb(var(--text-secondary))' }}
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={() => deletingViewId && handleDeleteView(deletingViewId)}
                    className="flex-1 py-2 px-3 rounded-lg text-xs font-semibold bg-red-500 hover:bg-red-600 text-white transition-colors"
                  >
                    Remover
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

