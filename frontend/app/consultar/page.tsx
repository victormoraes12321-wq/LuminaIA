'use client'

import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  AlertCircle,
  MessageSquare,
} from 'lucide-react'
import { useLuminaQuery } from '@/hooks/useLuminaQuery'
import { useAuth } from '@/context/AuthContext'
import { Sidebar } from '@/components/Sidebar'
import { ChatInterface } from '@/components/chat/ChatInterface'
import { AssistantResponseBlock } from '@/components/chat/AssistantResponseBlock'
import { ConversationGraphNavigator } from '@/components/chat/ConversationGraphNavigator'

function WelcomeState({ onSelectQuery }: { onSelectQuery: (query: string) => void }) {
  const SUGGESTIONS = [
    { label: 'Faturamento de Junho/2026', query: 'Qual o faturamento do mes 06/2026' },
    { label: 'Top 5 Produtos em Vendas', query: 'Quais os 5 produtos mais vendidos' },
    { label: 'Ranking da Equipe Comercial', query: 'Quem sao os top vendedores' },
    { label: 'Desempenho por Filial', query: 'Qual o faturamento por filial' },
  ]

  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[420px] gap-7 p-6 max-w-2xl mx-auto text-center relative select-none">
      {/* Ambient AI Orb Glow */}
      <div className="relative">
        <motion.div
          animate={{ scale: [1, 1.15, 1], opacity: [0.35, 0.15, 0.35] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute -inset-10 rounded-full bg-gradient-to-r from-cyan-500/20 via-blue-500/20 to-purple-500/20 blur-3xl"
        />

        <motion.div
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
          className="relative w-20 h-20 rounded-2xl bg-gradient-to-br from-cyan-500/20 via-blue-500/15 to-indigo-500/20 border border-cyan-500/30 text-cyan-400 flex items-center justify-center shadow-[0_0_30px_rgba(6,182,212,0.3)]"
        >
          <Sparkles size={36} className="text-cyan-400 animate-pulse" />
        </motion.div>
      </div>

      <div className="space-y-2">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
          Como a IA pode ajudar sua gestão hoje?
        </h2>
        <p className="text-xs sm:text-sm leading-relaxed text-zinc-400 max-w-lg mx-auto">
          Faça perguntas em linguagem natural sobre o faturamento, produtos, clientes e desempenho das filiais.
        </p>
      </div>

      {/* Interactive Suggestion Chips */}
      <div className="flex flex-wrap gap-2 justify-center pt-2">
        {SUGGESTIONS.map((sugg) => (
          <button
            key={sugg.label}
            type="button"
            onClick={() => onSelectQuery(sugg.query)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium bg-zinc-900/80 hover:bg-cyan-500/15 border border-white/10 hover:border-cyan-500/40 text-zinc-300 hover:text-cyan-300 shadow-sm transition-all cursor-pointer"
          >
            <Sparkles size={12} className="text-cyan-400" />
            <span>{sugg.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export default function ConsultarPage() {
  const { loading: authLoading } = useAuth()
  const {
    loading,
    error,
    messages,
    sendQuery,
    clearError,
    injectedQuery,
    toggleFavorite,
    isFavorite,
    mode,
    changeMode,
    dashboardDefaults,
    saveDashboardDefaults,
    conversationGraph,
    resetConversation,
    backtrackToNode,
  } = useLuminaQuery()

  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, loading])

  if (authLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[rgb(var(--bg-base))]">
        <div className="flex flex-col items-center gap-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-8 h-8 rounded-full border-2 border-t-transparent border-lumina-400"
          />
          <span className="text-sm font-medium text-[rgb(var(--text-secondary))]">
            Carregando sua sessão...
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-[rgb(var(--bg-base))]">
      {/* ── Collapsible Global Sidebar ── */}
      <Sidebar onLogoClick={resetConversation} />

      {/* ── Main Consultar Dados Chat Workspace ── */}
      <main className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Simple Consultar Header */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-[rgb(var(--border)/0.5)] bg-[rgb(var(--bg-surface)/0.6)] backdrop-blur-md shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-lumina-500/10 text-lumina-400 border border-lumina-500/20">
              <Sparkles size={16} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[rgb(var(--text-primary))]">
                Consultar Dados
              </h2>
              <p className="text-[11px] text-[rgb(var(--text-muted))]">
                Exploração analítica em linguagem natural governada
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {loading && (
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-lumina-500/10 border border-lumina-500/30 text-lumina-400 text-xs font-semibold animate-pulse">
                <Sparkles size={12} />
                <span>Processando análise...</span>
              </div>
            )}
          </div>
        </header>

        {error && (
          <div className="mx-6 mt-3 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between text-xs text-amber-300 dark:text-amber-200 shadow-sm">
            <div className="flex items-center gap-2">
              <AlertCircle size={15} className="text-amber-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={clearError}
              className="text-xs font-semibold hover:underline ml-4 shrink-0 text-amber-400"
            >
              Dispensar
            </button>
          </div>
        )}

        {/* Vertical Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 min-w-0 chat-scroll">
          <div className="max-w-[1400px] mx-auto w-full flex flex-col min-h-full">
            <AnimatePresence mode="wait">
              {messages.length === 0 && (
                <motion.div
                  key="welcome"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex-1 flex items-center justify-center"
                >
                  <WelcomeState onSelectQuery={(q) => sendQuery(q)} />
                </motion.div>
              )}

              {messages.length > 0 && (
                <div className="flex gap-6 w-full max-w-[1400px] mx-auto items-start">
                  <div className="space-y-6 flex-1 pb-24 min-w-0">
                    {messages.map(msg => {
                      const isUser = msg.role === 'user'
                      if (isUser) {
                        return (
                          <div key={msg.id} className="flex justify-end">
                            <div
                              className="max-w-2xl px-5 py-3.5 rounded-2xl text-sm font-medium leading-relaxed bg-[rgb(var(--bg-elevated))] border border-[rgb(var(--border))] text-[rgb(var(--text-primary))] shadow-sm"
                            >
                              {msg.content}
                            </div>
                          </div>
                        )
                      }

                      if (!msg.queryResponse) {
                        return (
                          <div
                            key={msg.id}
                            className="max-w-2xl px-5 py-4 rounded-2xl text-sm leading-relaxed bg-[rgb(var(--bg-surface))] border border-[rgb(var(--border)/0.7)] text-[rgb(var(--text-secondary))]"
                          >
                            {msg.content}
                          </div>
                        )
                      }

                      return (
                        <AssistantResponseBlock
                          key={msg.id}
                          msg={msg}
                          isFavorited={isFavorite(msg.queryResponse?.query_id || '')}
                          onFavorite={() => {
                            if (msg.queryResponse) {
                              toggleFavorite(msg.queryResponse)
                            }
                          }}
                          onSendQuery={pergunta => sendQuery(pergunta)}
                        />
                      )
                    })}
                    <div ref={bottomRef} />
                  </div>

                  {conversationGraph && (
                    <div className="hidden 2xl:block w-72 sticky top-6">
                      <ConversationGraphNavigator
                        graph={conversationGraph}
                        onBacktrack={nodeId => backtrackToNode(nodeId)}
                      />
                    </div>
                  )}
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Bottom Input Composer */}
        <div className="p-4 border-t border-[rgb(var(--border)/0.5)] bg-[rgb(var(--bg-surface)/0.8)] backdrop-blur-md max-w-4xl mx-auto w-full">
          {error && (
            <div className="mb-2 flex items-center justify-between gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
              <div className="flex items-center gap-2">
                <AlertCircle size={14} className="shrink-0 text-red-400" />
                <span>{error}</span>
              </div>
              <button type="button" onClick={clearError} className="text-red-400 hover:text-white">
                Dispensar
              </button>
            </div>
          )}
          <ChatInterface
            messages={messages}
            loading={loading}
            error={error}
            injectedQuery={injectedQuery}
            onSend={sendQuery}
            onClearError={clearError}
            mode={mode}
            onChangeMode={changeMode}
            dashboardDefaults={dashboardDefaults}
            onSaveDashboardDefaults={saveDashboardDefaults}
          />
        </div>
      </main>
    </div>
  )
}
