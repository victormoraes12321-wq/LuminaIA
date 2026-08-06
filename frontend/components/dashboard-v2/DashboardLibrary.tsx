'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { LayoutDashboard, RefreshCw, Search, ShieldCheck } from 'lucide-react'
import { Sidebar } from '@/components/Sidebar'
import { cloneDashboardV2, createDashboardIdempotencyKey, DashboardApiErrorV2, listDashboardsV2 } from '@/lib/dashboard-v2/client'
import type { DashboardListItemResponseV2 } from '@/types/dashboard_backend_v2'
import type { DashboardUiModeV2 } from '@/types/dashboard_ui_sidechat_v2'
import type { DashboardAiAssistanceModeV2 } from '@/types/dashboard_ai_assistance_v2'
import { dashboardAiAllowsPreview } from '@/lib/dashboard-ai/config'

export function DashboardLibrary({ mode, aiMode }: { readonly mode: DashboardUiModeV2; readonly aiMode: DashboardAiAssistanceModeV2 }) {
  const [items, setItems] = useState<readonly DashboardListItemResponseV2[]>([])
  const [state, setState] = useState<'LOADING' | 'READY' | 'ERROR'>('LOADING')
  const [message, setMessage] = useState('')
  const [search, setSearch] = useState('')
  const [lifecycle, setLifecycle] = useState('ALL')
  const [createOpen, setCreateOpen] = useState(false)
  const [sourceDashboardId, setSourceDashboardId] = useState('')
  const [draftTitle, setDraftTitle] = useState('Novo dashboard manual')
  const [draftCanonicalName, setDraftCanonicalName] = useState('dashboard.manual.draft')
  const [draftDescription, setDraftDescription] = useState('Rascunho manual criado a partir de uma revisão governada.')
  const requestRef = useRef<AbortController | null>(null)

  const load = () => {
    requestRef.current?.abort()
    const controller = new AbortController()
    requestRef.current = controller
    setState('LOADING')
    listDashboardsV2(controller.signal).then(result => {
      if (!controller.signal.aborted) {
        setItems(result)
        setSourceDashboardId(result[0]?.dashboard.identity.dashboard_id ?? '')
        setState('READY')
      }
    }).catch(error => {
      if (controller.signal.aborted) return
      setMessage(error instanceof DashboardApiErrorV2 ? error.message : 'Não foi possível carregar a biblioteca.')
      setState('ERROR')
    })
  }

  useEffect(() => {
    void Promise.resolve().then(load)
    return () => requestRef.current?.abort()
  }, [])

  const filtered = useMemo(() => items.filter(item => {
    const metadata = `${item.dashboard.identity.title} ${item.dashboard.identity.description} ${item.dashboard.ownership.owner_reference} ${item.dashboard.origin}`.toLocaleLowerCase('pt-BR')
    return metadata.includes(search.toLocaleLowerCase('pt-BR')) && (lifecycle === 'ALL' || item.dashboard.lifecycle === lifecycle)
  }), [items, lifecycle, search])
  const canClone = mode !== 'V2_READ' && mode !== 'V2_PREVIEW' && items.some(item => item.effective_capabilities.includes('dashboard:clone'))
  const canAiCreate = canClone && dashboardAiAllowsPreview(aiMode)
  const createDraft = async () => {
    try {
      await cloneDashboardV2(sourceDashboardId, draftCanonicalName, draftTitle, draftDescription, 'Criação manual de rascunho pela interface governada.', createDashboardIdempotencyKey())
      setCreateOpen(false)
      load()
    } catch (error) {
      setMessage(error instanceof DashboardApiErrorV2 ? error.message : 'O rascunho manual não foi criado.')
      setState('ERROR')
    }
  }

  return (
    <div className="flex min-h-screen bg-[rgb(var(--bg-base))] text-[rgb(var(--text-primary))]" data-testid="dashboard-v2-library">
      <Sidebar />
      <main className="dashboard-main-content min-w-0 flex-1 px-4 py-8 sm:px-8">
        <div className="mx-auto max-w-7xl">
          <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div><div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-violet-500"><ShieldCheck className="h-4 w-4" />Interface governada · {mode}</div><h1 className="text-3xl font-semibold tracking-tight">Dashboards governados</h1><p className="mt-2 max-w-2xl text-sm text-[rgb(var(--text-muted))]">Somente dashboards autorizados pelo backend para a sessão atual aparecem nesta biblioteca.</p></div>
            <div className="flex flex-wrap gap-2">{canAiCreate && <Link href="/dashboard/v2/new" className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white">Criar com IA</Link>}{canClone && <button type="button" onClick={() => setCreateOpen(true)} className="rounded-xl border border-violet-500 px-4 py-2 text-sm font-semibold text-violet-500">Criar rascunho manual</button>}<button type="button" onClick={load} className="rounded-xl border border-[rgb(var(--border))] px-4 py-2 text-sm"><RefreshCw className="mr-2 inline h-4 w-4" />Atualizar</button></div>
          </header>
          <section aria-label="Filtros da biblioteca" className="mb-6 flex flex-wrap gap-3 rounded-2xl border border-[rgb(var(--border)/0.6)] bg-[rgb(var(--bg-surface))] p-4">
            <label className="relative min-w-56 flex-1"><Search className="absolute left-3 top-3 h-4 w-4 text-[rgb(var(--text-muted))]" /><span className="sr-only">Buscar dashboards</span><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Buscar título, descrição, owner ou origem" className="w-full rounded-xl border border-[rgb(var(--border))] bg-transparent py-2.5 pl-10 pr-3 text-sm" /></label>
            <label><span className="sr-only">Filtrar por lifecycle</span><select value={lifecycle} onChange={event => setLifecycle(event.target.value)} className="rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg-surface))] px-3 py-2.5 text-sm"><option value="ALL">Todos os estados</option>{['DRAFT', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'ARCHIVED'].map(value => <option value={value} key={value}>{value}</option>)}</select></label>
          </section>
          {state === 'LOADING' && <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-label="Carregando dashboards">{[1, 2, 3, 4, 5, 6].map(value => <div key={value} className="h-52 animate-pulse rounded-2xl bg-[rgb(var(--bg-elevated))]" />)}</div>}
          {state === 'ERROR' && <div role="alert" className="rounded-2xl border border-red-500/40 bg-red-500/10 p-6"><p>{message}</p><button type="button" onClick={load} className="mt-4 rounded-lg border px-4 py-2 text-sm">Tentar novamente</button></div>}
          {state === 'READY' && filtered.length === 0 && <div className="rounded-2xl border border-dashed border-[rgb(var(--border))] p-12 text-center"><LayoutDashboard className="mx-auto mb-3 h-10 w-10 text-[rgb(var(--text-muted))]" /><h2 className="font-semibold">Nenhum dashboard disponível</h2><p className="mt-2 text-sm text-[rgb(var(--text-muted))]">Ajuste os filtros ou solicite acesso ao responsável. Nenhuma lista é mantida no navegador.</p></div>}
          {state === 'READY' && filtered.length > 0 && <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{filtered.map(item => <Link href={`/dashboard/v2/${encodeURIComponent(item.dashboard.identity.dashboard_id)}`} key={item.dashboard.identity.dashboard_id} className="group rounded-2xl border border-[rgb(var(--border)/0.65)] bg-[rgb(var(--bg-surface))] p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-violet-500/50"><div className="mb-5 flex items-start justify-between gap-3"><div className="rounded-xl bg-violet-500/10 p-2.5 text-violet-500"><LayoutDashboard /></div><div className="flex flex-wrap justify-end gap-1"><span className="rounded-full bg-violet-500/10 px-2 py-1 text-[10px] font-semibold text-violet-500">{item.dashboard.lifecycle}</span><span className="rounded-full border px-2 py-1 text-[10px]">{item.dashboard.classification}</span></div></div><h2 className="text-lg font-semibold group-hover:text-violet-500">{item.dashboard.identity.title}</h2><p className="mt-2 line-clamp-2 text-sm text-[rgb(var(--text-muted))]">{item.dashboard.identity.description}</p><dl className="mt-5 grid grid-cols-2 gap-3 border-t border-[rgb(var(--border)/0.45)] pt-4 text-xs"><div><dt className="text-[rgb(var(--text-muted))]">Origem</dt><dd>{item.dashboard.origin}</dd></div><div><dt className="text-[rgb(var(--text-muted))]">Publicação ativa</dt><dd>{item.dashboard.active_publication_id ? 'Sim' : 'Não'}</dd></div><div><dt className="text-[rgb(var(--text-muted))]">Última revisão</dt><dd className="truncate font-mono">{item.dashboard.head_revision_id ?? 'Nenhuma'}</dd></div><div><dt className="text-[rgb(var(--text-muted))]">Permissões</dt><dd>{item.effective_capabilities.length}</dd></div></dl></Link>)}</div>}
          {state === 'READY' && items.length >= 50 && <p className="mt-6 text-center text-xs text-[rgb(var(--text-muted))]">Primeira página keyset carregada. A continuação depende do cursor emitido pelo backend.</p>}
          {createOpen && <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4"><form className="w-full max-w-lg space-y-4 rounded-2xl bg-[rgb(var(--bg-surface))] p-6 shadow-2xl" onSubmit={event => { event.preventDefault(); void createDraft() }}><h2 className="text-lg font-semibold">Criar DRAFT manual</h2><p className="text-xs text-[rgb(var(--text-muted))]">Clona uma revisão governada existente. Nenhuma IA é chamada e nenhuma publicação é criada.</p><label className="grid gap-1 text-sm">Fonte<select value={sourceDashboardId} onChange={event => setSourceDashboardId(event.target.value)} className="rounded-lg border bg-transparent px-3 py-2">{items.filter(item => item.effective_capabilities.includes('dashboard:clone')).map(item => <option value={item.dashboard.identity.dashboard_id} key={item.dashboard.identity.dashboard_id}>{item.dashboard.identity.title}</option>)}</select></label><label className="grid gap-1 text-sm">Nome canônico<input value={draftCanonicalName} onChange={event => setDraftCanonicalName(event.target.value)} className="rounded-lg border bg-transparent px-3 py-2" /></label><label className="grid gap-1 text-sm">Título<input value={draftTitle} onChange={event => setDraftTitle(event.target.value)} className="rounded-lg border bg-transparent px-3 py-2" /></label><label className="grid gap-1 text-sm">Descrição<textarea value={draftDescription} onChange={event => setDraftDescription(event.target.value)} className="rounded-lg border bg-transparent px-3 py-2" /></label><div className="flex justify-end gap-2"><button type="button" onClick={() => setCreateOpen(false)} className="rounded-lg border px-3 py-2 text-sm">Cancelar</button><button type="submit" className="rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white">Criar DRAFT</button></div></form></div>}
        </div>
      </main>
    </div>
  )
}
