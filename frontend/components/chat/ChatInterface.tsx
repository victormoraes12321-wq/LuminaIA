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
import {
  analyzeMissingSlots,
  buildClarifiedPrompt,
  type ClarificationRequirement,
} from '@/lib/clarification/slotAnalyzer'

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

const MODE_OPTIONS: Array<{ id: QueryMode; icon: LucideIcon; label: string; desc: string }> = [
  { id: 'operational', icon: Zap, label: 'Operacional', desc: 'Respostas rápidas para consultas do dia a dia.' },
  { id: 'analytical', icon: ChartNoAxesColumn, label: 'Analítico (Padrão)', desc: 'Equilíbrio entre velocidade, contexto e inteligência.' },
  { id: 'executive', icon: BrainCircuit, label: 'Consultor Executivo', desc: 'Diagnóstico executivo completo com correlações, riscos, oportunidades e análise estratégica.' },
]

export function ChatInterface({
  loading,
  injectedQuery,
  onSend,
  onClearError,
  mode,
  onChangeMode,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  
  const [showModeMenu, setShowModeMenu] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null)
  const [pendingRequirement, setPendingRequirement] = useState<ClarificationRequirement | null>(null)
  const [slotSelections, setSlotSelections] = useState<Record<string, string>>({})
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

    const requirement = analyzeMissingSlots(trimmedInput)
    if (requirement.required && requirement.slot_configs.length > 0) {
      const initialSelections: Record<string, string> = {}
      for (const config of requirement.slot_configs) {
        initialSelections[config.id] = config.default_id
      }
      setSlotSelections(initialSelections)
      setPendingRequirement(requirement)
      setPendingQuestion(trimmedInput)
      return
    }

    onSend(trimmedInput)
    setInput('')
    onClearError()
  }

  const confirmClarification = () => {
    if (!pendingQuestion || !pendingRequirement || loading) return

    const clarifiedPrompt = buildClarifiedPrompt(pendingQuestion, pendingRequirement, slotSelections)
    const finalQuery = dashboardInstructions.trim()
      ? `${clarifiedPrompt} Instruções adicionais: ${dashboardInstructions.trim()}`
      : clarifiedPrompt

    onSend(finalQuery)
    setInput('')
    setPendingQuestion(null)
    setPendingRequirement(null)
    setSlotSelections({})
    setDashboardInstructions('')
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
      {/* ── Clarification Modal Dinâmico por Missing Slot ── */}
      <AnimatePresence>
        {pendingQuestion && pendingRequirement && (
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
              data-testid="modal-clarification"
              className="w-full max-w-lg rounded-xl border border-zinc-800 bg-zinc-950 p-5 shadow-2xl"
              style={{ background: 'rgb(var(--bg-elevated))', borderColor: 'rgb(var(--border))' }}
            >
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">
                    {pendingRequirement.modal_title || 'Especificação de Consulta'}
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-zinc-400">
                    {pendingRequirement.modal_description || 'Identificamos slots ambíguos na sua pergunta:'}
                  </p>
                  <div className="mt-2 rounded-md bg-zinc-900/80 px-2.5 py-1.5 border border-zinc-800/80">
                    <p className="text-xs text-lumina-300 font-mono italic truncate">"{pendingQuestion}"</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setPendingQuestion(null)
                    setPendingRequirement(null)
                  }}
                  className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-400 transition hover:bg-zinc-800 hover:text-white"
                  aria-label="Fechar configuração"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
                {pendingRequirement.slot_configs.map((config, idx) => (
                  <div key={config.id} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                        {config.label}
                      </p>
                      <span className="text-[10px] text-zinc-500 font-mono">Slot {idx + 1}/{pendingRequirement.slot_configs.length}</span>
                    </div>

                    <div className={cn(
                      'grid gap-2',
                      config.options.length <= 3 ? 'grid-cols-3' : config.options.length <= 4 ? 'grid-cols-2' : 'grid-cols-3'
                    )}>
                      {config.options.map(option => {
                        const isSelected = (slotSelections[config.id] || config.default_id) === option.id
                        // Retém test-ids canônicos para compatibilidade total de automação
                        const testId =
                          config.id === 'ranking_metric' || config.id === 'filial'
                            ? `basis-option-${option.id}`
                            : config.id === 'ranking_limit' || config.id === 'comparison_baseline' || config.id === 'entity_scope'
                              ? `format-option-${option.id}`
                              : `option-${option.id}`

                        return (
                          <button
                            type="button"
                            key={option.id}
                            data-testid={testId}
                            onClick={() => {
                              setSlotSelections(prev => ({
                                ...prev,
                                [config.id]: option.id,
                              }))
                            }}
                            className={cn(
                              'flex flex-col items-center justify-center rounded-lg border p-2 text-center transition min-h-[44px]',
                              isSelected
                                ? 'border-lumina-500/60 bg-lumina-500/15 text-white shadow-sm'
                                : 'border-zinc-800 text-zinc-300 hover:border-zinc-700 hover:bg-zinc-900',
                            )}
                          >
                            <span className="text-xs font-semibold">{option.label}</span>
                            {option.description && (
                              <span className="mt-0.5 text-[10px] text-zinc-400 line-clamp-1 leading-tight">
                                {option.description}
                              </span>
                            )}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}

                <label className="block pt-1">
                  <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                    Instruções Adicionais (Opcional)
                  </span>
                  <textarea
                    value={dashboardInstructions}
                    onChange={event => setDashboardInstructions(event.target.value)}
                    rows={2}
                    maxLength={400}
                    className="w-full resize-none rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-xs text-white outline-none transition placeholder:text-zinc-600 focus:border-lumina-500/70"
                    placeholder="Ex.: em gráfico de barras, destacar filial 1, ordenar decrescente"
                  />
                </label>
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-zinc-800/80 pt-3">
                <span className="text-[11px] text-zinc-500">
                  {pendingRequirement.slot_configs.length} slot(s) resolvido(s)
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setPendingQuestion(null)
                      setPendingRequirement(null)
                    }}
                    className="h-9 rounded-lg border border-zinc-800 px-3 text-xs font-semibold text-zinc-300 transition hover:bg-zinc-900 hover:text-white"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    data-testid="confirm-clarification"
                    onClick={confirmClarification}
                    className="flex h-9 items-center gap-2 rounded-lg bg-lumina-500 px-4 text-xs font-semibold text-white transition hover:bg-lumina-400 shadow-md shadow-lumina-500/20"
                  >
                    <Check size={14} />
                    Confirmar e Consultar
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Input Container Principal ── */}
      <div 
        className="flex flex-col border border-zinc-800/80 rounded-2xl bg-zinc-900/40 backdrop-blur-md transition-all duration-200 focus-within:border-lumina-500/50 focus-within:ring-1 focus-within:ring-lumina-500/50 focus-within:bg-zinc-900/60 shadow-lg"
        style={{
          borderColor: 'rgb(var(--border))',
          background: 'rgb(var(--bg-elevated) / 0.6)'
        }}
      >
        {/* Textarea */}
        <div className="p-3">
          <textarea
            ref={inputRef}
            data-testid="chat-input"
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={loading}
            placeholder="Pergunte sobre vendas, faturamento, filiais, vendedores, produtos ou clientes..."
            rows={1}
            className="w-full bg-transparent resize-none border-0 p-0 text-sm text-zinc-100 placeholder-zinc-500 focus:ring-0 focus:outline-none max-h-32 min-h-[24px] leading-relaxed disabled:opacity-50"
          />
        </div>

        {/* Action Toolbar Bottom */}
        <div className="flex items-center justify-between px-3 pb-2.5 pt-1 border-t border-zinc-800/40">
          <div className="flex items-center gap-2">
            {/* Mode Switcher */}
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setShowModeMenu(!showModeMenu)}
                disabled={loading}
                className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 px-2 py-1 rounded-md hover:bg-zinc-800/60 transition-colors disabled:opacity-50"
              >
                {mode === 'operational' && <Zap size={13} className="text-amber-400" />}
                {mode === 'analytical' && <ChartNoAxesColumn size={13} className="text-lumina-400" />}
                {mode === 'executive' && <BrainCircuit size={13} className="text-purple-400" />}
                <span className="capitalize font-medium">{mode}</span>
              </button>

              {/* Mode Dropdown */}
              <AnimatePresence>
                {showModeMenu && (
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 5 }}
                    className="absolute left-0 bottom-full mb-2 w-64 rounded-xl border border-zinc-800 bg-zinc-950 p-1.5 shadow-2xl z-50"
                    style={{ background: 'rgb(var(--bg-elevated))', borderColor: 'rgb(var(--border))' }}
                  >
                    {MODE_OPTIONS.map((opt) => {
                      const Icon = opt.icon
                      const isSelected = mode === opt.id
                      return (
                        <button
                          key={opt.id}
                          onClick={() => {
                            onChangeMode(opt.id)
                            setShowModeMenu(false)
                          }}
                          className={cn(
                            'flex items-start gap-2.5 w-full p-2 rounded-lg text-left transition-colors',
                            isSelected ? 'bg-lumina-500/15 text-white' : 'hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200'
                          )}
                        >
                          <Icon size={16} className={cn('mt-0.5 flex-shrink-0', isSelected ? 'text-lumina-400' : 'text-zinc-500')} />
                          <div>
                            <p className="text-xs font-semibold text-zinc-200">{opt.label}</p>
                            <p className="text-[10px] text-zinc-500 mt-0.5 leading-tight">{opt.desc}</p>
                          </div>
                        </button>
                      )
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isInvalid || loading}
            aria-label="Enviar pergunta"
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-xl transition-all duration-200',
              isInvalid || loading
                ? 'bg-zinc-800 text-zinc-600 cursor-not-allowed opacity-50'
                : 'bg-lumina-gradient text-white shadow-md shadow-lumina-500/20 hover:scale-105 active:scale-95'
            )}
          >
            <Send size={14} className={loading ? 'animate-pulse' : ''} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface;
