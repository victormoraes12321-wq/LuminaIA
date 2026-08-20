'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  CheckCircle2,
  Database,
  Loader2,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Upload,
} from 'lucide-react'

import { Sidebar } from '@/components/Sidebar'
import { useAuth } from '@/context/AuthContext'
import { getApiBase } from '@/lib/utils'
import type {
  SemanticApiError,
  SemanticAuditEvent,
  SemanticCapabilities,
  SemanticEvaluationResult,
  SemanticIndexDefinition,
  SemanticIndexSource,
  SemanticIndexVersion,
  SemanticSearchResult,
} from '@/types/semanticRetrieval'


export default function SemanticIndexPage() {
  const { token, user, loading: authLoading } = useAuth()
  const featureEnabled = process.env.NEXT_PUBLIC_SEMANTIC_RETRIEVAL_ENABLED === 'true'
  const canAdminister = featureEnabled && user?.role === 'ADMIN'
  const [capabilities, setCapabilities] = useState<SemanticCapabilities | null>(null)
  const [indexes, setIndexes] = useState<SemanticIndexDefinition[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [versions, setVersions] = useState<SemanticIndexVersion[]>([])
  const [events, setEvents] = useState<SemanticAuditEvent[]>([])
  const [staleSources, setStaleSources] = useState<SemanticIndexSource[]>([])
  const [evaluations, setEvaluations] = useState<SemanticEvaluationResult[]>([])
  const [term, setTerm] = useState('')
  const [expectedType, setExpectedType] = useState('')
  const [domain, setDomain] = useState('')
  const [inspection, setInspection] = useState<SemanticSearchResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState('')
  const [error, setError] = useState('')

  const request = useCallback(async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const response = await fetch(`${getApiBase()}/api/v2/semantic${path}`, {
      ...init,
      credentials: 'include',
      headers: {
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    const payload = await response.json() as T & SemanticApiError
    if (!response.ok) {
      throw new Error(payload.error?.message ?? 'Não foi possível concluir a operação.')
    }
    return payload
  }, [token])

  const selected = useMemo(
    () => indexes.find(index => index.index_id === selectedId) ?? null,
    [indexes, selectedId],
  )

  const load = useCallback(async () => {
    if (!canAdminister) return
    setLoading(true)
    setError('')
    try {
      const [nextCapabilities, nextIndexes] = await Promise.all([
        request<SemanticCapabilities>('/capabilities'),
        request<SemanticIndexDefinition[]>('/admin/indexes'),
      ])
      setCapabilities(nextCapabilities)
      setIndexes(nextIndexes)
      setSelectedId(current => current || nextIndexes[0]?.index_id || '')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao carregar os índices.')
    } finally {
      setLoading(false)
    }
  }, [canAdminister, request])

  const loadSelected = useCallback(async () => {
    if (!selectedId) {
      setVersions([])
      setEvents([])
      setStaleSources([])
      setEvaluations([])
      return
    }
    try {
      const [nextVersions, nextEvents, nextStaleSources, nextEvaluations] = await Promise.all([
        request<SemanticIndexVersion[]>(`/admin/indexes/${selectedId}/versions`),
        request<SemanticAuditEvent[]>(`/admin/audit?index_id=${selectedId}&limit=100`),
        selected?.active_version_id
          ? request<SemanticIndexSource[]>(`/admin/indexes/${selectedId}/stale-sources`)
          : Promise.resolve([]),
        request<SemanticEvaluationResult[]>(`/admin/indexes/${selectedId}/evaluations?limit=20`),
      ])
      setVersions(nextVersions)
      setEvents(nextEvents)
      setStaleSources(nextStaleSources)
      setEvaluations(nextEvaluations)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao carregar a versão.')
    }
  }, [request, selected, selectedId])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  useEffect(() => {
    const timer = window.setTimeout(() => void loadSelected(), 0)
    return () => window.clearTimeout(timer)
  }, [loadSelected])

  async function runAction(name: string, operation: () => Promise<unknown>) {
    setAction(name)
    setError('')
    try {
      await operation()
      await load()
      await loadSelected()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'A operação falhou.')
    } finally {
      setAction('')
    }
  }

  async function createIndex() {
    await runAction('create', async () => {
      const created = await request<SemanticIndexDefinition>('/admin/indexes/default', {
        method: 'POST',
        body: JSON.stringify({ name: 'Índice semântico empresarial' }),
      })
      setSelectedId(created.index_id)
    })
  }

  async function buildIndex() {
    if (!selected) return
    await runAction('build', () => request(`/admin/indexes/${selected.index_id}/build`, {
      method: 'POST',
      body: JSON.stringify({
        index_id: selected.index_id,
        expected_definition_lock_version: selected.lock_version,
        build_mode: 'FULL',
        idempotency_key: crypto.randomUUID(),
      }),
    }))
  }

  async function publish(version: SemanticIndexVersion) {
    if (!selected) return
    await runAction(`publish-${version.version_id}`, () => request(
      `/admin/indexes/${selected.index_id}/publish`,
      {
        method: 'POST',
        body: JSON.stringify({
          version_id: version.version_id,
          expected_definition_lock_version: selected.lock_version,
          reason: 'Publicação aprovada pelo administrador.',
        }),
      },
    ))
  }

  async function rollback(version: SemanticIndexVersion) {
    if (!selected) return
    await runAction(`rollback-${version.version_id}`, () => request(
      `/admin/indexes/${selected.index_id}/rollback`,
      {
        method: 'POST',
        body: JSON.stringify({
          index_id: selected.index_id,
          target_version_id: version.version_id,
          expected_definition_lock_version: selected.lock_version,
          reason: 'Rollback operacional solicitado pelo administrador.',
        }),
      },
    ))
  }

  async function inspect(event: React.FormEvent) {
    event.preventDefault()
    if (!capabilities || !term.trim()) return
    setAction('inspect')
    setError('')
    try {
      setInspection(await request<SemanticSearchResult>('/admin/search', {
        method: 'POST',
        body: JSON.stringify({
          query: term.trim(),
          index_id: selectedId || null,
          context: {
            expected_entity_types: expectedType ? [expectedType] : [],
            expected_domain: domain.trim() || null,
            active_canonical_ids: [],
            profile_favorite_ids: [],
            permission_fingerprint: capabilities.permission_fingerprint,
            profile_tie_breaker_enabled: false,
          },
          top_k: 10,
        }),
      }))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao inspecionar o termo.')
    } finally {
      setAction('')
    }
  }

  return (
    <div className="flex min-h-screen bg-[rgb(var(--bg-primary))] text-[rgb(var(--text-primary))]">
      <Sidebar />
      <main className="dashboard-main-content min-w-0 flex-1">
        <header className="border-b border-[rgb(var(--border))] px-6 py-5">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
            <div>
              <h1 className="text-lg font-semibold">Índice semântico</h1>
              {capabilities && (
                <p className="mt-1 text-xs text-zinc-500">
                  {capabilities.mode} · {capabilities.contract_version}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => void load()}
              className="rounded-md p-2 text-zinc-400 hover:bg-zinc-800 hover:text-white"
              aria-label="Atualizar índice semântico"
              title="Atualizar"
            >
              <RefreshCw size={16} aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="mx-auto max-w-7xl px-6 py-6">
          {error && <p role="alert" className="mb-5 text-sm text-rose-400">{error}</p>}
          {!authLoading && !canAdminister ? (
            <p className="py-12 text-center text-sm text-zinc-500">
              O índice semântico não está disponível para este perfil.
            </p>
          ) : loading ? (
            <p className="flex items-center gap-2 text-sm text-zinc-400">
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
              Carregando...
            </p>
          ) : (
            <div className="space-y-8">
              <section aria-labelledby="semantic-versions-title">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 id="semantic-versions-title" className="text-sm font-semibold">Versões</h2>
                    <p className="mt-1 text-xs text-zinc-500">
                      Builds são imutáveis e exigem publicação explícita.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {indexes.length > 0 ? (
                      <>
                        <select
                          value={selectedId}
                          onChange={event => setSelectedId(event.target.value)}
                          className="h-9 rounded-md border border-zinc-800 bg-zinc-950 px-3 text-xs"
                          aria-label="Índice semântico"
                        >
                          {indexes.map(index => (
                            <option key={index.index_id} value={index.index_id}>{index.name}</option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => void buildIndex()}
                          disabled={Boolean(action)}
                          className="inline-flex h-9 items-center gap-2 rounded-md bg-indigo-600 px-3 text-xs font-medium text-white disabled:opacity-50"
                        >
                          <Play size={14} aria-hidden="true" />
                          Novo build
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => void createIndex()}
                        disabled={Boolean(action)}
                        className="inline-flex h-9 items-center gap-2 rounded-md bg-indigo-600 px-3 text-xs font-medium text-white disabled:opacity-50"
                      >
                        <Database size={14} aria-hidden="true" />
                        Criar índice
                      </button>
                    )}
                  </div>
                </div>

                <div className="overflow-x-auto border-y border-zinc-800">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-zinc-900/70 text-zinc-400">
                      <tr>
                        <th className="px-3 py-2 font-medium">Versão</th>
                        <th className="px-3 py-2 font-medium">Estado</th>
                        <th className="px-3 py-2 font-medium">Documentos</th>
                        <th className="px-3 py-2 font-medium">Aliases</th>
                        <th className="px-3 py-2 font-medium">Relações</th>
                        <th className="px-3 py-2 font-medium">Fontes</th>
                        <th className="px-3 py-2 font-medium text-right">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-900">
                      {versions.map(version => (
                        <tr key={version.version_id}>
                          <td className="px-3 py-3 font-mono">v{version.version}</td>
                          <td className="px-3 py-3">{version.lifecycle}</td>
                          <td className="px-3 py-3 tabular-nums">{version.document_count}</td>
                          <td className="px-3 py-3 tabular-nums">{version.alias_count}</td>
                          <td className="px-3 py-3 tabular-nums">{version.relation_count}</td>
                          <td className="px-3 py-3">
                            {version.source_manifest.sources.map(source => (
                              <span key={`${source.source_type}-${source.source_id}`} className="mr-2">
                                {source.source_type} {source.source_version}
                              </span>
                            ))}
                          </td>
                          <td className="px-3 py-3">
                            <div className="flex justify-end gap-1">
                              {version.lifecycle === 'READY' && (
                                <button
                                  type="button"
                                  onClick={() => void publish(version)}
                                  disabled={Boolean(action)}
                                  className="rounded-md p-2 text-emerald-400 hover:bg-emerald-500/10 disabled:opacity-50"
                                  aria-label={`Publicar versão ${version.version}`}
                                  title="Publicar"
                                >
                                  <Upload size={14} aria-hidden="true" />
                                </button>
                              )}
                              {version.lifecycle === 'DEPRECATED' && (
                                <button
                                  type="button"
                                  onClick={() => void rollback(version)}
                                  disabled={Boolean(action)}
                                  className="rounded-md p-2 text-amber-400 hover:bg-amber-500/10 disabled:opacity-50"
                                  aria-label={`Restaurar versão ${version.version}`}
                                  title="Restaurar"
                                >
                                  <RotateCcw size={14} aria-hidden="true" />
                                </button>
                              )}
                              {version.lifecycle === 'PUBLISHED' && (
                                <CheckCircle2 size={15} className="m-2 text-emerald-400" aria-label="Versão ativa" />
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section aria-labelledby="semantic-inspector-title">
                <h2 id="semantic-inspector-title" className="text-sm font-semibold">Inspector de busca</h2>
                <form onSubmit={inspect} className="mt-3 grid gap-3 md:grid-cols-[minmax(0,2fr)_1fr_1fr_auto]">
                  <label className="text-xs text-zinc-400">
                    Termo
                    <input
                      value={term}
                      onChange={event => setTerm(event.target.value)}
                      maxLength={500}
                      required
                      className="mt-1 h-9 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-zinc-100 outline-none focus:border-indigo-500"
                    />
                  </label>
                  <label className="text-xs text-zinc-400">
                    Tipo esperado
                    <select
                      value={expectedType}
                      onChange={event => setExpectedType(event.target.value)}
                      className="mt-1 h-9 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-zinc-100"
                    >
                      <option value="">Qualquer</option>
                      <option value="METRIC">Métrica</option>
                      <option value="DIMENSION">Dimensão</option>
                      <option value="BRANCH">Filial</option>
                      <option value="SELLER">Vendedor</option>
                      <option value="CUSTOMER">Cliente</option>
                      <option value="PRODUCT">Produto</option>
                    </select>
                  </label>
                  <label className="text-xs text-zinc-400">
                    Domínio
                    <input
                      value={domain}
                      onChange={event => setDomain(event.target.value)}
                      maxLength={128}
                      className="mt-1 h-9 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-zinc-100 outline-none focus:border-indigo-500"
                    />
                  </label>
                  <button
                    type="submit"
                    disabled={action === 'inspect'}
                    className="mt-5 inline-flex h-9 items-center justify-center gap-2 rounded-md border border-zinc-700 px-3 text-xs font-medium hover:bg-zinc-800 disabled:opacity-50"
                  >
                    {action === 'inspect' ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
                    Inspecionar
                  </button>
                </form>

                {inspection && (
                  <div className="mt-4 overflow-x-auto border-y border-zinc-800">
                    <div className="border-b border-zinc-800 px-3 py-2 text-xs text-zinc-400">
                      {inspection.decision} · {inspection.normalized_query}
                    </div>
                    <table className="w-full text-left text-xs">
                      <thead className="bg-zinc-900/70 text-zinc-400">
                        <tr>
                          <th className="px-3 py-2 font-medium">Candidato</th>
                          <th className="px-3 py-2 font-medium">Canônico</th>
                          <th className="px-3 py-2 font-medium">Tipo</th>
                          <th className="px-3 py-2 font-medium">Score</th>
                          <th className="px-3 py-2 font-medium">Canais</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-900">
                        {inspection.candidates.map(candidate => (
                          <tr key={candidate.document_id}>
                            <td className="px-3 py-3">{candidate.public_label}</td>
                            <td className="px-3 py-3 font-mono">{candidate.canonical_reference.canonical_id}</td>
                            <td className="px-3 py-3">{candidate.entity_type}</td>
                            <td className="px-3 py-3 tabular-nums">{candidate.score.toFixed(6)}</td>
                            <td className="px-3 py-3">
                              {candidate.breakdown.channels.map(channel => channel.channel).join(', ')}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              <section aria-labelledby="semantic-health-title">
                <h2 id="semantic-health-title" className="text-sm font-semibold">
                  Fontes e avaliações
                </h2>
                <div className="mt-3 grid gap-6 lg:grid-cols-2">
                  <div>
                    <h3 className="text-xs font-medium text-zinc-400">Fontes desatualizadas</h3>
                    {staleSources.length === 0 ? (
                      <p className="mt-2 text-xs text-emerald-400">Nenhuma fonte desatualizada.</p>
                    ) : (
                      <ul className="mt-2 divide-y divide-zinc-900 border-y border-zinc-800">
                        {staleSources.map(source => (
                          <li
                            key={`${source.source_type}-${source.source_id}`}
                            className="flex justify-between gap-3 px-3 py-2 text-xs"
                          >
                            <span>{source.source_type} · {source.source_id}</span>
                            <span className="text-amber-400">{source.source_version}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div>
                    <h3 className="text-xs font-medium text-zinc-400">Avaliações recentes</h3>
                    {evaluations.length === 0 ? (
                      <p className="mt-2 text-xs text-zinc-500">Nenhuma avaliação executada.</p>
                    ) : (
                      <ol className="mt-2 divide-y divide-zinc-900 border-y border-zinc-800">
                        {evaluations.map(evaluation => (
                          <li
                            key={evaluation.evaluation_id}
                            className="flex justify-between gap-3 px-3 py-2 text-xs"
                          >
                            <span>{evaluation.corpus_version} · {evaluation.case_count} casos</span>
                            <span className={evaluation.passed ? 'text-emerald-400' : 'text-rose-400'}>
                              {evaluation.passed ? 'APROVADA' : 'REPROVADA'}
                            </span>
                          </li>
                        ))}
                      </ol>
                    )}
                  </div>
                </div>
              </section>

              <section aria-labelledby="semantic-audit-title">
                <h2 id="semantic-audit-title" className="text-sm font-semibold">Auditoria</h2>
                <ol className="mt-3 divide-y divide-zinc-900 border-y border-zinc-800">
                  {events.slice(0, 20).map(event => (
                    <li key={event.event_id} className="flex flex-wrap justify-between gap-2 px-3 py-2 text-xs">
                      <span>{event.event_type} · {event.reason_code}</span>
                      <time className="text-zinc-500">{new Date(event.created_at).toLocaleString('pt-BR')}</time>
                    </li>
                  ))}
                </ol>
              </section>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
