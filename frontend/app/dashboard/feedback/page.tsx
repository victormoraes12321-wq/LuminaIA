'use client'

import { useCallback, useEffect, useState } from 'react'
import { Download, Loader2, RotateCcw, Send } from 'lucide-react'

import { Sidebar } from '@/components/Sidebar'
import { useAuth } from '@/context/AuthContext'
import { getApiBase } from '@/lib/utils'
import type { FeedbackApiError, FeedbackRecord } from '@/types/supervisedFeedback'


export default function MyFeedbackPage() {
  const { token } = useAuth()
  const feedbackEnabled = process.env.NEXT_PUBLIC_SUPERVISED_FEEDBACK_ENABLED === 'true'
  const [items, setItems] = useState<FeedbackRecord[]>([])
  const [loading, setLoading] = useState(feedbackEnabled)
  const [error, setError] = useState('')
  const [answers, setAnswers] = useState<Record<string, string>>({})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${getApiBase()}/api/v2/me/feedback?limit=100`, {
        credentials: 'include',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      const payload = await response.json() as FeedbackRecord[] & FeedbackApiError
      if (!response.ok) throw new Error(payload.error?.message ?? 'Não foi possível carregar suas avaliações.')
      setItems(payload)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao carregar avaliações.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (!feedbackEnabled) return
    const timeout = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timeout)
  }, [feedbackEnabled, load])

  async function withdraw(item: FeedbackRecord) {
    const response = await fetch(
      `${getApiBase()}/api/v2/me/feedback/${item.feedback_id}/withdraw`,
      {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ expected_lock_version: item.lock_version }),
      },
    )
    if (!response.ok) {
      const payload = await response.json() as FeedbackApiError
      setError(payload.error?.message ?? 'Não foi possível retirar a avaliação.')
      return
    }
    await load()
  }

  async function respond(item: FeedbackRecord) {
    const explanation = answers[item.feedback_id]?.trim()
    if (!explanation) {
      setError('Informe os dados solicitados pelo revisor.')
      return
    }
    const response = await fetch(
      `${getApiBase()}/api/v2/me/feedback/${item.feedback_id}/information-response`,
      {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          explanation,
          expected_lock_version: item.lock_version,
        }),
      },
    )
    if (!response.ok) {
      const payload = await response.json() as FeedbackApiError
      setError(payload.error?.message ?? 'Não foi possível enviar a informação.')
      return
    }
    setAnswers(current => ({ ...current, [item.feedback_id]: '' }))
    await load()
  }

  function exportOwn() {
    window.location.assign(`${getApiBase()}/api/v2/me/feedback-export`)
  }

  return (
    <div className="flex min-h-screen bg-[rgb(var(--bg-primary))] text-[rgb(var(--text-primary))]">
      <Sidebar />
      <main className="dashboard-main-content min-w-0 flex-1">
        <header className="border-b border-[rgb(var(--border))] px-6 py-5">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
            <div>
              <h1 className="text-lg font-semibold">Minhas avaliações</h1>
              <p className="mt-1 text-xs text-zinc-500">Acompanhe ou retire avaliações enviadas.</p>
            </div>
            <button
              type="button"
              onClick={exportOwn}
              className="inline-flex items-center gap-2 rounded-md border border-zinc-700 px-3 py-2 text-xs font-semibold text-zinc-300 hover:bg-zinc-800"
            >
              <Download size={14} aria-hidden="true" />
              Exportar
            </button>
          </div>
        </header>
        <div className="mx-auto max-w-6xl px-6 py-6">
          {error && <p className="mb-4 text-sm text-rose-400" role="alert">{error}</p>}
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-zinc-400">
              <Loader2 size={16} className="animate-spin" /> Carregando avaliações...
            </div>
          ) : (
            <div className="overflow-x-auto border border-zinc-800">
              <table className="w-full min-w-[720px] text-left text-xs">
                <thead className="bg-zinc-900/70 text-zinc-400">
                  <tr>
                    <th className="px-4 py-3">Data</th>
                    <th className="px-4 py-3">Categoria</th>
                    <th className="px-4 py-3">Situação</th>
                    <th className="px-4 py-3">Explicação</th>
                    <th className="px-4 py-3 text-right">Ação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {items.map(item => (
                    <tr key={item.feedback_id}>
                      <td className="px-4 py-3 text-zinc-400">
                        {new Date(item.created_at).toLocaleString('pt-BR')}
                      </td>
                      <td className="px-4 py-3 font-medium">{item.category}</td>
                      <td className="px-4 py-3">{item.lifecycle}</td>
                      <td className="max-w-md px-4 py-3 text-zinc-400">
                        <span>{item.explanation ?? 'Sem observação'}</span>
                        {item.lifecycle === 'NEEDS_INFORMATION' && (
                          <label className="mt-2 block">
                            <span className="sr-only">Informação complementar</span>
                            <input
                              value={answers[item.feedback_id] ?? ''}
                              onChange={event => setAnswers(current => ({
                                ...current,
                                [item.feedback_id]: event.target.value,
                              }))}
                              placeholder="Informação complementar"
                              className="h-8 w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-200"
                            />
                          </label>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {['RECEIVED', 'VALIDATED', 'TRIAGED'].includes(item.lifecycle) && (
                          <button
                            type="button"
                            onClick={() => void withdraw(item)}
                            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-zinc-400 hover:bg-zinc-800 hover:text-white"
                          >
                            <RotateCcw size={13} aria-hidden="true" />
                            Retirar
                          </button>
                        )}
                        {item.lifecycle === 'NEEDS_INFORMATION' && (
                          <button
                            type="button"
                            onClick={() => void respond(item)}
                            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-zinc-300 hover:bg-zinc-800 hover:text-white"
                          >
                            <Send size={13} aria-hidden="true" />
                            Responder
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {!items.length && (
                    <tr><td colSpan={5} className="px-4 py-10 text-center text-zinc-500">Nenhuma avaliação enviada.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
