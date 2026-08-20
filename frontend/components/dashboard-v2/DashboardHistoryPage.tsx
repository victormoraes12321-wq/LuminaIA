'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, GitCompare, Users } from 'lucide-react'
import {
  addDashboardCollaboratorV2,
  approveDashboardV2,
  createDashboardIdempotencyKey,
  getDashboardV2,
  listDashboardPublicationsV2,
  listDashboardRevisionsV2,
  publishDashboardV2,
  rejectDashboardV2,
  removeDashboardCollaboratorV2,
  requestDashboardChangesV2,
  rollbackDashboardV2,
  updateDashboardCollaboratorV2,
} from '@/lib/dashboard-v2/client'
import type {
  DashboardCollaboratorRoleV2,
  DashboardDetailResponseV2,
  DashboardPublicationV2,
  DashboardRevisionRecordV2,
} from '@/types/dashboard_backend_v2'

const COLLABORATOR_ROLES: readonly DashboardCollaboratorRoleV2[] = [
  'VIEWER', 'EDITOR_VISUAL', 'EDITOR_SEMANTIC', 'REVIEWER', 'PUBLISHER', 'ADMINISTRATOR',
]

type LifecycleAction = 'CHANGES' | 'APPROVE' | 'REJECT' | 'PUBLISH' | 'ROLLBACK'

