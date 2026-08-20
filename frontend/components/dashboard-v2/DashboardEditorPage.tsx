'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, RotateCcw, Save, Send, Undo2 } from 'lucide-react'
import {
  applySemanticPatchV2,
  applyVisualPatchV2,
  createDashboardIdempotencyKey,
  DashboardApiErrorV2,
  getDashboardV2,
  submitDashboardReviewV2,
} from '@/lib/dashboard-v2/client'
import type { DashboardPatchOperationV2, DashboardSemanticPatchV2, DashboardVisualPatchV2 } from '@/types/dashboard_blueprint_v2'
import type { DashboardDetailResponseV2 } from '@/types/dashboard_backend_v2'
import type { DashboardUiModeV2 } from '@/types/dashboard_ui_sidechat_v2'
import type { DashboardAiAssistanceModeV2 } from '@/types/dashboard_ai_assistance_v2'
import { dashboardAiAllowsEdit } from '@/lib/dashboard-ai/config'

export function DashboardEditorPage({ dashboardId, mode, aiMode }: { readonly dashboardId: string; readonly mode: DashboardUiModeV2; readonly aiMode: DashboardAiAssistanceModeV2 }) {
  const [detail, setDetail] = useState<DashboardDetailResponseV2 | undefined>()
  const [editorMode, setEditorMode] = useState<'VISUAL' | 'SEMANTIC'>('VISUAL')
  const [operations, setOperations] = useState<readonly DashboardPatchOperationV2[]>([])
  const [reason, setReason] = useState('Ajuste manual governado')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [conflict, setConflict] = useState(false)
  const controllerRef = useRef<AbortController | null>(null)

  const load = useCallback(() => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    setBusy(true)
    getDashboardV2(dashboardId, controller.signal).then(setDetail).catch(error => setMessage(error instanceof DashboardApiErrorV2 ? error.message : 'Falha ao carregar editor.')).finally(() => setBusy(false))
  }, [dashboardId])
  useEffect(() => { void Promise.resolve().then(load); return () => controllerRef.current?.abort() }, [load])

  const revision = detail?.head_revision
  const blueprint = revision?.blueprint
  const titleOperation = operations.find(operation => operation.path === '/identity/title')
  const previewTitle = typeof titleOperation?.value === 'string' ? titleOperation.value : blueprint?.identity.title ?? ''
  const visualOperations = operations.filter(operation => operation.path.startsWith('/identity/') || operation.path.startsWith('/layout/') || /^\/widgets\/\d+\/(title|formatting|theme_token|visible)/.test(operation.path))
  const semanticOperations = operations.filter(operation => operation.path.startsWith('/data_bindings/') || operation.path.startsWith('/filters/') || operation.path.startsWith('/interactions/'))
  const activeOperations = editorMode === 'VISUAL' ? visualOperations : semanticOperations
  const canVisual = detail?.effective_capabilities.includes('dashboard:edit_visual') && mode !== 'V2_READ' && mode !== 'V2_PREVIEW'
  const canSemantic = detail?.effective_capabilities.includes('dashboard:edit_semantic') && mode !== 'V2_READ' && mode !== 'V2_PREVIEW'
  const firstPlacement = blueprint?.layout.breakpoints[0]?.items[0]
  const firstBinding = blueprint?.data_bindings[0]

  const setOperation = (next: DashboardPatchOperationV2) => setOperations(current => [...current.filter(operation => operation.path !== next.path), next])
  const discard = () => { setOperations([]); setConflict(false); setMessage('Preview descartado; a revisão base permanece intacta.') }
  const save = async () => {
    if (!detail || !revision || activeOperations.length === 0) return
    setBusy(true)
    setConflict(false)
    try {
      if (editorMode === 'VISUAL') {
        const patch: DashboardVisualPatchV2 = { patch_type: 'VISUAL', blueprint_id: blueprint!.identity.blueprint_id, base_blueprint_checksum: revision.blueprint_checksum, base_semantic_checksum: revision.semantic.checksum, base_visual_revision: revision.visual.number, target_visual_revision: revision.visual.number + 1, operations: activeOperations }
        const next = await applyVisualPatchV2(dashboardId, patch, detail.dashboard.lock_version, revision.lock_version, reason, createDashboardIdempotencyKey())
        setDetail(current => current ? { ...current, dashboard: { ...current.dashboard, head_revision_id: next.revision_id }, head_revision: next } : current)
        setMessage('Revisão visual criada; a semântica foi preservada.')
      } else {
        const patch: DashboardSemanticPatchV2 = { patch_type: 'SEMANTIC', blueprint_id: blueprint!.identity.blueprint_id, base_blueprint_checksum: revision.blueprint_checksum, base_semantic_checksum: revision.semantic.checksum, base_semantic_revision: revision.semantic.number, target_semantic_revision: revision.semantic.number + 1, requires_revalidation: true, operations: activeOperations }
        const next = await applySemanticPatchV2(dashboardId, patch, detail.dashboard.lock_version, revision.lock_version, reason, createDashboardIdempotencyKey())
        setDetail(current => current ? { ...current, dashboard: { ...current.dashboard, head_revision_id: next.revision_id, lifecycle: 'DRAFT', head_lifecycle: 'DRAFT' }, head_revision: next } : current)
        setMessage('Revisão semântica criada em DRAFT e enviada à revalidação autoritativa.')
      }
      setOperations([])
    } catch (error) {
      if (error instanceof DashboardApiErrorV2 && error.status === 409) setConflict(true)
      setMessage(error instanceof DashboardApiErrorV2 ? error.message : 'A revisão não foi criada.')
    } finally { setBusy(false) }
  }
  const submitReview = async () => {
    if (!detail?.head_revision) return
    setBusy(true)
    try {
      await submitDashboardReviewV2(dashboardId, detail.head_revision.revision_id, detail.dashboard.lock_version, reason, createDashboardIdempotencyKey())
      setMessage('Revisão enviada para avaliação humana.')
    } catch (error) { setMessage(error instanceof DashboardApiErrorV2 ? error.message : 'Falha ao enviar para review.') } finally { setBusy(false) }
  }

  const previewDetails = useMemo(() => `${activeOperations.length} operação(ões) sobre ${revision?.revision_id ?? 'revisão indisponível'}`, [activeOperations.length, revision?.revision_id])
  if (!detail || !blueprint || !revision) return <div className="grid min-h-screen place-items-center" role="status">{message || 'Carregando editor governado…'}</div>
  return (
    <main className="min-h-screen bg-[rgb(var(--bg-base))] p-4 text-[rgb(var(--text-primary))] sm:p-8" data-testid="dashboard-v2-editor">
      <div className="mx-auto max-w-6xl">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4"><div className="flex items-center gap-3"><Link href={`/dashboard/v2/${encodeURIComponent(dashboardId)}`} aria-label="Voltar ao dashboard"><ArrowLeft /></Link><div><h1 className="text-2xl font-semibold">Editor manual</h1><p className="text-xs text-[rgb(var(--text-muted))]">Base {revision.revision_id} · CAS {detail.dashboard.lock_version}/{revision.lock_version}</p></div></div><div className="flex flex-wrap gap-2">{dashboardAiAllowsEdit(aiMode) && <Link href={`/dashboard/v2/new?target=${encodeURIComponent(dashboardId)}&revision=${encodeURIComponent(revision.revision_id)}&kind=${editorMode.toLowerCase()}&origin=DASHBOARD_EDITOR`} className="rounded-lg bg-violet-600 px-3 py-2 text-xs font-semibold text-white">Assistir com IA</Link>}<button type="button" onClick={discard} disabled={!operations.length} className="rounded-lg border px-3 py-2 text-xs"><RotateCcw className="mr-1 inline h-3.5 w-3.5" />Descartar</button><button type="button" onClick={() => setOperations(current => current.slice(0, -1))} disabled={!operations.length} className="rounded-lg border px-3 py-2 text-xs"><Undo2 className="mr-1 inline h-3.5 w-3.5" />Desfazer</button></div></header>
        <div className="mb-5 flex rounded-xl bg-[rgb(var(--bg-elevated))] p-1"><button type="button" onClick={() => setEditorMode('VISUAL')} className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${editorMode === 'VISUAL' ? 'bg-[rgb(var(--bg-surface))] shadow' : ''}`}>VISUAL EDITOR</button><button type="button" onClick={() => setEditorMode('SEMANTIC')} className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${editorMode === 'SEMANTIC' ? 'bg-[rgb(var(--bg-surface))] shadow' : ''}`}>SEMANTIC EDITOR</button></div>
        <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
          <section className="space-y-4 rounded-2xl border border-[rgb(var(--border))] bg-[rgb(var(--bg-surface))] p-5">
            {editorMode === 'VISUAL' ? <>
              <label className="grid gap-1 text-sm">Título<input key="visual-title" value={previewTitle} disabled={!canVisual} onChange={event => setOperation({ operation: 'REPLACE', path: '/identity/title', value: event.target.value })} className="rounded-lg border bg-transparent px-3 py-2" /></label>
              <label className="grid gap-1 text-sm">Descrição<textarea defaultValue={blueprint.identity.description} disabled={!canVisual} onChange={event => setOperation({ operation: 'REPLACE', path: '/identity/description', value: event.target.value })} className="rounded-lg border bg-transparent px-3 py-2" /></label>
              {firstPlacement && <fieldset className="space-y-3 border-t pt-4"><legend className="font-semibold">Layout · primeiro widget</legend><div className="grid grid-cols-2 gap-2">{(['x', 'y', 'width', 'height'] as const).map(field => <label className="grid gap-1 text-xs" key={field}>{field}<input type="number" min={0} defaultValue={firstPlacement[field]} disabled={!canVisual} onChange={event => setOperation({ operation: 'REPLACE', path: `/layout/breakpoints/0/items/0/${field}`, value: Number(event.target.value) })} className="rounded-lg border bg-transparent px-2 py-1.5" /></label>)}</div><p aria-live="polite" className="text-xs text-[rgb(var(--text-muted))]">Controles numéricos oferecem mover e redimensionar por teclado, sem dependência de drag-and-drop.</p></fieldset>}
              <p className="rounded-lg bg-amber-500/10 p-3 text-xs">Tokens, labels, formatação, visibilidade e breakpoints usam os mesmos paths visuais allowlisted. Acessibilidade estrutural permanece visível no preview e requer revisão completa quando fora da allowlist do backend.</p>
            </> : <>
              <label className="grid gap-1 text-sm">Dataset analítico canônico<input key="semantic-dataset" defaultValue={firstBinding?.analytical_dataset_id} disabled={!canSemantic || !firstBinding} onChange={event => setOperation({ operation: 'REPLACE', path: '/data_bindings/0/analytical_dataset_id', value: event.target.value })} className="rounded-lg border bg-transparent px-3 py-2" /></label>
              <p className="rounded-lg bg-violet-500/10 p-3 text-xs">Bindings, métricas, dimensões, períodos, comparações, filtros, interações e proveniência são editados como patch semântico. Toda gravação volta a DRAFT e exige revalidação autoritativa; o side chat nunca executa este fluxo.</p>
            </>}
            <label className="grid gap-1 text-sm">Motivo<input value={reason} onChange={event => setReason(event.target.value)} minLength={3} className="rounded-lg border bg-transparent px-3 py-2" /></label>
            <button type="button" onClick={() => void save()} disabled={busy || !activeOperations.length || reason.trim().length < 3 || (editorMode === 'VISUAL' ? !canVisual : !canSemantic)} className="w-full rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"><Save className="mr-2 inline h-4 w-4" />Criar revisão</button>
            {detail.effective_capabilities.includes('dashboard:review') && <button type="button" onClick={() => void submitReview()} disabled={busy || operations.length > 0} className="w-full rounded-lg border px-4 py-2 text-sm"><Send className="mr-2 inline h-4 w-4" />Enviar para review</button>}
          </section>
          <section className="rounded-2xl border border-[rgb(var(--border))] bg-[rgb(var(--bg-surface))] p-6" aria-label="Preview imutável"><div className="mb-5 flex items-center justify-between"><div><span className="rounded-full bg-violet-500/10 px-2 py-1 text-xs text-violet-500">PREVIEW LOCAL</span><h2 className="mt-3 text-2xl font-semibold">{previewTitle}</h2><p className="mt-1 text-sm text-[rgb(var(--text-muted))]">{blueprint.identity.description}</p></div><span className="text-xs">{operations.length ? 'Dirty' : 'Clean'}</span></div><div className="grid min-h-80 place-items-center rounded-xl border border-dashed border-[rgb(var(--border))] p-8 text-center"><div><p className="font-semibold">Estrutura do Blueprint V2 preservada</p><p className="mt-2 text-sm text-[rgb(var(--text-muted))]">{previewDetails}. O preview não publica, não grava automaticamente e não altera a revisão base.</p></div></div></section>
        </div>
        {conflict && <div role="alert" className="mt-5 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4"><h2 className="font-semibold">Conflito de revisão</h2><p className="mt-1 text-sm">Nada foi sobrescrito. Recarregue a versão atual, compare com a base e reaplique manualmente.</p><button type="button" onClick={load} className="mt-3 rounded-lg border px-3 py-2 text-xs">Recarregar versão atual</button></div>}
        {message && <p role="status" className="mt-5 rounded-xl bg-[rgb(var(--bg-elevated))] p-4 text-sm">{message}</p>}
      </div>
    </main>
  )
}
