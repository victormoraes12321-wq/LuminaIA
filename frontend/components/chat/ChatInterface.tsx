'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  AlertCircle,
  Zap,
  BrainCircuit,
  ChartNoAxesColumn,
  Table2,
  BarChart3,
  Check,
  X,
  SlidersHorizontal,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type {
  ChatMessage,
  DashboardDefaults,
  DashboardFormat,
  DashboardValueBasis,
  QueryMode,
  QueryResponse,
} from '@/types/lumina'

// ── ChatInterface ─────────────────────────────────────────────

interface ChatInterfaceProps {
  messages: ChatMessage[]
  loading: boolean
  error: string | null
  injectedQuery: string
  onSend: (pergunta: string) => void
  onClearError: () => void
  onSelectResponse?: (response: QueryResponse) => void
  mode: QueryMode
  onChangeMode: (mode: QueryMode) => void
  dashboardDefaults?: DashboardDefaults | null
  onSaveDashboardDefaults?: (defaults: DashboardDefaults) => void | Promise<void>
}

const DASHBOARD_DEFAULTS_KEY = 'lumina_dashboard_answer_defaults'

const MODE_OPTIONS: Array<{ id: QueryMode; icon: LucideIcon; label: string; desc: string }> = [
  { id: 'operational', icon: Zap, label: 'Operacional', desc: 'Respostas rápidas para consultas do dia a dia.' },
  { id: 'analytical', icon: ChartNoAxesColumn, label: 'Analítico (Padrão)', desc: 'Equilíbrio entre velocidade, contexto e inteligência.' },
  { id: 'executive', icon: BrainCircuit, label: 'Consultor Executivo', desc: 'Diagnóstico executivo completo com correlações, riscos, oportunidades e análise estratégica.' },
]

const VALUE_OPTIONS: Array<{ id: DashboardValueBasis; label: string }> = [
  { id: 'liquido', label: 'Líquido' },
  { id: 'bruto', label: 'Bruto' },
  { id: 'ambos', label: 'Os dois' },
]

const FORMAT_OPTIONS: Array<{ id: DashboardFormat; label: string; icon: LucideIcon }> = [
  { id: 'tabela', label: 'Tabela', icon: Table2 },
  { id: 'grafico', label: 'Gráfico', icon: BarChart3 },
  { id: 'ambos', label: 'Ambos', icon: SlidersHorizontal },
]

const QUICK_QUERY_OPTIONS = [
  'Faturamento do mês',
  'Ranking de vendedores',
  'Vendas RB por vendedor',
  'Desconto médio',
  'Top clientes',
  'Produtos mais vendidos',
  'Estoque por produto',
  'Financeiro em aberto',
]

function normalizeQuestion(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

function loadDashboardDefaults(): DashboardDefaults | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(DASHBOARD_DEFAULTS_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<DashboardDefaults>
    if (!parsed.basis || !parsed.format) return null
    return {
      basis: parsed.basis,
      format: parsed.format,
      instructions: parsed.instructions || '',
    }
  } catch {
    return null
  }
}

function saveDashboardDefaults(defaults: DashboardDefaults) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(DASHBOARD_DEFAULTS_KEY, JSON.stringify(defaults))
}

function asksForDashboardSelection(question: string): boolean {
  const normalized = normalizeQuestion(question)
  return [
    'selecionar a forma',
    'selecionar forma',
    'escolher a forma',
    'escolher formato',
    'como dashboard',
    'tipo de dashboard',
    'montar dashboard',
  ].some(term => normalized.includes(term))
}

function needsDashboardOptions(question: string): boolean {
  const normalized = normalizeQuestion(question)
  const analyticalIntent = [
    'analise',
    'analisar',
    'dashboard',
    'relatorio',
    'indicador',
    'kpi',
    'total',
    'quantidade',
    'media',
    'faturamento',
    'receita',
    'venda',
    'vendas',
    'venda total',
    'vendas totais',
    'ranking',
    'top',
    'vendedor',
    'cliente',
    'produto',
    'produtos',
    'estoque',
    'pedido',
    'pedidos',
    'compra',
    'compras',
    'fornecedor',
    'fornecedores',
    'financeiro',
    'boleto',
    'pagamento',
    'receber',
    'pagar',
    'inadimplencia',
    'inadimplência',
    'meta',
    'metas',
    'custo',
    'comissao',
    'comissão',
    'filial',
    'loja',
    'regiao',
    'região',
    'cidade',
    'estado',
    'curva abc',
    'ticket',
    'desconto',
    'rb',
    'devolucao',
    'lucro',
  ].some(term => normalized.includes(term))
  if (!analyticalIntent) return false

  const hasValueBasis = ['liquido', 'liquida', 'bruto', 'bruta', 'ambos', 'os dois', 'comercial'].some(term => normalized.includes(term))
  const hasFormat = ['tabela', 'planilha', 'grafico', 'grafica', 'barras', 'pizza', 'linha', 'dashboard'].some(term => normalized.includes(term))
  const requiresValueBasis = ['faturamento', 'receita', 'venda total', 'vendas totais', 'lucro', 'margem'].some(term => normalized.includes(term))
  return !hasFormat || (requiresValueBasis && !hasValueBasis)
}

