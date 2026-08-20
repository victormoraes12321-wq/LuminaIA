'use client'

import { useState, useRef, useEffect } from 'react'
import {
  Sparkles,
  Send,
  X,
  Bot,
  User,
  ArrowRight,
  TrendingUp,
  Table as TableIcon,
  RotateCcw,
  Zap,
  Filter,
  Layers,
  Building2,
  Users,
  Compass,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import type { AnalyticalContext, DashboardChatAction } from './types'

interface ContextualSideChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  action?: DashboardChatAction
}

interface ContextualSideChatProps {
  open: boolean
  context: AnalyticalContext
  loading: boolean
  onClose: () => void
  onSendQuery: (
    question: string,
    context: AnalyticalContext
  ) => Promise<{ answer: string; action?: DashboardChatAction }>
  onExecuteAction: (action: DashboardChatAction) => void
}

export function ContextualSideChat({
  open,
  context,
  loading: parentLoading,
  onClose,
  onSendQuery,
  onExecuteAction,
}: ContextualSideChatProps) {
  const [messages, setMessages] = useState<ContextualSideChatMessage[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content:
        'Olá! Estou pronto para explorar os dados executivos com você. Pergunte sobre faturamento, filiais, vendedores ou peça para alterar a visualização.',
      timestamp: 'Agora',
    },
  ])
  const [input, setInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, chatLoading])

  const handleSend = async (textToSend?: string) => {
    const q = (textToSend || input).trim()
    if (!q || chatLoading) return

    const userMsg: ContextualSideChatMessage = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: q,
      timestamp: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages(prev => [...prev, userMsg])
    if (!textToSend) setInput('')
    setChatLoading(true)

    try {
      const response = await onSendQuery(q, context)
      const assistantMsg: ContextualSideChatMessage = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        action: response.action,
      }
      setMessages(prev => [...prev, assistantMsg])

      // Auto-dispatch typed action
      if (response.action) {
        onExecuteAction(response.action)
      }
    } catch (err) {
      const errMsg: ContextualSideChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro ao consultar o assistente contextual.',
        timestamp: 'Agora',
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setChatLoading(false)
    }
  }

  // Active Context Badges
  const contextBadges = []
  if (context.filial) contextBadges.push(`Filial ${context.filial}`)
  if (context.periodPreset) contextBadges.push(context.periodPreset)
  if (context.vendedor) contextBadges.push(`Vendedor: ${context.vendedor.name}`)
  if (context.produto) contextBadges.push(`Produto: ${context.produto.name}`)
  if (context.cliente) contextBadges.push(`Cliente: ${context.cliente.name}`)
  const contextSummary = contextBadges.length > 0 ? contextBadges.join(' • ') : 'Visão Geral Consolidada'

  // Quick Prompt Chips (Categorized & Non-Clipped)
  const QUICK_PROMPTS = [
    { label: 'Quem mais vendeu?', query: 'Quem vendeu mais no período?' },
    { label: 'Top 5 Produtos', query: 'Top 5 produtos por faturamento' },
    { label: 'Ver como Tabela', query: 'Transforme em tabela' },
    { label: 'Ver como Gráfico', query: 'Transforme em gráfico' },
    { label: 'Comparar Filiais', query: 'Compare o desempenho das filiais' },
    { label: 'Limpar Filtros', query: 'Limpar filtros' },
  ]

  if (!open) return null

  return (
    <aside
      data-testid="contextual-side-chat"
      className="flex flex-col h-full w-full border-l border-white/10 bg-zinc-950/95 backdrop-blur-2xl text-[rgb(var(--text-primary))] shadow-[-10px_0_35px_rgba(0,0,0,0.6)] select-none overflow-hidden"
    >
      {/* ── Top Header ── */}
      <div className="p-4 border-b border-white/10 bg-zinc-900/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-cyan-500/15 text-cyan-400 flex items-center justify-center border border-cyan-500/30 shadow-[0_0_12px_rgba(6,182,212,0.25)]">
              <Bot size={16} />
            </div>
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-white">
                Copiloto de IA
              </h2>
              <span className="text-[10px] text-zinc-400">Assistente Contextual Ativo</span>
            </div>
          </div>

          <button
            type="button"
            data-testid="close-side-chat"
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={15} />
          </button>
        </div>

        {/* Dynamic Context Pill */}
        <div
          data-testid="side-chat-context-badge"
          className="mt-3 flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-[11px] text-cyan-300"
        >
          <Zap size={12} className="shrink-0 text-cyan-400 animate-pulse" />
          <div className="min-w-0 flex-1 truncate">
            <span className="font-semibold">Contexto:</span>{' '}
            <span className="text-zinc-300">{contextSummary}</span>
          </div>
        </div>
      </div>

      {/* ── Messages Stream ── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 thin-scroll">
        {messages.map((msg) => {
          const isUser = msg.role === 'user'
          return (
            <div
              key={msg.id}
              className={cn('flex flex-col', isUser ? 'items-end' : 'items-start')}
            >
              <div
                className={cn(
                  'max-w-[90%] rounded-2xl px-4 py-3 text-xs leading-relaxed shadow-sm transition-all',
                  isUser
                    ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-br-sm font-medium shadow-[0_4px_15px_rgba(6,182,212,0.25)]'
                    : 'bg-zinc-900/90 border border-white/10 text-zinc-200 rounded-bl-sm shadow-[0_4px_20px_rgba(0,0,0,0.4)]'
                )}
              >
                <p className="whitespace-pre-line">{msg.content}</p>

                {msg.action && (
                  <div className="mt-2.5 pt-2 border-t border-white/10 flex items-center gap-1.5 text-[10px] text-cyan-300 font-semibold">
                    <Sparkles size={11} className="text-cyan-400" />
                    <span>Ação Executada: {msg.action.action_type}</span>
                  </div>
                )}
              </div>
              <span className="text-[10px] text-zinc-500 mt-1 px-1">
                {msg.timestamp}
              </span>
            </div>
          )
        })}

        {chatLoading && (
          <div className="flex items-center gap-2 text-xs text-cyan-400 p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
            <Sparkles size={14} className="animate-spin text-cyan-400" />
            <span className="font-medium text-[11px]">Consultando dados da empresa...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Quick Context Prompt Chips (Responsive Wrap, 0 Cutoffs) ── */}
      <div className="px-3.5 py-2.5 border-t border-white/10 bg-zinc-900/40">
        <div className="flex flex-wrap gap-1.5">
          {QUICK_PROMPTS.map((chip) => (
            <button
              key={chip.label}
              type="button"
              data-testid={`quick-prompt-${chip.label.toLowerCase().replace(/\s+/g, '-')}`}
              onClick={() => handleSend(chip.query)}
              className="px-2.5 py-1 rounded-full text-[10px] font-medium bg-white/5 border border-white/10 text-zinc-300 hover:text-cyan-300 hover:bg-cyan-500/15 hover:border-cyan-500/30 transition-all cursor-pointer"
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Input Box ── */}
      <div className="p-3.5 border-t border-white/10 bg-zinc-950">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            data-testid="side-chat-input"
            placeholder="Pergunte sobre estes dados..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 rounded-xl border border-white/10 bg-zinc-900/90 px-3.5 py-2 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30 transition-all font-sans"
          />
          <button
            type="submit"
            data-testid="side-chat-send"
            disabled={!input.trim() || chatLoading}
            className="p-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-40 text-white shadow-md transition-all shrink-0 cursor-pointer"
          >
            <Send size={13} />
          </button>
        </form>
      </div>
    </aside>
  )
}

