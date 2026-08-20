'use client'

import { useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { AlertTriangle, ArrowLeft, Bot, Check, FileCheck2, ShieldCheck, Square, X } from 'lucide-react'
import { DashboardWidgetRenderer } from '@/components/dashboard-v2/DashboardWidgetRenderer'
import {
  answerDashboardAiClarification,
  applyDashboardAiProposal,
  cancelDashboardAiProposal,
  createDashboardAiProposal,
  DashboardAiApiErrorV2,
  decideDashboardAiProposal,
  getDashboardAiProposal,
  reviseDashboardAiProposal,
} from '@/lib/dashboard-ai/client'
import { dashboardAiAllowsApply } from '@/lib/dashboard-ai/config'
import type { DashboardAiAssistanceModeV2, DashboardAiProposalV2 } from '@/types/dashboard_ai_assistance_v2'

const STATUS_LABEL: Readonly<Record<string, string>> = {
  RECEIVED: 'Solicitação recebida', ANALYZING: 'Analisando intenção', NEEDS_CLARIFICATION: 'Aguardando esclarecimento',
  RESOLVING: 'Resolvendo referências canônicas', SYNTHESIZING: 'Sintetizando estrutura', VALIDATING: 'Validando Blueprint V2',
  READY_FOR_REVIEW: 'Pronta para revisão humana', ACCEPTED: 'Aceita; aplicação separada necessária', APPLIED: 'DRAFT criado',
  REJECTED: 'Proposta rejeitada', CANCELLED: 'Proposta cancelada', BLOCKED: 'Proposta bloqueada', FAILED: 'Falha governada',
}

export function DashboardAiCreationWizard({ mode, targetDashboardId, targetRevisionId, editKind, origin = 'CREATION_WIZARD' }: { readonly mode: DashboardAiAssistanceModeV2; readonly targetDashboardId?: string; readonly targetRevisionId?: string; readonly editKind?: 'visual' | 'semantic'; readonly origin?: 'CREATION_WIZARD' | 'DASHBOARD_EDITOR' | 'SIDE_CHAT' }) {
  const router = useRouter()
  const [objective, setObjective] = useState(editKind === 'visual' ? 'Novo título executivo para este dashboard' : editKind === 'semantic' ? 'Alterar a métrica principal para ticket médio' : 'Criar dashboard de ticket médio por mês em julho')
  const [audience, setAudience] = useState('gestão')
  const [period, setPeriod] = useState('último mês fechado')
  const [dimensions, setDimensions] = useState('mês')
  const [visual, setVisual] = useState('visão executiva compacta')
  const [proposal, setProposal] = useState<DashboardAiProposalV2>()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const controllerRef = useRef<AbortController | undefined>(undefined)
  const generationRef = useRef(0)

  const instruction = `${objective}. Público: ${audience}. Período: ${period}. Dimensões: ${dimensions}. Preferência visual: ${visual}.`
  const run = async () => {
    controllerRef.current?.abort('STALE_DASHBOARD_AI_REQUEST')
    const controller = new AbortController(); controllerRef.current = controller
    const generation = ++generationRef.current
    setBusy(true); setMessage('')
    try {
      const operation = editKind === 'visual' ? 'PROPOSE_VISUAL_CHANGE' : editKind === 'semantic' ? 'PROPOSE_SEMANTIC_CHANGE' : 'CREATE_DASHBOARD'
      const result = await createDashboardAiProposal({
        operation, origin, instruction,
        context: { locale: 'pt-BR', timezone: 'America/Sao_Paulo', ...(targetDashboardId ? { target_dashboard_id: targetDashboardId } : {}), ...(targetRevisionId ? { target_revision_id: targetRevisionId } : {}) }, client_request_id: crypto.randomUUID(),
      }, crypto.randomUUID(), controller.signal)
      if (generation === generationRef.current && !controller.signal.aborted) setProposal(result)
    } catch (error) {
      if (!controller.signal.aborted && generation === generationRef.current) setMessage(error instanceof DashboardAiApiErrorV2 ? error.message : 'A proposta não pôde ser criada.')
    } finally { if (generation === generationRef.current) setBusy(false) }
  }
  const answer = async (questionId: string, optionId: string, lock: number) => {
    if (!proposal) return
    setBusy(true)
    try { setProposal(await answerDashboardAiClarification(proposal.proposal_id, questionId, [optionId], lock)) }
    catch (error) { setMessage(error instanceof DashboardAiApiErrorV2 ? error.message : 'O esclarecimento não foi aceito.') }
    finally { setBusy(false) }
  }
  const decide = async (decision: 'accept' | 'reject') => {
    if (!proposal) return
    setBusy(true)
    try {
      await decideDashboardAiProposal(proposal, decision, decision === 'accept' ? 'Confirmo esta versão da proposta.' : 'Rejeito esta versão da proposta.', crypto.randomUUID())
      setProposal(await getDashboardAiProposal(proposal.proposal_id))
    } catch (error) { setMessage(error instanceof DashboardAiApiErrorV2 ? error.message : 'A decisão não foi registrada.') }
    finally { setBusy(false) }
  }
  const revise = async () => {
    if (!proposal) return
    setBusy(true); setMessage('')
    try { setProposal(await reviseDashboardAiProposal(proposal, instruction, crypto.randomUUID())) }
    catch (error) { setMessage(error instanceof DashboardAiApiErrorV2 ? error.message : 'A nova versão da proposta não foi criada.') }
    finally { setBusy(false) }
  }
  const apply = async () => {
    if (!proposal) return
    setBusy(true)
    try {
      const result = await applyDashboardAiProposal(proposal, crypto.randomUUID())
      setProposal(await getDashboardAiProposal(proposal.proposal_id))
      setMessage('DRAFT criado. Nenhuma publicação ou aprovação foi realizada.')
      router.prefetch(`/dashboard/v2/${encodeURIComponent(result.dashboard_id)}/edit`)
    } catch (error) { setMessage(error instanceof DashboardAiApiErrorV2 ? error.message : 'A proposta aceita não foi aplicada.') }
    finally { setBusy(false) }
  }
  const cancel = async () => {
    if (!proposal) { controllerRef.current?.abort('USER_CANCELLED'); generationRef.current += 1; setBusy(false); return }
    setBusy(true)
    try { setProposal(await cancelDashboardAiProposal(proposal)) }
    catch (error) { setMessage(error instanceof DashboardAiApiErrorV2 ? error.message : 'Não foi possível cancelar.') }
    finally { setBusy(false) }
  }

  const latest = proposal?.latest
  const blueprint = latest?.blueprint_proposal?.blueprint
  const patch = latest?.semantic_proposal?.patch ?? latest?.visual_proposal?.patch
  return (
    <main className="min-h-screen bg-[rgb(var(--bg-base))] px-4 py-8 text-[rgb(var(--text-primary))] sm:px-8" data-testid="dashboard-ai-wizard">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex items-start gap-4"><Link href="/dashboard/v2" aria-label="Voltar à biblioteca" className="mt-1 rounded-lg border p-2"><ArrowLeft /></Link><div><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-violet-500"><Bot className="h-4 w-4" />Assistência governada · {mode}</div><h1 className="mt-2 text-3xl font-semibold">Criar dashboard com IA</h1><p className="mt-2 max-w-3xl text-sm text-[rgb(var(--text-muted))]">A IA interpreta a intenção. Métricas, dimensões, período, Blueprint, checksums e patches são resolvidos e sintetizados por autoridades determinísticas. A aplicação exige confirmação humana e cria somente DRAFT.</p></div></header>
        <div className="grid gap-6 lg:grid-cols-[minmax(300px,0.75fr)_minmax(0,1.5fr)]">
          <form onSubmit={event => { event.preventDefault(); void run() }} className="space-y-4 rounded-2xl border border-[rgb(var(--border))] bg-[rgb(var(--bg-surface))] p-5" aria-label="Objetivo do dashboard assistido">
            <h2 className="font-semibold">1. Descreva a intenção</h2>
            <label className="grid gap-1 text-sm">Objetivo<textarea value={objective} onChange={event => setObjective(event.target.value)} maxLength={2000} rows={5} className="rounded-xl border bg-transparent p-3" /></label>
            <label className="grid gap-1 text-sm">Público<input value={audience} onChange={event => setAudience(event.target.value)} maxLength={120} className="rounded-xl border bg-transparent p-3" /></label>
            <label className="grid gap-1 text-sm">Período<input value={period} onChange={event => setPeriod(event.target.value)} maxLength={120} className="rounded-xl border bg-transparent p-3" /></label>
            <label className="grid gap-1 text-sm">Dimensões<input value={dimensions} onChange={event => setDimensions(event.target.value)} maxLength={160} className="rounded-xl border bg-transparent p-3" /></label>
            <label className="grid gap-1 text-sm">Preferência visual<input value={visual} onChange={event => setVisual(event.target.value)} maxLength={160} className="rounded-xl border bg-transparent p-3" /></label>
            <div className="flex gap-2"><button type="submit" disabled={busy} className="flex-1 rounded-xl bg-violet-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60">Gerar proposta</button>{busy && <button type="button" onClick={() => void cancel()} className="rounded-xl border px-3" aria-label="Cancelar geração"><Square className="h-4 w-4" /></button>}</div>
            <p className="text-xs text-[rgb(var(--text-muted))]">O texto bruto não é persistido; o backend mantém apenas fingerprint e intenção normalizada. Sem SQL, Oracle ou consulta analítica.</p>
          </form>
          <section className="min-w-0 space-y-5" aria-label="Revisão da proposta">
            {!proposal && <div className="grid min-h-80 place-items-center rounded-2xl border border-dashed border-[rgb(var(--border))] p-8 text-center text-sm text-[rgb(var(--text-muted))]"><div><ShieldCheck className="mx-auto mb-3 h-10 w-10 text-violet-500" />A proposta aparecerá aqui com evidências, riscos, checksums e preview estrutural — nunca com números simulados.</div></div>}
            {proposal && <>
              <div className="rounded-2xl border border-violet-500/30 bg-violet-500/10 p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold">2. Estado da proposta</h2><p className="mt-1 text-sm">{STATUS_LABEL[proposal.status] ?? proposal.status}</p></div><span className="rounded-full border px-3 py-1 font-mono text-xs">v{proposal.current_version} · CAS {proposal.lock_version}</span></div></div>
              {proposal.status === 'READY_FOR_REVIEW' && <div className="relative z-20 flex flex-wrap justify-end gap-2 bg-[rgb(var(--bg-base))] py-2"><button type="button" disabled={busy} onClick={() => void revise()} className="rounded-xl border px-4 py-2 text-sm">Gerar nova versão</button><button type="button" disabled={busy} onClick={() => void decide('reject')} className="rounded-xl border px-4 py-2 text-sm"><X className="mr-1 inline h-4 w-4" />Rejeitar</button><button type="button" disabled={busy} onClick={() => void decide('accept')} className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white"><Check className="mr-1 inline h-4 w-4" />Aceitar esta versão</button></div>}
              {proposal.status === 'ACCEPTED' && <div className="relative z-20 rounded-2xl border border-emerald-500/40 bg-[rgb(var(--bg-surface))] p-5"><h3 className="font-semibold">4. Aplicação separada</h3><p className="mt-1 text-sm">O aceite não alterou nenhum dashboard. Confirme novamente para criar o DRAFT.</p>{dashboardAiAllowsApply(mode) ? <button type="button" disabled={busy} onClick={() => void apply()} className="mt-4 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white">Confirmar e criar DRAFT</button> : <p className="mt-3 text-xs">Este modo permite somente preview.</p>}</div>}
              {proposal.clarification?.questions.map(question => <div key={question.question_id} className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-5" data-testid="dashboard-ai-clarification"><h3 className="font-semibold">Esclarecimento obrigatório</h3><p className="mt-2 text-sm">{question.prompt}</p><div className="mt-4 grid gap-2 sm:grid-cols-2">{question.options.map(option => <button type="button" disabled={busy} key={option.option_id} onClick={() => void answer(question.question_id, option.option_id, proposal.clarification!.lock_version)} className="rounded-xl border bg-[rgb(var(--bg-surface))] p-3 text-left text-sm"><strong>{option.label}</strong><span className="mt-1 block text-xs text-[rgb(var(--text-muted))]">{option.description}</span></button>)}</div></div>)}
              {latest && <div className="grid gap-4 xl:grid-cols-2"><article className="rounded-2xl border p-5"><h3 className="font-semibold">Racional público</h3><p className="mt-2 text-sm">{latest.rationale.summary}</p><ul className="mt-3 list-disc space-y-1 pl-5 text-xs">{latest.rationale.decisions.map(item => <li key={item}>{item}</li>)}</ul><p className="mt-3 text-[11px] text-[rgb(var(--text-muted))]">{latest.rationale.omitted_details_notice}</p></article><article className="rounded-2xl border p-5"><h3 className="font-semibold">Evidências e riscos</h3><div className="mt-3 space-y-2">{latest.evidence.map(item => <div key={item.evidence_id} className="rounded-lg bg-[rgb(var(--bg-elevated))] p-2 text-xs"><FileCheck2 className="mr-1 inline h-3.5 w-3.5 text-emerald-500" />{item.public_label}<span className="block font-mono text-[10px] text-[rgb(var(--text-muted))]">{item.canonical_reference} · {item.authority_version}</span></div>)}{latest.risks.map(item => <p key={item.code} className="rounded-lg bg-red-500/10 p-2 text-xs"><AlertTriangle className="mr-1 inline h-3.5 w-3.5" />{item.severity}: {item.message}</p>)}{latest.warnings.map(item => <p key={item.code} className="rounded-lg bg-amber-500/10 p-2 text-xs">{item.message}</p>)}</div></article></div>}
              {blueprint && <article className="pointer-events-none rounded-2xl border p-5" data-testid="dashboard-ai-blueprint-preview"><h3 className="font-semibold">3. Preview estrutural</h3><p className="mt-1 text-xs text-[rgb(var(--text-muted))]">Placeholders do renderer certificado do Prompt 21. Nenhum valor empresarial foi consultado ou inventado.</p><div className="mt-4 grid gap-4 sm:grid-cols-2">{blueprint.widgets.map(widget => <DashboardWidgetRenderer key={widget.identity.widget_id} widget={widget} />)}</div><dl className="mt-4 grid gap-2 text-[11px] sm:grid-cols-3"><div><dt>Blueprint</dt><dd className="truncate font-mono">{latest?.blueprint_proposal?.blueprint_checksum}</dd></div><div><dt>Semântico</dt><dd className="truncate font-mono">{latest?.blueprint_proposal?.semantic_checksum}</dd></div><div><dt>Visual</dt><dd className="truncate font-mono">{latest?.blueprint_proposal?.visual_checksum}</dd></div></dl></article>}
              {patch && <article className="rounded-2xl border p-5"><h3 className="font-semibold">Diff proposto</h3><pre className="mt-3 max-h-72 overflow-auto rounded-xl bg-black/80 p-4 text-xs text-white">{JSON.stringify(patch.operations, null, 2)}</pre></article>}
              {proposal.status === 'APPLIED' && proposal.applied_dashboard_id && <Link href={`/dashboard/v2/${encodeURIComponent(proposal.applied_dashboard_id)}/edit`} className="inline-flex rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white">Abrir DRAFT no editor</Link>}
            </>}
            {message && <p role="status" className="rounded-xl border p-3 text-sm">{message}</p>}
          </section>
        </div>
      </div>
    </main>
  )
}