export function DashboardHistoryPage({ dashboardId }: { readonly dashboardId: string }) {
  const [detail, setDetail] = useState<DashboardDetailResponseV2>()
  const [revisions, setRevisions] = useState<readonly DashboardRevisionRecordV2[]>([])
  const [publications, setPublications] = useState<readonly DashboardPublicationV2[]>([])
  const [selected, setSelected] = useState<readonly string[]>([])
  const [confirmation, setConfirmation] = useState(false)
  const [publicationVersion, setPublicationVersion] = useState('1.0.1')
  const [comment, setComment] = useState('Decisão humana registrada pela interface governada.')
  const [newUser, setNewUser] = useState('')
  const [newRole, setNewRole] = useState<DashboardCollaboratorRoleV2>('VIEWER')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      getDashboardV2(dashboardId, controller.signal),
      listDashboardRevisionsV2(dashboardId, controller.signal),
      listDashboardPublicationsV2(dashboardId, controller.signal),
    ]).then(([nextDetail, nextRevisions, nextPublications]) => {
      setDetail(nextDetail)
      setRevisions(nextRevisions)
      setPublications(nextPublications)
    }).catch(error => {
      if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'Histórico indisponível.')
    })
    return () => controller.abort()
  }, [dashboardId])

  const compared = useMemo(() => revisions.filter(revision => selected.includes(revision.revision_id)), [revisions, selected])

  const lifecycle = async (action: LifecycleAction) => {
    if (!detail?.head_revision || !confirmation || busy) return
    setBusy(true)
    setMessage('')
    try {
      const key = createDashboardIdempotencyKey()
      if (action === 'CHANGES') await requestDashboardChangesV2(dashboardId, detail.head_revision.revision_id, detail.dashboard.lock_version, comment, key)
      if (action === 'APPROVE') await approveDashboardV2(dashboardId, detail.head_revision.revision_id, detail.dashboard.lock_version, comment, key)
      if (action === 'REJECT') await rejectDashboardV2(dashboardId, detail.head_revision.revision_id, detail.dashboard.lock_version, comment, key)
      if (action === 'PUBLISH') await publishDashboardV2(dashboardId, detail.head_revision.revision_id, detail.dashboard.lock_version, detail.active_publication?.generation ?? 0, publicationVersion, key)
      if (action === 'ROLLBACK') {
        const target = publications.find(publication => publication.publication_id !== detail.active_publication?.publication_id) ?? publications[0]
        if (!target) throw new Error('Nenhuma publicação histórica elegível para rollback.')
        await rollbackDashboardV2(dashboardId, target.publication_id, detail.dashboard.lock_version, detail.active_publication?.generation ?? 1, publicationVersion, comment, key)
      }
      setMessage(`${action} concluído pelo backend governado.`)
      setConfirmation(false)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Ação de lifecycle bloqueada.')
    } finally {
      setBusy(false)
    }
  }

  const addCollaborator = async () => {
    if (!detail || !newUser.trim() || busy) return
    setBusy(true)
    try {
      const collaborator = await addDashboardCollaboratorV2(dashboardId, newUser.trim(), newRole)
      setDetail({ ...detail, collaborators: [...detail.collaborators, collaborator] })
      setNewUser('')
      setMessage('Colaborador incluído pelo backend governado.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Colaborador não incluído.')
    } finally { setBusy(false) }
  }

  const updateCollaborator = async (collaboratorId: string, role: DashboardCollaboratorRoleV2, lockVersion: number) => {
    if (!detail || busy) return
    setBusy(true)
    try {
      const updated = await updateDashboardCollaboratorV2(dashboardId, collaboratorId, role, lockVersion)
      setDetail({ ...detail, collaborators: detail.collaborators.map(item => item.collaborator_id === collaboratorId ? updated : item) })
      setMessage('Papel do colaborador atualizado com CAS.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Papel não atualizado.')
    } finally { setBusy(false) }
  }

  const removeCollaborator = async (collaboratorId: string, lockVersion: number) => {
    if (!detail || !confirmation || busy) return
    setBusy(true)
    try {
      await removeDashboardCollaboratorV2(dashboardId, collaboratorId, lockVersion)
      setDetail({ ...detail, collaborators: detail.collaborators.filter(item => item.collaborator_id !== collaboratorId) })
      setMessage('Colaborador removido com CAS.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Colaborador não removido.')
    } finally { setBusy(false) }
  }

  if (!detail) return <main className="grid min-h-screen place-items-center" role="status">Carregando histórico governado…</main>
  const canManageCollaborators = detail.effective_capabilities.includes('dashboard:manage_collaborators')

  return (
    <main className="min-h-screen bg-[rgb(var(--bg-base))] p-4 text-[rgb(var(--text-primary))] sm:p-8" data-testid="dashboard-v2-history">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 flex items-center gap-3"><Link href={`/dashboard/v2/${encodeURIComponent(dashboardId)}`} aria-label="Voltar"><ArrowLeft /></Link><div><h1 className="text-2xl font-semibold">Histórico e colaboração</h1><p className="text-xs text-[rgb(var(--text-muted))]">Eventos imutáveis; rollback sempre cria nova publicação no backend.</p></div></header>
        <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
          <section className="space-y-3"><h2 className="font-semibold">Revisões</h2>{revisions.map(revision => <label key={revision.revision_id} className="flex gap-3 rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg-surface))] p-4"><input type="checkbox" checked={selected.includes(revision.revision_id)} disabled={!selected.includes(revision.revision_id) && selected.length >= 2} onChange={event => setSelected(current => event.target.checked ? [...current, revision.revision_id] : current.filter(id => id !== revision.revision_id))} /><div className="min-w-0"><p className="truncate font-mono text-xs">{revision.revision_id}</p><p className="mt-1 text-sm">{revision.reason}</p><p className="mt-2 text-xs text-[rgb(var(--text-muted))]">Visual {revision.visual.number} · Semântica {revision.semantic.number} · {revision.semantic.validation_status} · {revision.created_at}</p></div></label>)}{!revisions.length && <p>Nenhuma revisão disponível.</p>}</section>
          <aside className="space-y-6">
            <section className="rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg-surface))] p-4"><h2 className="mb-3 flex items-center gap-2 font-semibold"><GitCompare className="h-4 w-4" />Comparar</h2>{compared.length === 2 ? <dl className="text-xs"><dt>Semântica</dt><dd>{compared[0].semantic.checksum === compared[1].semantic.checksum ? 'Preservada' : 'Alterada'}</dd><dt className="mt-2">Visual</dt><dd>{compared[0].visual.checksum === compared[1].visual.checksum ? 'Preservado' : 'Alterado'}</dd></dl> : <p className="text-xs text-[rgb(var(--text-muted))]">Selecione duas revisões. A comparação autoritativa continua disponível no backend.</p>}</section>
            <section className="rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--bg-surface))] p-4"><h2 className="mb-3 flex items-center gap-2 font-semibold"><Users className="h-4 w-4" />Colaboradores</h2>{detail.collaborators.map(collaborator => <div key={collaborator.collaborator_id} className="space-y-2 border-t py-3 text-xs first:border-0"><p className="font-mono">{collaborator.user_reference}</p>{canManageCollaborators ? <><select aria-label={`Papel de ${collaborator.user_reference}`} value={collaborator.role} disabled={busy} onChange={event => void updateCollaborator(collaborator.collaborator_id, event.target.value as DashboardCollaboratorRoleV2, collaborator.lock_version)} className="w-full rounded border bg-transparent px-2 py-1">{COLLABORATOR_ROLES.map(role => <option key={role}>{role}</option>)}</select><button type="button" disabled={!confirmation || busy} onClick={() => void removeCollaborator(collaborator.collaborator_id, collaborator.lock_version)} className="rounded border px-2 py-1">Remover colaborador</button></> : <p>{collaborator.role} · lock {collaborator.lock_version}</p>}</div>)}{!detail.collaborators.length && <p className="text-xs text-[rgb(var(--text-muted))]">Lista não disponível para este papel.</p>}{canManageCollaborators && <div className="mt-3 grid gap-2 border-t pt-3"><input aria-label="Referência do novo colaborador" value={newUser} onChange={event => setNewUser(event.target.value)} className="rounded border bg-transparent px-2 py-1" /><select aria-label="Papel do novo colaborador" value={newRole} onChange={event => setNewRole(event.target.value as DashboardCollaboratorRoleV2)} className="rounded border bg-transparent px-2 py-1">{COLLABORATOR_ROLES.map(role => <option key={role}>{role}</option>)}</select><button type="button" disabled={!newUser.trim() || busy} onClick={() => void addCollaborator()} className="rounded border px-2 py-1">Adicionar colaborador</button></div>}</section>
            <section className="space-y-3 rounded-xl bg-amber-500/10 p-4 text-xs"><strong>Lifecycle humano</strong><textarea aria-label="Justificativa da decisão" value={comment} onChange={event => setComment(event.target.value)} className="w-full rounded border bg-transparent px-2 py-1" /><input aria-label="Próxima versão de publicação" value={publicationVersion} onChange={event => setPublicationVersion(event.target.value)} className="w-full rounded border bg-transparent px-2 py-1" /><label className="flex gap-2"><input type="checkbox" checked={confirmation} onChange={event => setConfirmation(event.target.checked)} />Confirmo a ação selecionada</label><div className="grid gap-2">{detail.effective_capabilities.includes('dashboard:review') && <button type="button" onClick={() => void lifecycle('CHANGES')} disabled={!confirmation || busy} className="rounded border px-2 py-1">Solicitar alterações</button>}{detail.effective_capabilities.includes('dashboard:approve') && <><button type="button" onClick={() => void lifecycle('APPROVE')} disabled={!confirmation || busy} className="rounded border px-2 py-1">Aprovar revisão</button><button type="button" onClick={() => void lifecycle('REJECT')} disabled={!confirmation || busy} className="rounded border px-2 py-1">Rejeitar revisão</button></>}{detail.effective_capabilities.includes('dashboard:publish') && <button type="button" onClick={() => void lifecycle('PUBLISH')} disabled={!confirmation || busy} className="rounded border px-2 py-1">Publicar revisão</button>}{detail.effective_capabilities.includes('dashboard:rollback') && <button type="button" onClick={() => void lifecycle('ROLLBACK')} disabled={!confirmation || busy} className="rounded border px-2 py-1">Criar rollback</button>}</div><p>Review, approval, publication, rollback e colaboradores exigem capability e CAS. O side chat não executa estas ações.</p></section>
          </aside>
        </div>
        {message && <p role="status" className="mt-5 rounded-xl border p-3 text-sm">{message}</p>}
      </div>
    </main>
  )
}