function inferDashboardDefaults(question: string, saved: DashboardDefaults | null): DashboardDefaults {
  const normalized = normalizeQuestion(question)
  let basis = saved?.basis || 'liquido'
  let format = saved?.format || 'tabela'

  if (['liquido e bruto', 'bruto e liquido', 'ambos', 'os dois'].some(term => normalized.includes(term))) {
    basis = 'ambos'
  } else if (['bruto', 'bruta'].some(term => normalized.includes(term))) {
    basis = 'bruto'
  } else if (['liquido', 'liquida', 'comercial'].some(term => normalized.includes(term))) {
    basis = 'liquido'
  }

  if (['tabela e grafico', 'grafico e tabela', 'planilha e grafico', 'ambos', 'os dois'].some(term => normalized.includes(term))) {
    format = 'ambos'
  } else if (['grafico', 'grafica', 'barras', 'pizza', 'linha'].some(term => normalized.includes(term))) {
    format = 'grafico'
  } else if (['tabela', 'planilha'].some(term => normalized.includes(term))) {
    format = 'tabela'
  }

  return {
    basis,
    format,
    instructions: saved?.instructions || '',
  }
}

function questionWithDashboardDefaults(question: string, defaults: DashboardDefaults): string {
  const valueText =
    defaults.basis === 'ambos'
      ? 'líquido e bruto'
      : defaults.basis === 'bruto'
        ? 'bruto'
        : 'líquido'
  const formatText =
    defaults.format === 'ambos'
      ? 'tabela e gráfico'
      : defaults.format === 'grafico'
        ? 'gráfico'
        : 'tabela'
  const instructions = defaults.instructions.trim()
  return [
    question,
    `Preferências da resposta: base de valor ${valueText}; visualização em ${formatText}.`,
    instructions ? `Instruções adicionais: ${instructions}` : '',
  ].filter(Boolean).join(' ')
}

