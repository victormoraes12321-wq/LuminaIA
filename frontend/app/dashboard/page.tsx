'use client'

import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  AlertCircle,
} from 'lucide-react'
import { useLuminaQuery } from '@/hooks/useLuminaQuery'
import { useAuth } from '@/context/AuthContext'
import { Sidebar } from '@/components/Sidebar'
import { ChatInterface } from '@/components/chat/ChatInterface'
import { AssistantResponseBlock } from '@/components/chat/AssistantResponseBlock'
import { ConversationGraphNavigator } from '@/components/chat/ConversationGraphNavigator'

// ── Empty / Welcome State ──────────────────────────────────────

function WelcomeState() {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-8 p-8">
      {/* Hero graphic */}
      <div className="relative">
        {/* Outer glow rings */}
        <motion.div
          animate={{ scale: [1, 1.08, 1], opacity: [0.3, 0.15, 0.3] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute -inset-8 rounded-full bg-lumina-500/10 blur-2xl"
        />
        <motion.div
          animate={{ scale: [1, 1.12, 1], opacity: [0.2, 0.08, 0.2] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
          className="absolute -inset-16 rounded-full bg-teal-400/10 blur-3xl"
        />

        {/* Central icon */}
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          className="relative w-24 h-24 rounded-3xl bg-lumina-gradient flex items-center justify-center shadow-lumina-lg"
        >
          <Sparkles size={40} className="text-white" />
        </motion.div>
      </div>

      {/* Text */}
      <div className="text-center max-w-lg">
        <h2 className="text-2xl font-bold mb-3 text-gradient">
          Como posso ajudar?
        </h2>
        <p className="text-sm md:text-base leading-relaxed" style={{ color: 'rgb(var(--text-secondary))' }}>
          Faça perguntas em linguagem natural sobre seus dados.
          O Motor de Intenção identificará automaticamente a análise mais adequada.
        </p>
      </div>

      {/* Feature chips */}
      <div className="flex flex-wrap gap-2 justify-center">
        {[
          { icon: '📊', label: 'Gráficos Inteligentes' },
          { icon: '🤖', label: 'Motor de Intenção IA' },
          { icon: '⚡', label: 'Resposta em segundos' },
          { icon: '🔒', label: 'Dados Corporativos' },
        ].map(chip => (
          <span
            key={chip.label}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full"
            style={{
              background: 'rgb(var(--bg-elevated))',
              border: '1px solid rgb(var(--border) / 0.6)',
              color: 'rgb(var(--text-muted))',
            }}
          >
            <span>{chip.icon}</span>
            {chip.label}
          </span>
        ))}
      </div>
    </div>
  )
}



export default function DashboardPage() {
  const { loading: authLoading, user } = useAuth()
  const {
    loading,
    error,
    messages,
    history,
    favorites,
    sendQuery,
    clearError,
    setInjectedQuery,
    injectedQuery,
    toggleFavorite,
    isFavorite,
    mode,
    changeMode,
    conversationGraph,
    backtrackToNode,
  } = useLuminaQuery()

  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, loading])

  const handleSidebarHistory = (pergunta: string) => {
    setInjectedQuery(pergunta)
  }

  const handleSidebarFavorite = (titulo: string) => {
    setInjectedQuery(titulo)
  }

  if (authLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center animate-fade-in" style={{ background: 'rgb(var(--bg-base))' }}>
        <div className="flex flex-col items-center gap-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-8 h-8 rounded-full border-2 border-t-transparent border-lumina-400"
          />
          <span className="text-sm font-medium" style={{ color: 'rgb(var(--text-secondary))' }}>
            Carregando sua sessão...
          </span>
        </div>
      </div>
    )
  }

  return (
    <div
      className="flex h-dvh overflow-hidden"
      style={{ background: 'rgb(var(--bg-base))' }}
    >
      {/* ── Sidebar ─────────────────────────────────────────── */}
      <Sidebar
        history={history}
        favorites={favorites}
        onSelectHistory={handleSidebarHistory}
        onSelectFavorite={handleSidebarFavorite}
      />

      {/* ── Main Content ─────────────────────────────────────── */}
      <main
        className="flex flex-col flex-1 min-w-0 overflow-hidden"
        style={{ marginLeft: 'var(--sidebar-w)' }}
      >
        {/* Top Bar */}
        <header
          className="flex items-center justify-between px-6 py-4 flex-shrink-0"
          style={{ borderBottom: '1px solid rgb(var(--border) / 0.5)' }}
        >
          <div>
            <h2 className="text-base font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
              Dashboard Inteligente
            </h2>
            <p className="text-xs mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
              {history.length > 0
                ? `${history.length} ${history.length === 1 ? 'consulta realizada' : 'consultas realizadas'} nesta sessão`
                : 'Consulte seus dados em linguagem natural'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {loading && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl"
                style={{
                  background: 'rgb(var(--accent) / 0.08)',
                  border: '1px solid rgb(var(--accent) / 0.2)',
                }}
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="w-3 h-3 rounded-full border-2 border-t-transparent border-lumina-400"
                />
                <span className="text-xs font-medium text-lumina-400">
                  Processando...
                </span>
              </motion.div>
            )}
          </div>
        </header>

        {/* ── Bento Grid / Workspace Area ──────────────────── */}
        <div className="flex-1 overflow-y-auto p-6 min-w-0 chat-scroll">
          <div className="max-w-[1600px] mx-auto w-full flex flex-col">
            <AnimatePresence mode="wait">
              {/* Se não houver mensagens, mostra tela de boas-vindas */}
              {messages.length === 0 && (
                <motion.div
                  key="welcome"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex-1 flex items-center justify-center"
                >
                  <WelcomeState />
                </motion.div>
              )}

              {/* Timeline de Conversa (Perguntas, Respostas e Dashboards Inline) */}
              {messages.length > 0 && (
                <div className="flex gap-6 w-full max-w-[1600px] mx-auto items-start">
                  {/* Timeline Principal */}
                  <div className="space-y-8 flex-1 pb-24 min-w-0">
                    {messages.map((msg) => {
                      const isUser = msg.role === 'user'
                      const isError = msg.role === 'error'
                      if (isUser) {
                        return (
                          <div key={msg.id} className="flex items-start gap-3 flex-row-reverse animate-fade-in w-full max-w-5xl mx-auto">
                            {/* User Avatar */}
                            <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 bg-lumina-gradient text-white text-[10px] font-bold select-none">
                              {user ? user.nome.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : 'U'}
                            </div>
                            {/* User Content Bubble */}
                            <div
                              className="max-w-[70%] rounded-2xl px-5 py-3 text-sm leading-relaxed shadow-sm rounded-tr-md"
                              style={{
                                background: 'linear-gradient(135deg, rgb(var(--accent)), #8B83FF)',
                                color: 'white',
                              }}
                            >
                              <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                              <p className="text-[10px] mt-1.5 opacity-60 text-right">
                                {msg.timestamp.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                              </p>
                            </div>
                          </div>
                        )
                      }

                      if (isError) {
                        return (
                          <div key={msg.id} className="flex items-start gap-3 animate-fade-in w-full max-w-5xl mx-auto">
                            <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 bg-red-500/20 text-red-400 border border-red-500/20">
                              <AlertCircle size={14} />
                            </div>
                            <div
                              className="max-w-[85%] rounded-2xl px-5 py-3 text-sm leading-relaxed shadow-sm rounded-tl-md"
                              style={{
                                background: 'rgb(255 107 107 / 0.1)',
                                border: '1px solid rgb(255 107 107 / 0.25)',
                                color: 'rgb(255 107 107)',
                              }}
                            >
                              <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                            </div>
                          </div>
                        )
                      }

                      return (
                        <AssistantResponseBlock
                          key={msg.id}
                          msg={msg}
                          onFavorite={() => toggleFavorite(msg.queryResponse!)}
                          isFavorited={msg.queryResponse ? isFavorite(msg.queryResponse.query_id) : false}
                          onSendQuery={sendQuery}
                        />
                      )
                    })}

                    {/* Indicador de processamento/carregamento ao final da timeline */}
                    {loading && (
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-xl border flex items-center justify-center bg-zinc-800/40">
                          <Sparkles size={14} className="text-lumina-400 animate-pulse" />
                        </div>
                        <div className="p-4 rounded-2xl rounded-tl-md bg-zinc-800/40 border border-zinc-700/40">
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-lumina-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                            <div className="w-2 h-2 rounded-full bg-lumina-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                            <div className="w-2 h-2 rounded-full bg-lumina-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                        </div>
                      </div>
                    )}

                    <div ref={bottomRef} />
                  </div>

                  {/* Painel de Backtracking / Grafo (Lateral Direita) */}
                  {Object.keys(conversationGraph.nodes).length > 0 && (
                    <div className="w-80 flex-shrink-0 sticky top-0 hidden lg:block">
                      <ConversationGraphNavigator
                        graph={conversationGraph}
                        onBacktrack={backtrackToNode}
                      />
                    </div>
                  )}
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* ── Bottom Docked Chat Interface (Edge-to-Edge) ──── */}
        <div
          className="w-full flex-shrink-0 border-t border-slate-200/50 dark:border-zinc-800/50 bg-slate-50/80 dark:bg-zinc-950/80 backdrop-blur-md px-6 py-4"
        >
          <div className="max-w-3xl mx-auto w-full">
            <ChatInterface
              messages={messages}
              loading={loading}
              error={error}
              injectedQuery={injectedQuery}
              onSend={sendQuery}
              onClearError={clearError}
              mode={mode}
              onChangeMode={changeMode}
              onSelectResponse={() => undefined}
            />
          </div>
        </div>
      </main>
    </div>
  )
}
