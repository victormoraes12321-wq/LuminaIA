'use client'

import { useState } from 'react'
import { Check, MessageSquareText, ThumbsDown, ThumbsUp, X } from 'lucide-react'

import { getApiBase } from '@/lib/utils'
import type { QueryResponse } from '@/types/lumina'


type FeedbackCategory =
  | 'POSITIVE'
  | 'PARTIALLY_CORRECT'
  | 'INCORRECT_VALUE'
  | 'INCORRECT_FILTER'
  | 'INCORRECT_PERIOD'
  | 'INCORRECT_METRIC'
  | 'INCORRECT_ENTITY'
  | 'INCORRECT_DIMENSION'
  | 'INCORRECT_COMPARISON'
  | 'INCORRECT_VISUALIZATION'
  | 'MISSING_CONTEXT'
  | 'UNWANTED_INHERITANCE'
  | 'MISSING_INHERITANCE'
  | 'AMBIGUOUS'
  | 'OUT_OF_SCOPE'
  | 'UNSAFE_OUTPUT'
  | 'PERFORMANCE'
  | 'OTHER'

const categoryOptions: Array<{ value: FeedbackCategory; label: string }> = [
  { value: 'PARTIALLY_CORRECT', label: 'Parcialmente correta' },
  { value: 'INCORRECT_VALUE', label: 'Valor incorreto' },
  { value: 'INCORRECT_FILTER', label: 'Filtro incorreto' },
  { value: 'INCORRECT_PERIOD', label: 'Período incorreto' },
  { value: 'INCORRECT_METRIC', label: 'Métrica incorreta' },
  { value: 'INCORRECT_ENTITY', label: 'Pessoa, filial ou item incorreto' },
  { value: 'INCORRECT_DIMENSION', label: 'Agrupamento incorreto' },
  { value: 'INCORRECT_COMPARISON', label: 'Comparação incorreta' },
  { value: 'INCORRECT_VISUALIZATION', label: 'Visualização incorreta' },
  { value: 'MISSING_CONTEXT', label: 'Faltou contexto' },
  { value: 'UNWANTED_INHERITANCE', label: 'Herdou contexto que não deveria' },
  { value: 'MISSING_INHERITANCE', label: 'Não manteve o contexto' },
  { value: 'AMBIGUOUS', label: 'Resposta ambígua' },
  { value: 'OUT_OF_SCOPE', label: 'Fora do assunto solicitado' },
  { value: 'UNSAFE_OUTPUT', label: 'Conteúdo inseguro ou indevido' },
  { value: 'PERFORMANCE', label: 'Demorou ou falhou tecnicamente' },
  { value: 'OTHER', label: 'Outro motivo' },
]

interface FeedbackControlsProps {
  response: QueryResponse
}