export function ChatInterface({
  loading,
  error,
  injectedQuery,
  onSend,
  onClearError,
  mode,
  onChangeMode,
  dashboardDefaults,
  onSaveDashboardDefaults,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('')
  const inputRef           = useRef<HTMLTextAreaElement>(null)
  
  const [showModeMenu, setShowModeMenu] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const [pendingDashboardQuestion, setPendingDashboardQuestion] = useState<string | null>(null)
  const [dashboardBasis, setDashboardBasis] = useState<DashboardValueBasis>('liquido')
  const [dashboardFormat, setDashboardFormat] = useState<DashboardFormat>('tabela')
  const [dashboardInstructions, setDashboardInstructions] = useState('')

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowModeMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Validação client-side do comprimento e conteúdo da pergunta
  const trimmedInput = input.trim()
  const isInvalid = trimmedInput.length < 3 || trimmedInput.length > 1000

  // Consume injected query from sidebar clicks
  useEffect(() => {
    if (injectedQuery) {
      queueMicrotask(() => {
        setInput(injectedQuery)
        inputRef.current?.focus()
      })
    }
  }, [injectedQuery])

  const handleSubmit = () => {
    if (isInvalid || loading) return
    const forceSelection = asksForDashboardSelection(trimmedInput)
    if (forceSelection || needsDashboardOptions(trimmedInput)) {
      const saved = dashboardDefaults ?? loadDashboardDefaults()
      const inferred = inferDashboardDefaults(trimmedInput, saved)
      if (saved && !forceSelection) {
        onSend(questionWithDashboardDefaults(trimmedInput, inferred))
        setInput('')
        onClearError()
        return
      }
      setDashboardBasis(inferred.basis)
      setDashboardFormat(inferred.format)
      setDashboardInstructions(inferred.instructions)
      setPendingDashboardQuestion(trimmedInput)
      return
    }
    onSend(trimmedInput)
    setInput('')
    onClearError()
  }

  const confirmDashboardOptions = () => {
    if (!pendingDashboardQuestion || loading) return
    const defaults = {
      basis: dashboardBasis,
      format: dashboardFormat,
      instructions: dashboardInstructions,
    }
    saveDashboardDefaults(defaults)
    void Promise.resolve(onSaveDashboardDefaults?.(defaults)).catch((err) => {
      console.warn('Falha ao salvar preferência de dashboard:', err)
    })
    onSend(questionWithDashboardDefaults(pendingDashboardQuestion, defaults))
    setInput('')
    setPendingDashboardQuestion(null)
    onClearError()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-resize textarea
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`
  }

  return (
    <div className="flex flex-col w-full">
      <AnimatePresence>
        {pendingDashboardQuestion && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 sm:items-center"
          >
            <motion.div
              initial={{ opacity: 0, y: 18, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 18, scale: 0.98 }}
              className="w-full max-w-lg rounded-lg border border-zinc-800 bg-zinc-950 p-4 shadow-2xl"
              style={{ background: 'rgb(var(--bg-elevated))', borderColor: 'rgb(var(--border))' }}
            >
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">Configurar resposta</p>
                  <p className="mt-1 text-xs leading-relaxed text-zinc-400 line-clamp-2">{pendingDashboardQuestion}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setPendingDashboardQuestion(null)}
                  className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-400 transition hover:bg-zinc-800 hover:text-white"
                  aria-label="Fechar configuração"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Base do valor</p>
                  <div className="grid grid-cols-3 gap-2">
                    {VALUE_OPTIONS.map(option => (
                      <button
                        type="button"
                        key={option.id}
                        onClick={() => setDashboardBasis(option.id)}
                        className={cn(
                          'flex h-10 items-center justify-center rounded-md border px-2 text-xs font-semibold transition',
                          dashboardBasis === option.id
                            ? 'border-lumina-500/60 bg-lumina-500/15 text-white'
                            : 'border-zinc-800 text-zinc-300 hover:border-zinc-700 hover:bg-zinc-900',
                        )}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Formato</p>
                  <div className="grid grid-cols-3 gap-2">
                    {FORMAT_OPTIONS.map(option => {
                      const Icon = option.icon
                      return (
                        <button
                          type="button"
                          key={option.id}
                          onClick={() => setDashboardFormat(option.id)}
                          className={cn(
                            'flex h-10 items-center justify-center gap-2 rounded-md border px-2 text-xs font-semibold transition',
                            dashboardFormat === option.id
                              ? 'border-lumina-500/60 bg-lumina-500/15 text-white'
                              : 'border-zinc-800 text-zinc-300 hover:border-zinc-700 hover:bg-zinc-900',
                          )}
                        >
                          <Icon size={14} />
                          {option.label}
                        </button>
                      )
                    })}
                  </div>
                </div>

                <label className="block">
                  <span className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                    Instruções opcionais
                  </span>
                  <textarea
                    value={dashboardInstructions}
                    onChange={event => setDashboardInstructions(event.target.value)}
                    rows={3}
                    maxLength={400}
                    className="w-full resize-none rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-lumina-500/70"
                    placeholder="Ex.: destacar filial 3, ocultar descontos, trazer top 10"
                  />
                </label>
              </div>

              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setPendingDashboardQuestion(null)}
                  className="h-9 rounded-md border border-zinc-800 px-3 text-xs font-semibold text-zinc-300 transition hover:bg-zinc-900 hover:text-white"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={confirmDashboardOptions}
                  className="flex h-9 items-center gap-2 rounded-md bg-lumina-500 px-3 text-xs font-semibold text-white transition hover:bg-lumina-400"
                >
                  <Check size={14} />
                  Aplicar
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
      {/* Input area */}
      <div className="flex-shrink-0 p-4">
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 mb-2 px-3 py-2 rounded-xl"
            style={{
              background: 'rgb(255 107 107 / 0.08)',
              border: '1px solid rgb(255 107 107 / 0.2)',
            }}
          >
            <AlertCircle size={13} className="text-red-400 flex-shrink-0" />
            <p className="text-xs text-red-400 flex-1 leading-snug">{error}</p>
          </motion.div>
        )}

        <div
          className="flex items-end gap-2 rounded-2xl p-2 px-3 lumina-glow-focus max-w-3xl mx-auto w-full"
          style={{
            background: 'rgb(var(--bg-elevated))',
            border: '1px solid rgb(var(--border) / 0.7)',
          }}
        >
          {/* Mode Selector Dropdown */}
          <div className="relative flex-shrink-0" ref={menuRef}>
            <motion.button
              whileHover={!loading ? { scale: 1.08 } : undefined}
              whileTap={!loading ? { scale: 0.92 } : undefined}
              disabled={loading}
              onClick={() => setShowModeMenu(!showModeMenu)}
              className={cn(
                'w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200 cursor-pointer text-zinc-400 hover:text-white',
                'hover:bg-zinc-800/60 disabled:opacity-50 disabled:cursor-not-allowed select-none mb-0.5'
              )}
              title="Mudar profundidade de análise da IA"
            >
              {(() => {
                const ActiveIcon = MODE_OPTIONS.find(option => option.id === mode)?.icon || ChartNoAxesColumn
                return <ActiveIcon size={15} />
              })()}
            </motion.button>

            <AnimatePresence>
              {showModeMenu && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  className="absolute bottom-11 left-0 w-80 rounded-2xl border border-zinc-800 bg-zinc-950 p-2 shadow-xl z-30"
                  style={{ background: 'rgb(var(--bg-elevated))', borderColor: 'rgb(var(--border))' }}
                >
                  <p className="text-[10px] font-bold text-lumina-400 uppercase tracking-widest px-3 py-1.5 border-b border-zinc-800/40 mb-1 select-none">
                    Modo de Resposta da IA
                  </p>
                  
                  {MODE_OPTIONS.map((opt) => {
                    const Icon = opt.icon
                    return (
                      <button
                        key={opt.id}
                        onClick={() => {
                          onChangeMode(opt.id)
                          setShowModeMenu(false)
                        }}
                        className={cn(
                          "w-full text-left flex items-start gap-2.5 p-2 px-3 rounded-xl transition-all cursor-pointer",
                          mode === opt.id
                            ? "bg-lumina-500/10 border border-lumina-500/20"
                            : "hover:bg-zinc-800/40 border border-transparent"
                        )}
                      >
                        <Icon size={16} className="mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className={cn("text-xs font-semibold", mode === opt.id ? "text-lumina-400" : "text-white")}>
                            {opt.label}
                          </p>
                          <p className="text-[10px] text-zinc-400 leading-normal mt-0.5 whitespace-normal">
                            {opt.desc}
                          </p>
                        </div>
                      </button>
                    )
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <textarea
            ref={inputRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Faça uma pergunta sobre seus dados..."
            rows={1}
            disabled={loading}
            className={cn(
              'flex-1 bg-transparent text-sm resize-none outline-none leading-relaxed',
              'placeholder:text-[rgb(var(--text-muted))] py-1 px-1',
              'disabled:opacity-50 disabled:cursor-not-allowed',
            )}
            style={{
              color: 'rgb(var(--text-primary))',
              minHeight: 32,
              maxHeight: 120,
            }}
          />

          {/* Send button */}
          <motion.button
            onClick={handleSubmit}
            disabled={isInvalid || loading}
            whileHover={!isInvalid && !loading ? { scale: 1.08 } : undefined}
            whileTap={!isInvalid && !loading ? { scale: 0.92 } : undefined}
            className={cn(
              'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-200 cursor-pointer',
              !isInvalid && !loading
                ? 'bg-lumina-gradient shadow-lumina text-white'
                : 'text-[rgb(var(--text-muted))] bg-zinc-800/40 opacity-40 cursor-not-allowed',
            )}
            style={
              isInvalid || loading
                ? { background: 'rgb(var(--bg-hover))' }
                : undefined
            }
            aria-label="Enviar pergunta"
          >
            {loading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                className="w-4 h-4 rounded-full border-2 border-t-transparent border-lumina-400"
              />
            ) : (
              <Send size={14} />
            )}
          </motion.button>
        </div>

        {trimmedInput.length === 0 && !loading && (
          <div className="mx-auto mt-2 flex max-w-3xl flex-wrap justify-center gap-2">
            {QUICK_QUERY_OPTIONS.map(option => (
              <button
                type="button"
                key={option}
                onClick={() => {
                  setInput(option)
                  queueMicrotask(() => inputRef.current?.focus())
                }}
                className="rounded-md border border-zinc-800 bg-zinc-950/60 px-2.5 py-1.5 text-[11px] font-medium text-zinc-300 transition hover:border-lumina-500/50 hover:text-white"
              >
                {option}
              </button>
            ))}
          </div>
        )}

        <p className="text-xs text-center mt-2" style={{ color: 'rgb(var(--text-muted))' }}>
          Enter para enviar · Shift+Enter para nova linha
        </p>
      </div>
    </div>
  )
}
