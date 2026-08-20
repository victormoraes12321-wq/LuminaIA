'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  Check,
  Database,
  Download,
  Loader2,
  RefreshCw,
  ShieldCheck,
  UserCheck,
  X,
} from 'lucide-react'

import { Sidebar } from '@/components/Sidebar'
import { useAuth } from '@/context/AuthContext'
import { getApiBase } from '@/lib/utils'
import type {
  FeedbackApiError,
  FeedbackRecord,
  FeedbackReviewDecision,
  ApprovedTrainingExample,
  TrainingCandidate,
  TrainingDatasetSnapshot,
} from '@/types/supervisedFeedback'


export default function FeedbackReviewPage() {
  const { token, user, loading: authLoading } = useAuth()
  const adminEnabled = process.env.NEXT_PUBLIC_SUPERVISED_FEEDBACK_ADMIN_ENABLED === 'true'
  const canReview = adminEnabled && (user?.role === 'ADMIN' || user?.role === 'GESTOR')
  const [items, setItems] = useState<FeedbackRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [rationale, setRationale] = useState<Record<string, string>>({})
  const [view, setView] = useState<'review' | 'curation'>('review')
  const [candidates, setCandidates] = useState<TrainingCandidate[]>([])
  const [examples, setExamples] = useState<ApprovedTrainingExample[]>([])
  const [snapshots, setSnapshots] = useState<TrainingDatasetSnapshot[]>([])
  const [selectedExamples, setSelectedExamples] = useState<string[]>([])
  const [datasetName, setDatasetName] = useState('Casos supervisionados')

  const request = useCallback(async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const response = await fetch(`${getApiBase()}/api/v2${path}`, {
      ...init,
      credentials: 'include',
      headers: {
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    const payload = await response.json() as T & FeedbackApiError
    if (!response.ok) throw new Error(payload.error?.message ?? 'Não foi possível concluir a operação.')
    return payload
  }, [token])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setItems(await request<FeedbackRecord[]>('/feedback/review/queue?limit=100'))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao carregar a fila.')
    } finally {
      setLoading(false)
    }
  }, [request])

  const loadCuration = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [nextCandidates, nextExamples, nextSnapshots] = await Promise.all([
        request<TrainingCandidate[]>('/feedback/training-candidates?limit=100'),
        request<ApprovedTrainingExample[]>('/feedback/training-examples?limit=100'),
        request<TrainingDatasetSnapshot[]>('/feedback/datasets?limit=100'),
      ])
      setCandidates(nextCandidates)
      setExamples(nextExamples)
      setSnapshots(nextSnapshots)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao carregar a curadoria.')
    } finally {
      setLoading(false)
    }
  }, [request])

  useEffect(() => {
    if (!canReview) return
    const timeout = window.setTimeout(
      () => void (view === 'review' ? load() : loadCuration()),
      0,
    )
    return () => window.clearTimeout(timeout)
  }, [canReview, load, loadCuration, view])

  async function assign(item: FeedbackRecord) {
    if (!user) return
    await request(`/feedback/${item.feedback_id}/reviewer`, {
      method: 'POST',
      body: JSON.stringify({
        reviewer_user_id: user.id,
        expected_lock_version: item.lock_version,
      }),
    })
    await load()
  }

  async function review(item: FeedbackRecord, decision: FeedbackReviewDecision) {
    const text = rationale[item.feedback_id]?.trim()
    if (!text) {
      setError('Informe a justificativa da revisão.')
      return
    }
    await request(`/feedback/${item.feedback_id}/review`, {
      method: 'POST',
      body: JSON.stringify({
        decision,
        rationale: text,
        expected_lock_version: item.lock_version,
      }),
    })
    await load()
  }

  async function finalize(item: FeedbackRecord, action: 'approve' | 'reject') {
    await request(`/feedback/${item.feedback_id}/${action}`, {
      method: 'POST',
      body: JSON.stringify({ expected_lock_version: item.lock_version }),
    })
    await load()
  }

  async function transitionCandidate(
    item: TrainingCandidate,
    action: 'validate' | 'approve' | 'reject',
  ) {
    await request(`/feedback/training-candidates/${item.candidate_id}/${action}`, {
      method: 'POST',
      body: JSON.stringify({
        expected_lock_version: item.lock_version,
        ...(action === 'approve' ? { domain: 'GENERAL' } : {}),
      }),
    })
    await loadCuration()
  }

  async function createDataset() {
    if (!selectedExamples.length) {
      setError('Selecione ao menos um exemplo aprovado.')
      return
    }
    await request('/feedback/datasets', {
      method: 'POST',
      body: JSON.stringify({
        version: 1,
        name: datasetName.trim() || 'Casos supervisionados',
        description: 'Snapshot governado para avaliação offline.',
        purpose: 'OFFLINE_EVALUATION',
        example_ids: selectedExamples,
      }),
    })
    setSelectedExamples([])
    await loadCuration()
  }

  async function transitionSnapshot(
    item: TrainingDatasetSnapshot,
    action: 'transition' | 'publish',
    target?: 'IN_REVIEW' | 'APPROVED' | 'REJECTED',
  ) {
    await request(`/feedback/datasets/${item.snapshot_id}/${action}`, {
      method: 'POST',
      body: JSON.stringify({
        expected_lock_version: item.lock_version,
        ...(target ? { target } : {}),
      }),
    })
    await loadCuration()
  }

  async function exportSnapshot(item: TrainingDatasetSnapshot) {
    const response = await fetch(
      `${getApiBase()}/api/v2/feedback/datasets/${item.snapshot_id}/export`,
      {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ purpose: 'OFFLINE_EVALUATION' }),
      },
    )
    if (!response.ok) {
      const payload = await response.json() as FeedbackApiError
      throw new Error(payload.error?.message ?? 'Falha ao exportar o snapshot.')
    }
    const url = URL.createObjectURL(await response.blob())
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `dataset-${item.dataset_id}-v${item.version}.jsonl`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex min-h-screen bg-[rgb(var(--bg-primary))] text-[rgb(var(--text-primary))]">
      <Sidebar />
      <main className="dashboard-main-content min-w-0 flex-1">
        <header className="border-b border-[rgb(var(--border))] px-6 py-5">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
            <div>
              <h1 className="text-lg font-semibold">
                {view === 'review' ? 'Revisão de feedback' : 'Curadoria supervisionada'}
              </h1>
            </div>
            <button
              type="button"
              onClick={() => void (view === 'review' ? load() : loadCuration())}
              className="rounded-md p-2 text-zinc-400 hover:bg-zinc-800 hover:text-white"
              aria-label="Atualizar fila"
            >
              <RefreshCw size={16} aria-hidden="true" />
            </button>
          </div>
        </header>
        <div className="mx-auto max-w-7xl px-6 py-6">
          <div className="mb-5 inline-flex rounded-md border border-zinc-800 p-1" role="tablist" aria-label="Área de feedback">
            <button
              type="button"
              role="tab"
              aria-selected={view === 'review'}
              onClick={() => setView('review')}
              className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-xs ${view === 'review' ? 'bg-zinc-800 text-white' : 'text-zinc-400'}`}
            >
              <ShieldCheck size={14} aria-hidden="true" /> Revisão
            </button>
            {user?.role === 'ADMIN' && (
              <button
                type="button"
                role="tab"
                aria-selected={view === 'curation'}
                onClick={() => setView('curation')}
                className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-xs ${view === 'curation' ? 'bg-zinc-800 text-white' : 'text-zinc-400'}`}
              >
                <Database size={14} aria-hidden="true" /> Curadoria
              </button>
            )}
          </div>
          {error && <p className="mb-4 text-sm text-rose-400" role="alert">{error}</p>}
          {!authLoading && !canReview ? (
            <p className="py-10 text-center text-sm text-zinc-500">A fila de revisão não está disponível para este perfil.</p>
          ) : loading ? (
            <p className="flex items-center gap-2 text-sm text-zinc-400">
              <Loader2 size={16} className="animate-spin" /> Carregando...
            </p>
          ) : view === 'review' ? (
            <div className="space-y-3">
              {items.map(item => (
                <section key={item.feedback_id} className="border-b border-zinc-800 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        <strong>{item.category}</strong>
                        <span className="text-zinc-500">{item.lifecycle}</span>
                        <span className="text-zinc-500">{item.triage?.priority} · {item.triage?.review_queue}</span>
                      </div>
                      <p className="mt-2 text-sm text-zinc-300">{item.explanation ?? 'Sem explicação adicional.'}</p>
                      {item.lifecycle === 'IN_REVIEW' && item.reviewer_user_id === user?.id && !item.review_decision && (
                        <div className="mt-3 flex flex-wrap items-end gap-2">
                          <label className="min-w-[280px] flex-1 text-xs text-zinc-400">
                            Justificativa técnica
                            <input
                              value={rationale[item.feedback_id] ?? ''}
                              onChange={event => setRationale(value => ({
                                ...value,
                                [item.feedback_id]: event.target.value,
                              }))}
                              className="mt-1.5 h-9 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm text-zinc-200"
                            />
                          </label>
                          <button
                            type="button"
                            onClick={() => void review(item, 'CORRECT')}
                            className="rounded-md border border-zinc-700 px-3 py-2 text-xs hover:bg-zinc-800"
                          >
                            Correta
                          </button>
                          <button
                            type="button"
                            onClick={() => void review(item, 'INCORRECT')}
                            className="rounded-md border border-zinc-700 px-3 py-2 text-xs hover:bg-zinc-800"
                          >
                            Incorreta
                          </button>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {item.lifecycle === 'TRIAGED' && (
                        <button
                          type="button"
                          onClick={() => void assign(item)}
                          className="inline-flex items-center gap-1.5 rounded-md border border-zinc-700 px-3 py-2 text-xs hover:bg-zinc-800"
                        >
                          <UserCheck size={14} aria-hidden="true" /> Assumir
                        </button>
                      )}
                      {item.lifecycle === 'IN_REVIEW' && item.review_decision && user?.role === 'ADMIN' && (
                        <>
                          <button
                            type="button"
                            onClick={() => void finalize(item, 'approve')}
                            className="rounded-md p-2 text-emerald-400 hover:bg-zinc-800"
                            aria-label="Aprovar feedback revisado"
                          >
                            <Check size={16} aria-hidden="true" />
                          </button>
                          <button
                            type="button"
                            onClick={() => void finalize(item, 'reject')}
                            className="rounded-md p-2 text-rose-400 hover:bg-zinc-800"
                            aria-label="Rejeitar feedback revisado"
                          >
                            <X size={16} aria-hidden="true" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </section>
              ))}
              {!items.length && <p className="py-10 text-center text-sm text-zinc-500">A fila está vazia.</p>}
            </div>
          ) : (
            <div className="space-y-8">
              <section>
                <h2 className="text-sm font-semibold">Candidatos</h2>
                <div className="mt-3 divide-y divide-zinc-800 border-y border-zinc-800">
                  {candidates.map(item => (
                    <div key={item.candidate_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                      <div className="text-xs">
                        <strong>{item.status}</strong>
                        <span className="ml-2 text-zinc-500">{item.quality_status}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {item.status === 'CANDIDATE' && (
                          <>
                            <button
                              type="button"
                              onClick={() => void transitionCandidate(item, 'validate')}
                              className="rounded-md border border-zinc-700 px-3 py-2 text-xs hover:bg-zinc-800"
                            >
                              Validar
                            </button>
                            <button
                              type="button"
                              onClick={() => void transitionCandidate(item, 'reject')}
                              className="rounded-md p-2 text-rose-400 hover:bg-zinc-800"
                              aria-label="Rejeitar candidato"
                            >
                              <X size={15} aria-hidden="true" />
                            </button>
                          </>
                        )}
                        {item.status === 'VALIDATED' && (
                          <button
                            type="button"
                            onClick={() => void transitionCandidate(item, 'approve')}
                            className="rounded-md border border-emerald-700 px-3 py-2 text-xs text-emerald-300 hover:bg-emerald-950"
                          >
                            Aprovar exemplo
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                  {!candidates.length && <p className="py-6 text-sm text-zinc-500">Nenhum candidato disponível.</p>}
                </div>
              </section>

              <section>
                <h2 className="text-sm font-semibold">Novo snapshot</h2>
                <div className="mt-3 grid gap-3 sm:grid-cols-[minmax(220px,1fr)_auto]">
                  <label className="text-xs text-zinc-400">
                    Nome do dataset
                    <input
                      value={datasetName}
                      onChange={event => setDatasetName(event.target.value)}
                      className="mt-1.5 h-9 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm text-zinc-200"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => void createDataset()}
                    className="self-end rounded-md border border-zinc-700 px-3 py-2 text-xs hover:bg-zinc-800"
                  >
                    Criar snapshot
                  </button>
                </div>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {examples.map(item => (
                    <label key={item.example_id} className="flex items-center gap-2 border-b border-zinc-800 py-2 text-xs">
                      <input
                        type="checkbox"
                        checked={selectedExamples.includes(item.example_id)}
                        onChange={() => setSelectedExamples(current => (
                          current.includes(item.example_id)
                            ? current.filter(id => id !== item.example_id)
                            : [...current, item.example_id]
                        ))}
                      />
                      <span className="truncate">{item.domain} · qualidade {item.quality_score}</span>
                    </label>
                  ))}
                </div>
              </section>

              <section>
                <h2 className="text-sm font-semibold">Snapshots</h2>
                <div className="mt-3 divide-y divide-zinc-800 border-y border-zinc-800">
                  {snapshots.map(item => (
                    <div key={item.snapshot_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                      <div className="text-xs">
                        <strong>{item.name}</strong>
                        <span className="ml-2 text-zinc-500">v{item.version} · {item.status} · {item.example_ids.length} exemplos</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {item.status === 'DRAFT' && (
                          <button
                            type="button"
                            onClick={() => void transitionSnapshot(item, 'transition', 'IN_REVIEW')}
                            className="rounded-md border border-zinc-700 px-3 py-2 text-xs hover:bg-zinc-800"
                          >
                            Enviar para revisão
                          </button>
                        )}
                        {item.status === 'IN_REVIEW' && (
                          <button
                            type="button"
                            onClick={() => void transitionSnapshot(item, 'transition', 'APPROVED')}
                            className="rounded-md border border-zinc-700 px-3 py-2 text-xs hover:bg-zinc-800"
                          >
                            Aprovar snapshot
                          </button>
                        )}
                        {item.status === 'APPROVED' && (
                          <button
                            type="button"
                            onClick={() => void transitionSnapshot(item, 'publish')}
                            className="rounded-md border border-emerald-700 px-3 py-2 text-xs text-emerald-300 hover:bg-emerald-950"
                          >
                            Publicar
                          </button>
                        )}
                        {item.status === 'PUBLISHED' && (
                          <button
                            type="button"
                            onClick={() => void exportSnapshot(item)}
                            className="rounded-md p-2 text-zinc-300 hover:bg-zinc-800"
                            aria-label={`Exportar ${item.name} versão ${item.version}`}
                          >
                            <Download size={15} aria-hidden="true" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                  {!snapshots.length && <p className="py-6 text-sm text-zinc-500">Nenhum snapshot criado.</p>}
                </div>
              </section>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