export function FeedbackControls({ response }: FeedbackControlsProps) {
  const enabled = process.env.NEXT_PUBLIC_SUPERVISED_FEEDBACK_ENABLED === 'true'
  const [expanded, setExpanded] = useState(false)
  const [category, setCategory] = useState<FeedbackCategory>('PARTIALLY_CORRECT')
  const [explanation, setExplanation] = useState('')
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [error, setError] = useState('')

  const targetReady = Boolean(
    response.response_node_id
      && response.session_id
      && response.feedback_target_checksum,
  )
  if (!enabled || !targetReady) return null

  async function submit(selectedCategory: FeedbackCategory) {
    if (selectedCategory !== 'POSITIVE' && !explanation.trim()) {
      setExpanded(true)
      setCategory(selectedCategory)
      setError('Conte brevemente o que precisa ser corrigido.')
      return
    }
    setStatus('sending')
    setError('')
    const idempotencyKey = globalThis.crypto?.randomUUID?.()
      ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`
    try {
      const result = await fetch(`${getApiBase()}/api/v2/me/feedback`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target: {
            response_node_id: response.response_node_id,
            session_id: response.session_id,
            response_checksum: response.feedback_target_checksum,
            query_node_id: response.query_node_id ?? null,
            response_contract_version: 'lumina.query-response/1.0',
          },
          category: selectedCategory,
          correction: selectedCategory === 'POSITIVE'
            ? null
            : {
                items: [{
                  kind: 'FREE_TEXT_EXPLANATION',
                  explanation: explanation.trim(),
                }],
              },
          explanation: explanation.trim() || null,
          idempotency_key: idempotencyKey,
          contract_version: 'lumina.supervised-feedback/1.0',
        }),
      })
      if (!result.ok) throw new Error('Não foi possível registrar sua avaliação.')
      setStatus('sent')
      setExpanded(false)
    } catch (caught) {
      setStatus('error')
      setError(caught instanceof Error ? caught.message : 'Falha ao enviar avaliação.')
    }
  }

  if (status === 'sent') {
    return (
      <div
        className="flex items-center gap-2 border-t border-zinc-800/70 pt-3 text-xs text-emerald-400 no-print"
        role="status"
      >
        <Check size={14} aria-hidden="true" />
        Avaliação registrada para revisão.
      </div>
    )
  }

  return (
    <div className="border-t border-zinc-800/70 pt-3 no-print">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-zinc-400">Esta resposta ajudou?</span>
        <button
          type="button"
          onClick={() => void submit('POSITIVE')}
          disabled={status === 'sending'}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-800 hover:text-white disabled:opacity-50"
          aria-label="Marcar resposta como correta"
        >
          <ThumbsUp size={14} aria-hidden="true" />
          Sim
        </button>
        <button
          type="button"
          onClick={() => {
            setCategory('PARTIALLY_CORRECT')
            setExpanded(true)
          }}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-800 hover:text-white"
          aria-label="Marcar resposta como parcialmente correta"
        >
          <MessageSquareText size={14} aria-hidden="true" />
          Em parte
        </button>
        <button
          type="button"
          onClick={() => {
            setCategory('INCORRECT_VALUE')
            setExpanded(true)
          }}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-800 hover:text-white"
          aria-label="Marcar resposta como incorreta"
        >
          <ThumbsDown size={14} aria-hidden="true" />
          Não
        </button>
      </div>

      {expanded && (
        <div className="mt-3 max-w-xl space-y-3 border-l-2 border-indigo-500/50 pl-3">
          <div className="flex items-center justify-between gap-3">
            <label htmlFor={`feedback-category-${response.query_id}`} className="text-xs font-medium text-zinc-300">
              O que precisa melhorar?
            </label>
            <button
              type="button"
              onClick={() => setExpanded(false)}
              className="rounded-md p-1 text-zinc-500 hover:bg-zinc-800 hover:text-white"
              aria-label="Fechar avaliação"
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>
          <select
            id={`feedback-category-${response.query_id}`}
            value={category}
            onChange={(event) => setCategory(event.target.value as FeedbackCategory)}
            className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs text-zinc-200 outline-none focus:border-indigo-500"
          >
            {categoryOptions.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <label className="block text-xs text-zinc-400">
            Explique a correção
            <textarea
              value={explanation}
              onChange={(event) => setExplanation(event.target.value)}
              maxLength={2000}
              rows={3}
              className="mt-1.5 w-full resize-y rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs text-zinc-200 outline-none focus:border-indigo-500"
              placeholder="Exemplo: o período correto era julho e eu precisava do total por filial."
            />
          </label>
          {error && <p className="text-xs text-rose-400" role="alert">{error}</p>}
          <div className="flex items-center justify-between gap-3">
            <p className="text-[11px] text-zinc-500">
              O conteúdo será minimizado e revisado antes de qualquer uso.
            </p>
            <button
              type="button"
              onClick={() => void submit(category)}
              disabled={status === 'sending'}
              className="rounded-md bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {status === 'sending' ? 'Enviando...' : 'Enviar avaliação'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
