'use client'

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  Archive,
  BookOpen,
  Check,
  ChevronRight,
  Clock3,
  Diff,
  FilePlus2,
  GitBranchPlus,
  History,
  Loader2,
  Pencil,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Send,
  ShieldCheck,
  UserRoundCog,
  X,
} from 'lucide-react'
import { Sidebar } from '@/components/Sidebar'
import { Badge } from '@/components/ui/Badge'
import { useAuth } from '@/context/AuthContext'
import { cn, formatDate, getApiBase } from '@/lib/utils'
import type {
  KnowledgeApiError,
  KnowledgeAsset,
  KnowledgeAssetDetail,
  KnowledgeAuditEvent,
  KnowledgeCandidate,
  KnowledgeDiff,
  KnowledgeLifecycle,
  KnowledgeSearchResult,
} from '@/types/enterpriseKnowledge'

const API_PATH = '/api/v2/enterprise-knowledge'
const iconButtonClass = 'flex h-8 w-8 items-center justify-center rounded-md border border-zinc-700/60 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-white'
const actionButtonClass = 'inline-flex min-h-9 items-center justify-center gap-2 rounded-md border border-zinc-700/60 px-3 py-2 text-xs font-semibold text-zinc-300 transition-colors hover:bg-zinc-800 disabled:opacity-50'

const lifecycleLabels: Record<KnowledgeLifecycle, string> = {
  DRAFT: 'Rascunho',
  IN_REVIEW: 'Em revisão',
  APPROVED: 'Aprovado',
  PUBLISHED: 'Publicado',
  REJECTED: 'Rejeitado',
  DEPRECATED: 'Depreciado',
  ARCHIVED: 'Arquivado',
}

function errorMessage(payload: KnowledgeApiError, fallback: string): string {
  return payload.error?.message ?? payload.detail ?? fallback
}

function displayName(candidate: KnowledgeCandidate): string {
  return candidate.display_name || candidate.canonical_key
}

function contentDescription(content: KnowledgeAssetDetail['versions'][number]['content']): string {
  for (const value of [content.definition, content.description, content.full_description]) {
    if (typeof value === 'string' && value.trim()) return value
  }
  return 'Este asset não possui uma descrição pública.'
}

function formatOptionalDate(value: string | null): string {
  return value ? formatDate(value) : 'Sem limite'
}

export default function EnterpriseKnowledgePage() {
  const { user, token, loading: authLoading } = useAuth()
  const apiBase = getApiBase()
  const canGovern = user?.role === 'ADMIN' || user?.role === 'GESTOR'
  const canPublish = user?.role === 'ADMIN'

  const [tab, setTab] = useState<'glossary' | 'governance'>('glossary')
  const [query, setQuery] = useState('')
  const [searchResult, setSearchResult] = useState<KnowledgeSearchResult | null>(null)
  const [assets, setAssets] = useState<KnowledgeAsset[]>([])
  const [selected, setSelected] = useState<KnowledgeAssetDetail | null>(null)
  const [publicDetail, setPublicDetail] = useState<KnowledgeAssetDetail | null>(null)
  const [events, setEvents] = useState<KnowledgeAuditEvent[]>([])
  const [diff, setDiff] = useState<KnowledgeDiff | null>(null)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewDecision, setReviewDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED')
  const [reviewComment, setReviewComment] = useState('')
  const [lifecycleFilter, setLifecycleFilter] = useState('')
  const [domainFilter, setDomainFilter] = useState('')
  const [ownerFilter, setOwnerFilter] = useState('')
  const [editOpen, setEditOpen] = useState(false)
  const [editDefinition, setEditDefinition] = useState('')
  const [ownershipOpen, setOwnershipOpen] = useState(false)
  const [newOwnerId, setNewOwnerId] = useState('')
  const [form, setForm] = useState({
    canonicalKey: '',
    displayName: '',
    definition: '',
    domain: 'Vendas',
    aliases: '',
  })

  const request = useCallback(async <T,>(
    path: string,
    init?: RequestInit,
  ): Promise<T> => {
    const response = await fetch(`${apiBase}${API_PATH}${path}`, {
      ...init,
      credentials: 'include',
      headers: {
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    })
    if (!response.ok) {
      const payload = await response.json().catch(() => ({})) as KnowledgeApiError
      throw new Error(errorMessage(payload, 'Não foi possível concluir a operação.'))
    }
    return response.json() as Promise<T>
  }, [apiBase, token])

  const loadAssets = useCallback(async () => {
    if (!token || !canGovern) return
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ limit: '100' })
      if (lifecycleFilter) params.set('lifecycle', lifecycleFilter)
      if (domainFilter.trim()) params.set('domain', domainFilter.trim())
      setAssets(await request<KnowledgeAsset[]>(`/assets?${params}`))
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Erro ao carregar assets.')
    } finally {
      setLoading(false)
    }
  }, [canGovern, domainFilter, lifecycleFilter, request, token])

  useEffect(() => {
    if (tab === 'governance') void Promise.resolve().then(loadAssets)
  }, [loadAssets, tab])

  const searchGlossary = async (event: FormEvent) => {
    event.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ query: query.trim(), limit: '30' })
      setSearchResult(await request<KnowledgeSearchResult>(`/glossary?${params}`))
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : 'Erro na busca.')
    } finally {
      setLoading(false)
    }
  }

  const openPublishedDefinition = async (canonicalKey: string) => {
    setActionLoading(true)
    setError(null)
    try {
      setPublicDetail(await request<KnowledgeAssetDetail>(
        `/published/${encodeURIComponent(canonicalKey)}`,
      ))
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : 'Erro ao abrir a definição.')
    } finally {
      setActionLoading(false)
    }
  }

  const loadDetail = useCallback(async (assetId: string) => {
    setActionLoading(true)
    setError(null)
    try {
      const detail = await request<KnowledgeAssetDetail>(`/assets/${assetId}`)
      setSelected(detail)
      if (canPublish) {
        setEvents(await request<KnowledgeAuditEvent[]>(`/assets/${assetId}/audit`))
      } else {
        setEvents([])
      }
      if (detail.versions.length >= 2) {
        setDiff(await request<KnowledgeDiff>(`/assets/${assetId}/diff`, {
          method: 'POST',
          body: JSON.stringify({
            from_version_id: detail.versions[1].version_id,
            to_version_id: detail.versions[0].version_id,
          }),
        }))
      } else {
        setDiff(null)
      }
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : 'Erro ao abrir o asset.')
    } finally {
      setActionLoading(false)
    }
  }, [canPublish, request])

  const refreshSelected = async () => {
    if (!selected) return
    await Promise.all([loadAssets(), loadDetail(selected.asset.asset_id)])
  }

  const createAsset = async (event: FormEvent) => {
    event.preventDefault()
    if (!user) return
    setActionLoading(true)
    setError(null)
    try {
      const aliases = form.aliases.split(',').map(item => item.trim()).filter(Boolean)
      const response = await request<{ asset: KnowledgeAsset }>('/assets', {
        method: 'POST',
        body: JSON.stringify({
          canonical_key: form.canonicalKey.trim().toLowerCase(),
          asset_type: 'BUSINESS_TERM',
          domain: form.domain.trim(),
          owner_user_id: user.id,
          accountable_area: form.domain.trim(),
          steward_label: user.nome,
          content: {
            kind: 'BUSINESS_TERM',
            canonical_name: form.canonicalKey.trim().toLowerCase(),
            display_name: form.displayName.trim(),
            definition: form.definition.trim(),
            domain: form.domain.trim(),
            short_description: form.definition.trim().slice(0, 500),
            full_description: form.definition.trim(),
            aliases,
          },
        }),
      })
      setCreateOpen(false)
      setForm({ canonicalKey: '', displayName: '', definition: '', domain: 'Vendas', aliases: '' })
      await loadAssets()
      await loadDetail(response.asset.asset_id)
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Erro ao criar asset.')
    } finally {
      setActionLoading(false)
    }
  }

  const latestVersion = selected?.versions[0] ?? null

  const runAction = async (path: string, body?: object) => {
    if (!selected) return
    setActionLoading(true)
    setError(null)
    try {
      await request(path, {
        method: 'POST',
        ...(body ? { body: JSON.stringify(body) } : {}),
      })
      await refreshSelected()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Erro na operação.')
    } finally {
      setActionLoading(false)
    }
  }

  const submitReview = () => {
    if (!selected || !latestVersion) return
    void runAction(
      `/assets/${selected.asset.asset_id}/versions/${latestVersion.version_id}/submit`,
      { expected_lock_version: latestVersion.lock_version },
    )
  }

  const completeReview = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected || !latestVersion) return
    setReviewOpen(false)
    await runAction(
      `/assets/${selected.asset.asset_id}/versions/${latestVersion.version_id}/review`,
      {
        decision: reviewDecision,
        comment: reviewComment,
        expected_lock_version: latestVersion.lock_version,
      },
    )
    setReviewComment('')
  }

  const publish = () => {
    if (!selected || !latestVersion) return
    void runAction(
      `/assets/${selected.asset.asset_id}/versions/${latestVersion.version_id}/publish`,
      { expected_lock_version: latestVersion.lock_version },
    )
  }

  const deprecate = () => {
    if (!selected || !latestVersion) return
    if (!window.confirm('Depreciar esta versão publicada?')) return
    void runAction(
      `/assets/${selected.asset.asset_id}/versions/${latestVersion.version_id}/deprecate`,
    )
  }

  const rollback = (versionId: string) => {
    if (!selected) return
    if (!window.confirm('Criar uma nova versão baseada neste histórico?')) return
    void runAction(`/assets/${selected.asset.asset_id}/rollback`, {
      source_version_id: versionId,
    })
  }

  const createRevision = () => {
    if (!selected || !latestVersion) return
    void runAction(`/assets/${selected.asset.asset_id}/drafts`, {
      from_version_id: latestVersion.version_id,
    })
  }

  const editDraft = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected || !latestVersion) return
    const content = {
      ...latestVersion.content,
      ...(typeof latestVersion.content.definition === 'string'
        ? { definition: editDefinition.trim() }
        : { description: editDefinition.trim() }),
    }
    setEditOpen(false)
    setActionLoading(true)
    setError(null)
    try {
      await request(
        `/assets/${selected.asset.asset_id}/versions/${latestVersion.version_id}`,
        {
          method: 'PUT',
          body: JSON.stringify({
            content,
            expected_lock_version: latestVersion.lock_version,
            effective_from: latestVersion.effective_from,
            effective_to: latestVersion.effective_to,
          }),
        },
      )
      await refreshSelected()
    } catch (editError) {
      setError(editError instanceof Error ? editError.message : 'Erro ao editar o draft.')
    } finally {
      setActionLoading(false)
    }
  }

  const transferOwnership = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected) return
    setOwnershipOpen(false)
    setActionLoading(true)
    setError(null)
    try {
      await request(`/assets/${selected.asset.asset_id}/ownership`, {
        method: 'POST',
        body: JSON.stringify({
          new_owner_user_id: newOwnerId.trim(),
          expected_lock_version: selected.asset.lock_version,
        }),
      })
      await refreshSelected()
    } catch (ownershipError) {
      setError(ownershipError instanceof Error ? ownershipError.message : 'Erro ao transferir ownership.')
    } finally {
      setActionLoading(false)
    }
  }

  const filteredAssets = useMemo(
    () => assets.filter(asset => (
      !ownerFilter.trim()
      || asset.ownership.owner_user_id.toLowerCase().includes(ownerFilter.trim().toLowerCase())
      || asset.ownership.steward_label.toLowerCase().includes(ownerFilter.trim().toLowerCase())
    )),
    [assets, ownerFilter],
  )

  if (authLoading) {
    return (
      <div className="flex h-dvh items-center justify-center" style={{ background: 'rgb(var(--bg-base))' }}>
        <Loader2 className="animate-spin text-lumina-400" aria-label="Carregando" />
      </div>
    )
  }

  return (
    <div className="flex h-dvh overflow-hidden" style={{ background: 'rgb(var(--bg-base))' }}>
      <Sidebar />
      <div className="dashboard-main-content flex min-w-0 flex-1 flex-col overflow-hidden">
        <header
          className="flex flex-wrap items-center justify-between gap-4 px-5 py-4 md:px-8"
          style={{ borderBottom: '1px solid rgb(var(--border) / 0.55)' }}
        >
          <div className="flex min-w-0 items-center gap-3">
            <BookOpen size={20} className="shrink-0 text-lumina-400" />
            <div className="min-w-0">
              <h1 className="truncate text-lg font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
                Base de Conhecimento
              </h1>
              <p className="text-xs" style={{ color: 'rgb(var(--text-muted))' }}>
                lumina.enterprise-knowledge/1.0
              </p>
            </div>
          </div>
          <div className="flex items-center rounded-md border p-1" style={{ borderColor: 'rgb(var(--border))' }}>
            <button
              type="button"
              onClick={() => setTab('glossary')}
              className={cn(
                'rounded px-3 py-1.5 text-xs font-semibold',
                tab === 'glossary' ? 'bg-lumina-500 text-white' : 'text-[rgb(var(--text-secondary))]',
              )}
            >
              Glossário
            </button>
            {canGovern && (
              <button
                type="button"
                onClick={() => setTab('governance')}
                className={cn(
                  'rounded px-3 py-1.5 text-xs font-semibold',
                  tab === 'governance' ? 'bg-lumina-500 text-white' : 'text-[rgb(var(--text-secondary))]',
                )}
              >
                Governança
              </button>
            )}
          </div>
        </header>

        {error && (
          <div className="mx-5 mt-4 flex items-center gap-3 rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 md:mx-8" role="alert">
            <AlertCircle size={16} className="shrink-0 text-red-400" />
            <p className="min-w-0 flex-1 text-xs text-red-300">{error}</p>
            <button type="button" onClick={() => setError(null)} aria-label="Fechar erro">
              <X size={15} />
            </button>
          </div>
        )}

        {tab === 'glossary' ? (
          <main className="flex-1 overflow-y-auto px-5 py-6 md:px-8">
            <form onSubmit={searchGlossary} className="flex w-full max-w-3xl gap-2">
              <label className="relative flex-1">
                <span className="sr-only">Pesquisar no glossário</span>
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                <input
                  value={query}
                  onChange={event => setQuery(event.target.value)}
                  className="lumina-input w-full py-2.5 pl-10 pr-3 text-sm"
                  placeholder="Pesquisar termo ou alias"
                  maxLength={256}
                />
              </label>
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="flex h-10 w-10 items-center justify-center rounded-md bg-lumina-500 text-white disabled:opacity-50"
                aria-label="Pesquisar"
                title="Pesquisar"
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
              </button>
            </form>

            {searchResult?.ambiguous && (
              <div className="mt-5 flex items-center gap-2 text-xs text-amber-300" role="status">
                <AlertCircle size={15} />
                Termo ambíguo
              </div>
            )}

            <div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-2">
              {searchResult?.candidates.map(candidate => (
                <article
                  key={candidate.asset_id}
                  className="rounded-md border p-4"
                  style={{ borderColor: 'rgb(var(--border) / 0.7)', background: 'rgb(var(--bg-surface))' }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h2 className="truncate text-sm font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
                        {displayName(candidate)}
                      </h2>
                      <p className="mt-1 font-mono text-[11px]" style={{ color: 'rgb(var(--text-muted))' }}>
                        {candidate.canonical_key}
                      </p>
                    </div>
                    <Badge variant="success" size="xs">Publicado</Badge>
                  </div>
                  <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <dt style={{ color: 'rgb(var(--text-muted))' }}>Domínio</dt>
                      <dd className="mt-1" style={{ color: 'rgb(var(--text-secondary))' }}>{candidate.domain}</dd>
                    </div>
                    <div>
                      <dt style={{ color: 'rgb(var(--text-muted))' }}>Correspondência</dt>
                      <dd className="mt-1" style={{ color: 'rgb(var(--text-secondary))' }}>{candidate.match_type}</dd>
                    </div>
                  </dl>
                  {candidate.provenance.length > 0 && (
                    <p className="mt-4 text-[11px]" style={{ color: 'rgb(var(--text-muted))' }}>
                      {candidate.provenance[0].authority} · {candidate.provenance[0].title}
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={() => void openPublishedDefinition(candidate.canonical_key)}
                    className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-lumina-400 hover:text-lumina-300"
                  >
                    <BookOpen size={13} /> Abrir definição
                  </button>
                </article>
              ))}
            </div>

            {publicDetail && publicDetail.versions[0] && (
              <section
                className="mt-6 max-w-3xl border-t pt-6"
                style={{ borderColor: 'rgb(var(--border) / 0.6)' }}
                aria-labelledby="published-definition-title"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 id="published-definition-title" className="text-base font-bold">
                      {publicDetail.versions[0].content.display_name}
                    </h2>
                    <p className="mt-1 font-mono text-[11px] text-zinc-500">
                      {publicDetail.asset.canonical_key}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setPublicDetail(null)}
                    className={iconButtonClass}
                    aria-label="Fechar definição"
                    title="Fechar"
                  >
                    <X size={14} />
                  </button>
                </div>
                <p className="mt-4 whitespace-pre-wrap text-sm leading-6" style={{ color: 'rgb(var(--text-secondary))' }}>
                  {contentDescription(publicDetail.versions[0].content)}
                </p>
                <dl className="mt-5 grid grid-cols-1 gap-3 text-xs sm:grid-cols-3">
                  <div><dt className="text-zinc-500">Responsável</dt><dd className="mt-1">{publicDetail.asset.ownership.steward_label}</dd></div>
                  <div><dt className="text-zinc-500">Vigência inicial</dt><dd className="mt-1">{formatOptionalDate(publicDetail.versions[0].effective_from)}</dd></div>
                  <div><dt className="text-zinc-500">Vigência final</dt><dd className="mt-1">{formatOptionalDate(publicDetail.versions[0].effective_to)}</dd></div>
                </dl>
              </section>
            )}

            {searchResult && searchResult.candidates.length === 0 && (
              <div className="mt-16 text-center">
                <BookOpen size={30} className="mx-auto text-zinc-600" />
                <p className="mt-3 text-sm" style={{ color: 'rgb(var(--text-muted))' }}>Nenhuma definição publicada.</p>
              </div>
            )}
          </main>
        ) : (
          <main className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[minmax(280px,0.75fr)_minmax(420px,1.6fr)]">
            <section className="min-h-0 overflow-y-auto border-r px-4 py-4" style={{ borderColor: 'rgb(var(--border) / 0.55)' }}>
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 className="text-xs font-bold uppercase" style={{ color: 'rgb(var(--text-secondary))' }}>Assets</h2>
                <div className="flex gap-1">
                  <button type="button" onClick={() => void loadAssets()} className={iconButtonClass} title="Atualizar" aria-label="Atualizar">
                    <RefreshCw size={14} />
                  </button>
                  <button type="button" onClick={() => setCreateOpen(true)} className={iconButtonClass} title="Criar asset" aria-label="Criar asset">
                    <FilePlus2 size={14} />
                  </button>
                </div>
              </div>
              <div className="mb-4 grid grid-cols-1 gap-2">
                <label className="text-[10px] uppercase text-zinc-500">
                  Estado
                  <select
                    value={lifecycleFilter}
                    onChange={event => setLifecycleFilter(event.target.value)}
                    className="lumina-input mt-1 w-full px-2 py-2 text-xs normal-case"
                  >
                    <option value="">Todos</option>
                    {Object.entries(lifecycleLabels).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </label>
                <label className="text-[10px] uppercase text-zinc-500">
                  Domínio
                  <input
                    value={domainFilter}
                    onChange={event => setDomainFilter(event.target.value)}
                    onBlur={() => void loadAssets()}
                    className="lumina-input mt-1 w-full px-2 py-2 text-xs normal-case"
                    placeholder="Todos"
                  />
                </label>
                <label className="text-[10px] uppercase text-zinc-500">
                  Owner
                  <input
                    value={ownerFilter}
                    onChange={event => setOwnerFilter(event.target.value)}
                    className="lumina-input mt-1 w-full px-2 py-2 text-xs normal-case"
                    placeholder="Nome ou ID"
                  />
                </label>
              </div>
              {loading ? (
                <Loader2 className="mx-auto mt-14 animate-spin text-lumina-400" />
              ) : (
                <div className="space-y-1">
                  {filteredAssets.map(asset => (
                    <button
                      key={asset.asset_id}
                      type="button"
                      onClick={() => void loadDetail(asset.asset_id)}
                      className={cn(
                        'flex w-full items-center gap-3 rounded-md px-3 py-3 text-left',
                        selected?.asset.asset_id === asset.asset_id
                          ? 'bg-lumina-500/15'
                          : 'hover:bg-[rgb(var(--bg-elevated))]',
                      )}
                    >
                      <BookOpen size={14} className="shrink-0 text-lumina-400" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-xs font-semibold" style={{ color: 'rgb(var(--text-primary))' }}>
                          {asset.canonical_key}
                        </span>
                        <span className="mt-0.5 block truncate text-[10px]" style={{ color: 'rgb(var(--text-muted))' }}>
                          {asset.asset_type} · {asset.domain}
                        </span>
                      </span>
                      <ChevronRight size={13} className="shrink-0 text-zinc-600" />
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="min-h-0 overflow-y-auto px-5 py-5 md:px-7">
              {actionLoading && !selected ? (
                <Loader2 className="mx-auto mt-16 animate-spin text-lumina-400" />
              ) : selected && latestVersion ? (
                <div className="mx-auto max-w-5xl space-y-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <h2 className="text-lg font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
                        {latestVersion.content.display_name}
                      </h2>
                      <p className="mt-1 font-mono text-xs" style={{ color: 'rgb(var(--text-muted))' }}>
                        {selected.asset.canonical_key}
                      </p>
                    </div>
                    <Badge variant={latestVersion.lifecycle === 'PUBLISHED' ? 'success' : 'lumina'}>
                      {lifecycleLabels[latestVersion.lifecycle]}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap gap-2 border-y py-3" style={{ borderColor: 'rgb(var(--border) / 0.55)' }}>
                    {latestVersion.lifecycle === 'DRAFT' && (
                      <>
                        <button
                          type="button"
                          onClick={() => {
                            setEditDefinition(contentDescription(latestVersion.content))
                            setEditOpen(true)
                          }}
                          className={actionButtonClass}
                        >
                          <Pencil size={14} /> Editar
                        </button>
                        <button type="button" onClick={submitReview} className={actionButtonClass}>
                          <Send size={14} /> Submeter
                        </button>
                      </>
                    )}
                    {latestVersion.lifecycle === 'IN_REVIEW' && (
                      <>
                        <button
                          type="button"
                          onClick={() => { setReviewDecision('APPROVED'); setReviewOpen(true) }}
                          className={actionButtonClass}
                        >
                          <Check size={14} /> Aprovar
                        </button>
                        <button
                          type="button"
                          onClick={() => { setReviewDecision('REJECTED'); setReviewOpen(true) }}
                          className={cn(actionButtonClass, 'text-red-400')}
                        >
                          <X size={14} /> Rejeitar
                        </button>
                      </>
                    )}
                    {latestVersion.lifecycle === 'APPROVED' && canPublish && (
                      <button type="button" onClick={publish} className={actionButtonClass}>
                        <ShieldCheck size={14} /> Publicar
                      </button>
                    )}
                    {latestVersion.lifecycle === 'PUBLISHED' && canPublish && (
                      <>
                        <button type="button" onClick={createRevision} className={actionButtonClass}>
                          <GitBranchPlus size={14} /> Nova revisão
                        </button>
                        <button type="button" onClick={deprecate} className={actionButtonClass}>
                          <Archive size={14} /> Depreciar
                        </button>
                      </>
                    )}
                    {canPublish && (
                      <button
                        type="button"
                        onClick={() => {
                          setNewOwnerId(selected.asset.ownership.owner_user_id)
                          setOwnershipOpen(true)
                        }}
                        className={actionButtonClass}
                      >
                        <UserRoundCog size={14} /> Ownership
                      </button>
                    )}
                  </div>

                  <dl className="grid grid-cols-1 gap-4 text-xs sm:grid-cols-3">
                    <div><dt className="text-zinc-500">Versão</dt><dd className="mt-1 font-semibold">{latestVersion.version_number}</dd></div>
                    <div><dt className="text-zinc-500">Domínio</dt><dd className="mt-1 font-semibold">{selected.asset.domain}</dd></div>
                    <div><dt className="text-zinc-500">Atualizado</dt><dd className="mt-1 font-semibold">{formatDate(latestVersion.updated_at)}</dd></div>
                  </dl>

                  <dl className="grid grid-cols-1 gap-4 text-xs sm:grid-cols-3">
                    <div><dt className="text-zinc-500">Owner</dt><dd className="mt-1 break-all font-mono text-[10px]">{selected.asset.ownership.owner_user_id}</dd></div>
                    <div><dt className="text-zinc-500">Vigência inicial</dt><dd className="mt-1">{formatOptionalDate(latestVersion.effective_from)}</dd></div>
                    <div><dt className="text-zinc-500">Vigência final</dt><dd className="mt-1">{formatOptionalDate(latestVersion.effective_to)}</dd></div>
                  </dl>

                  <section>
                    <h3 className="text-xs font-bold uppercase text-zinc-500">Descrição</h3>
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-6" style={{ color: 'rgb(var(--text-secondary))' }}>
                      {contentDescription(latestVersion.content)}
                    </p>
                  </section>

                  <section>
                    <div className="mb-3 flex items-center gap-2">
                      <History size={14} className="text-lumina-400" />
                      <h3 className="text-xs font-bold uppercase text-zinc-500">Versões</h3>
                    </div>
                    <div className="overflow-x-auto rounded-md border" style={{ borderColor: 'rgb(var(--border) / 0.65)' }}>
                      <table className="w-full min-w-[520px] text-left text-xs">
                        <thead style={{ background: 'rgb(var(--bg-elevated))' }}>
                          <tr>
                            <th className="px-3 py-2">Versão</th>
                            <th className="px-3 py-2">Estado</th>
                            <th className="px-3 py-2">Checksum</th>
                            <th className="px-3 py-2 text-right">Ação</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selected.versions.map(version => (
                            <tr key={version.version_id} className="border-t" style={{ borderColor: 'rgb(var(--border) / 0.5)' }}>
                              <td className="px-3 py-2">v{version.version_number}</td>
                              <td className="px-3 py-2">{lifecycleLabels[version.lifecycle]}</td>
                              <td className="max-w-48 truncate px-3 py-2 font-mono text-[10px]">{version.checksum}</td>
                              <td className="px-3 py-2 text-right">
                                {canPublish && ['PUBLISHED', 'DEPRECATED'].includes(version.lifecycle) && (
                                  <button
                                    type="button"
                                    onClick={() => rollback(version.version_id)}
                                    className={iconButtonClass}
                                    title="Criar rollback"
                                    aria-label={`Criar rollback da versão ${version.version_number}`}
                                  >
                                    <RotateCcw size={13} />
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>

                  {diff && (
                    <section>
                      <div className="mb-3 flex items-center gap-2">
                        <Diff size={14} className="text-lumina-400" />
                        <h3 className="text-xs font-bold uppercase text-zinc-500">Diff v{diff.from_version} → v{diff.to_version}</h3>
                      </div>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                        <div className="rounded-md border p-3 text-xs"><b>Adicionados</b><p className="mt-2 text-zinc-500">{diff.added_fields.join(', ') || 'Nenhum'}</p></div>
                        <div className="rounded-md border p-3 text-xs"><b>Alterados</b><p className="mt-2 text-zinc-500">{diff.changed_fields.join(', ') || 'Nenhum'}</p></div>
                        <div className="rounded-md border p-3 text-xs"><b>Removidos</b><p className="mt-2 text-zinc-500">{diff.removed_fields.join(', ') || 'Nenhum'}</p></div>
                      </div>
                    </section>
                  )}

                  {canPublish && events.length > 0 && (
                    <section>
                      <div className="mb-3 flex items-center gap-2">
                        <Clock3 size={14} className="text-lumina-400" />
                        <h3 className="text-xs font-bold uppercase text-zinc-500">Auditoria</h3>
                      </div>
                      <ol className="space-y-2">
                        {events.map(event => (
                          <li key={event.event_id} className="flex items-center justify-between gap-3 border-b py-2 text-xs">
                            <span>{event.event_type}</span>
                            <time className="text-zinc-500">{formatDate(event.created_at)}</time>
                          </li>
                        ))}
                      </ol>
                    </section>
                  )}
                </div>
              ) : (
                <div className="flex h-full min-h-72 items-center justify-center text-sm text-zinc-500">
                  Selecione um asset
                </div>
              )}
            </section>
          </main>
        )}
      </div>

      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-4" role="presentation">
          <form
            onSubmit={createAsset}
            className="w-full max-w-xl rounded-md border p-5 shadow-2xl"
            style={{ background: 'rgb(var(--bg-surface))', borderColor: 'rgb(var(--border))' }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-knowledge-title"
          >
            <div className="flex items-center justify-between">
              <h2 id="create-knowledge-title" className="text-base font-bold">Novo termo empresarial</h2>
              <button type="button" onClick={() => setCreateOpen(false)} className={iconButtonClass} aria-label="Fechar">
                <X size={15} />
              </button>
            </div>
            <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className="text-xs">Chave canônica<input required pattern="[a-z0-9][a-z0-9_.-]{1,127}" value={form.canonicalKey} onChange={event => setForm(current => ({ ...current, canonicalKey: event.target.value }))} className="lumina-input mt-1.5 w-full px-3 py-2" /></label>
              <label className="text-xs">Nome<input required value={form.displayName} onChange={event => setForm(current => ({ ...current, displayName: event.target.value }))} className="lumina-input mt-1.5 w-full px-3 py-2" /></label>
              <label className="text-xs">Domínio<input required value={form.domain} onChange={event => setForm(current => ({ ...current, domain: event.target.value }))} className="lumina-input mt-1.5 w-full px-3 py-2" /></label>
              <label className="text-xs">Aliases<input value={form.aliases} onChange={event => setForm(current => ({ ...current, aliases: event.target.value }))} className="lumina-input mt-1.5 w-full px-3 py-2" /></label>
              <label className="text-xs sm:col-span-2">Definição<textarea required minLength={3} value={form.definition} onChange={event => setForm(current => ({ ...current, definition: event.target.value }))} className="lumina-input mt-1.5 min-h-28 w-full resize-y px-3 py-2" /></label>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setCreateOpen(false)} className={actionButtonClass}>Cancelar</button>
              <button type="submit" disabled={actionLoading} className={cn(actionButtonClass, 'bg-lumina-500 text-white')}>
                {actionLoading ? <Loader2 size={14} className="animate-spin" /> : <FilePlus2 size={14} />} Criar
              </button>
            </div>
          </form>
        </div>
      )}

      {reviewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-4" role="presentation">
          <form
            onSubmit={completeReview}
            className="w-full max-w-md rounded-md border p-5"
            style={{ background: 'rgb(var(--bg-surface))', borderColor: 'rgb(var(--border))' }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-title"
          >
            <h2 id="review-title" className="text-base font-bold">
              {reviewDecision === 'APPROVED' ? 'Aprovar versão' : 'Rejeitar versão'}
            </h2>
            <label className="mt-4 block text-xs">
              Comentário
              <textarea
                autoFocus
                required
                minLength={1}
                maxLength={4000}
                value={reviewComment}
                onChange={event => setReviewComment(event.target.value)}
                className="lumina-input mt-1.5 min-h-28 w-full resize-y px-3 py-2"
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setReviewOpen(false)} className={actionButtonClass}>Cancelar</button>
              <button type="submit" className={cn(actionButtonClass, 'bg-lumina-500 text-white')}>Confirmar</button>
            </div>
          </form>
        </div>
      )}

      {editOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-4" role="presentation">
          <form
            onSubmit={editDraft}
            className="w-full max-w-xl rounded-md border p-5"
            style={{ background: 'rgb(var(--bg-surface))', borderColor: 'rgb(var(--border))' }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-knowledge-title"
          >
            <div className="flex items-center justify-between gap-3">
              <h2 id="edit-knowledge-title" className="text-base font-bold">Editar draft</h2>
              <button type="button" onClick={() => setEditOpen(false)} className={iconButtonClass} aria-label="Fechar">
                <X size={15} />
              </button>
            </div>
            <label className="mt-4 block text-xs">
              Descrição
              <textarea
                autoFocus
                required
                minLength={3}
                maxLength={20_000}
                value={editDefinition}
                onChange={event => setEditDefinition(event.target.value)}
                className="lumina-input mt-1.5 min-h-40 w-full resize-y px-3 py-2"
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setEditOpen(false)} className={actionButtonClass}>Cancelar</button>
              <button type="submit" className={cn(actionButtonClass, 'bg-lumina-500 text-white')}>
                <Save size={14} /> Salvar
              </button>
            </div>
          </form>
        </div>
      )}

      {ownershipOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-4" role="presentation">
          <form
            onSubmit={transferOwnership}
            className="w-full max-w-md rounded-md border p-5"
            style={{ background: 'rgb(var(--bg-surface))', borderColor: 'rgb(var(--border))' }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="ownership-title"
          >
            <h2 id="ownership-title" className="text-base font-bold">Transferir ownership</h2>
            <label className="mt-4 block text-xs">
              ID do novo responsável
              <input
                autoFocus
                required
                pattern="[0-9a-fA-F-]{36}"
                value={newOwnerId}
                onChange={event => setNewOwnerId(event.target.value)}
                className="lumina-input mt-1.5 w-full px-3 py-2 font-mono text-xs"
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setOwnershipOpen(false)} className={actionButtonClass}>Cancelar</button>
              <button type="submit" className={cn(actionButtonClass, 'bg-lumina-500 text-white')}>
                <UserRoundCog size={14} /> Transferir
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
