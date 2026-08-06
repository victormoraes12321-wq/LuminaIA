'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { Bot, Check, RotateCcw, Send, ShieldAlert, Square, X } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { parseDashboardSideChatActionV2 } from '@/lib/dashboard-v2/actionValidator'
import {
  applyVisualPatchV2,
  askDashboardSideChatV2,
  createDashboardIdempotencyKey,
  DashboardApiErrorV2,
} from '@/lib/dashboard-v2/client'
import { dashboardVisualUpdateInterceptor } from '@/lib/dashboard-v2/visualUpdateInterceptor'
import { emitDashboardTelemetryV2 } from '@/lib/dashboard-v2/telemetry'
import { dashboardAiAllowsEdit, getPublicDashboardAiMode } from '@/lib/dashboard-ai/config'
import type {
  DashboardDetailResponseV2,
  DashboardRevisionRecordV2,
  DashboardRuntimeResultV2,
} from '@/types/dashboard_backend_v2'
import type {
  DashboardFilterStateV2,
  DashboardSideChatActionResultV2,
  DashboardSideChatMessageV2,
  DashboardSideChatModeV2,
  DashboardSideChatStreamStatusV2,
  DashboardUiModeV2,
} from '@/types/dashboard_ui_sidechat_v2'

interface DashboardSideChatPanelProps {
  readonly open: boolean
  readonly mode: DashboardUiModeV2
  readonly detail: DashboardDetailResponseV2
  readonly runtime?: DashboardRuntimeResultV2
  readonly selectedWidgetId?: string
  readonly filters: readonly DashboardFilterStateV2[]
  readonly onClose: () => void
  readonly onFocusWidget: (widgetId: string) => void
  readonly onOpenProvenance: (widgetId?: string) => void
  readonly onApplyFilter: (filterId: string, values: readonly (string | number | boolean)[]) => void
  readonly onResetFilters: () => void
  readonly onDrilldown: (interactionId: string, sourceWidgetId: string, canonicalValue: string) => void
  readonly onRevisionChanged: (revision: DashboardRevisionRecordV2, outcome: DashboardSideChatActionResultV2) => void
}

function messageId(): string {
  return globalThis.crypto.randomUUID()
}

const STREAM_STATUS_LABEL: Readonly<Record<DashboardSideChatStreamStatusV2, string>> = {
  IDLE: 'Pronto',
  CONNECTING: 'Conectando',
  RECEIVING: 'Recebendo resposta',
  COMPLETE: 'Envelope completo',
  CANCELLED: 'Cancelado',
  FAILED: 'Falha não repetível',
  RETRYABLE: 'Falha repetível',
  ACTION_PENDING: 'Ação aguardando confirmação',
  ACTION_CONFIRMED: 'Ação confirmada',
}

export function DashboardSideChatPanel(props: DashboardSideChatPanelProps) {
  const { user } = useAuth()
  const revision = props.detail.head_revision
  const blueprint = revision?.blueprint
  const [chatMode, setChatMode] = useState<DashboardSideChatModeV2>('ASK')
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<readonly DashboardSideChatMessageV2[]>([])
  const [busy, setBusy] = useState(false)
  const [streamStatus, setStreamStatus] = useState<DashboardSideChatStreamStatusV2>('IDLE')
  const [streamHistory, setStreamHistory] = useState<readonly DashboardSideChatStreamStatusV2[]>([])
  const [lastQuestion, setLastQuestion] = useState('')
  const [pendingResult, setPendingResult] = useState<DashboardSideChatActionResultV2 | undefined>()
  const [pendingSummary, setPendingSummary] = useState('')
  const controllerRef = useRef<AbortController | null>(null)
  const generationRef = useRef(0)
  const [sessionId, setSessionId] = useState(() => messageId())
  const aiEditEnabled = dashboardAiAllowsEdit(getPublicDashboardAiMode())

  const context = useMemo(() => {
    if (!blueprint || !revision) return undefined
    return {
      contract_version: 'lumina.dashboard-ui-sidechat/1.0' as const,
      dashboard_id: props.detail.dashboard.identity.dashboard_id,
      publication_id: props.detail.active_publication?.publication_id,
      revision_id: revision.revision_id,
      blueprint_semantic_checksum: revision.semantic.checksum,
      visible_widget_ids: blueprint.widgets.filter(widget => widget.visible).map(widget => widget.identity.widget_id),
      selected_widget_id: props.selectedWidgetId,
      binding_ids: blueprint.data_bindings.map(binding => binding.binding_id),
      metric_ids: blueprint.data_bindings.flatMap(binding => binding.metrics.map(metric => metric.metric_id)),
      dimension_ids: blueprint.data_bindings.flatMap(binding => binding.dimensions.map(dimension => dimension.dimension_id)),
      filters: props.filters.map(filter => ({ filter_id: filter.filter_id, values: filter.runtime_confirmed })),
      public_provenance_references: props.runtime?.provenance.metric_definition_references ?? [],
      certification_references: props.runtime?.widgets.flatMap(widget => widget.certification_reference ? [widget.certification_reference] : []) ?? [],
      conversation_session_id: sessionId,
      context_version: 0,
    }
  }, [blueprint, props.detail.active_publication?.publication_id, props.detail.dashboard.identity.dashboard_id, props.filters, props.runtime, props.selectedWidgetId, revision, sessionId])

  useEffect(() => {
    return () => controllerRef.current?.abort()
  }, [])

  if (!props.open) return null

  const appendAssistant = (content: string) => setMessages(current => [...current, { message_id: messageId(), role: 'ASSISTANT', content, created_at: new Date().toISOString() }])

  const transitionStream = (status: DashboardSideChatStreamStatusV2) => {
    setStreamStatus(status)
    setStreamHistory(current => current[current.length - 1] === status ? current : [...current, status])
  }

  const handleAction = (rawAction: unknown): 'CONFIRMED' | 'PENDING' | 'NO_ACTION' | 'INVALID' => {
    if (!revision) return 'INVALID'
    const action = parseDashboardSideChatActionV2(rawAction)
    if (!action) {
      if (rawAction !== undefined) appendAssistant('A ação retornada não passou pelo contrato fechado e não foi executada.')
      return rawAction === undefined ? 'NO_ACTION' : 'INVALID'
    }
    if (action.action_type === 'FOCUS_WIDGET') {
      if (blueprint?.widgets.some(widget => widget.identity.widget_id === action.widget_id)) {
        props.onFocusWidget(action.widget_id)
        return 'CONFIRMED'
      }
      appendAssistant('O widget solicitado não pertence à revisão ativa.')
      return 'INVALID'
    }
    if (action.action_type === 'OPEN_PROVENANCE') {
      if (!action.widget_id || blueprint?.widgets.some(widget => widget.identity.widget_id === action.widget_id)) {
        props.onOpenProvenance(action.widget_id)
        return 'CONFIRMED'
      }
      appendAssistant('O widget solicitado não pertence à revisão ativa.')
      return 'INVALID'
    }
    if (action.action_type === 'APPLY_FILTER') {
      const filter = blueprint?.filters.find(candidate => candidate.filter_id === action.filter_id)
      if (filter && action.values.length <= filter.maximum_selections) {
        props.onApplyFilter(action.filter_id, action.values)
        return 'CONFIRMED'
      }
      appendAssistant('O filtro retornado não é permitido pelo blueprint ativo.')
      return 'INVALID'
    }
    if (action.action_type === 'RESET_FILTERS') { props.onResetFilters(); return 'CONFIRMED' }
    if (action.action_type === 'DRILLDOWN') {
      const interaction = blueprint?.interactions.find(candidate => candidate.interaction_type === 'DRILLDOWN' && candidate.enabled && candidate.interaction_id === action.interaction_id && candidate.source_widget_id === action.source_widget_id)
      if (interaction) {
        props.onDrilldown(action.interaction_id, action.source_widget_id, action.canonical_value)
        return 'CONFIRMED'
      }
      appendAssistant('O drilldown solicitado não pertence ao blueprint ativo.')
      return 'INVALID'
    }
    if (action.action_type === 'BLOCKED') { appendAssistant(action.message); return 'CONFIRMED' }
    if (action.action_type === 'VISUAL_PATCH_PROPOSAL' || action.action_type === 'VISUAL_PATCH_APPLY') {
      const result = dashboardVisualUpdateInterceptor({
        action,
        dashboard_id: props.detail.dashboard.identity.dashboard_id,
        revision,
        capabilities: props.detail.effective_capabilities,
        mode: props.mode,
      })
      setPendingResult(result)
      setPendingSummary(action.summary)
      if (!result.preview_patch) appendAssistant(result.message)
      return result.preview_patch ? 'PENDING' : result.outcome === 'NO_OP' ? 'CONFIRMED' : 'INVALID'
    }
    if (action.action_type === 'NO_ACTION') return 'NO_ACTION'
    appendAssistant('Ação reconhecida, mas disponível apenas no fluxo governado correspondente.')
    return 'CONFIRMED'
  }

  const submit = async (submittedQuestion = question) => {
    const trimmed = submittedQuestion.trim()
    if (!trimmed || !context || !user || busy) return
    const generation = ++generationRef.current
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    setMessages(current => [...current, { message_id: messageId(), role: 'USER', content: trimmed, created_at: new Date().toISOString() }])
    setQuestion('')
    setLastQuestion(trimmed)
    setBusy(true)
    setStreamHistory(['CONNECTING'])
    setStreamStatus('CONNECTING')
    try {
      const response = await askDashboardSideChatV2(trimmed, chatMode, context, user.tenant_id, controller.signal, {
        onReceiving: () => {
          if (generation === generationRef.current && !controller.signal.aborted) transitionStream('RECEIVING')
        },
      })
      if (generation !== generationRef.current || controller.signal.aborted) return
      transitionStream('COMPLETE')
      const text = response.resposta_direta ?? response.ia_analise ?? response.mensagem ?? 'Resposta recebida sem conteúdo público.'
      appendAssistant(text)
      const actionResult = handleAction(response.dashboard_action)
      if (actionResult === 'PENDING') transitionStream('ACTION_PENDING')
      else if (actionResult === 'CONFIRMED') {
        transitionStream('ACTION_PENDING')
        transitionStream('ACTION_CONFIRMED')
      }
      else if (actionResult === 'INVALID') transitionStream('FAILED')
    } catch (error) {
      if (controller.signal.aborted) {
        transitionStream('CANCELLED')
        return
      }
      const retryable = !(error instanceof DashboardApiErrorV2) || error.status === 408 || error.status === 429 || error.status >= 500
      transitionStream(retryable ? 'RETRYABLE' : 'FAILED')
      appendAssistant(error instanceof DashboardApiErrorV2 ? error.message : 'Side chat indisponível. Nenhuma ação foi aplicada.')
    } finally {
      if (generation === generationRef.current) setBusy(false)
    }
  }

  const confirmVisualPatch = async () => {
    if (!pendingResult?.preview_patch || !revision) return
    const controller = new AbortController()
    controllerRef.current = controller
    setBusy(true)
    transitionStream('ACTION_PENDING')
    try {
      const backendRevision = await applyVisualPatchV2(
        props.detail.dashboard.identity.dashboard_id,
        pendingResult.preview_patch,
        props.detail.dashboard.lock_version,
        revision.lock_version,
        pendingSummary || 'Ajuste visual confirmado no side chat',
        createDashboardIdempotencyKey(),
        controller.signal,
      )
      const structuredAction = parseDashboardSideChatActionV2({
        action_type: 'VISUAL_PATCH_APPLY',
        dashboard_id: props.detail.dashboard.identity.dashboard_id,
        revision_id: revision.revision_id,
        semantic_checksum: revision.semantic.checksum,
        operations: pendingResult.preview_patch.operations,
        summary: pendingSummary,
      })
      if (!structuredAction) throw new Error('Ação visual local inválida.')
      const outcome = dashboardVisualUpdateInterceptor({ action: structuredAction, dashboard_id: props.detail.dashboard.identity.dashboard_id, revision, capabilities: props.detail.effective_capabilities, mode: props.mode, backend_revision: backendRevision })
      if (outcome.outcome === 'UI_MODIFIED') {
        props.onRevisionChanged(backendRevision, outcome)
        emitDashboardTelemetryV2({ event: 'DASHBOARD_SIDE_CHAT_UI_MODIFIED', dashboard_id: props.detail.dashboard.identity.dashboard_id, operation_count: pendingResult.preview_patch.operations.length })
      }
      appendAssistant(outcome.message)
      setPendingResult(undefined)
      transitionStream(outcome.outcome === 'UI_MODIFIED' ? 'ACTION_CONFIRMED' : 'FAILED')
    } catch (error) {
      if (controller.signal.aborted) {
        transitionStream('CANCELLED')
        return
      }
      const retryable = !(error instanceof DashboardApiErrorV2) || error.status === 408 || error.status === 429 || error.status >= 500
      transitionStream(retryable ? 'RETRYABLE' : 'FAILED')
      appendAssistant(error instanceof DashboardApiErrorV2 ? error.message : 'O patch visual não foi persistido.')
    } finally {
      setBusy(false)
    }
  }

  const cancelActiveRequest = () => {
    controllerRef.current?.abort('DASHBOARD_SIDE_CHAT_CANCELLED')
    generationRef.current += 1
    setBusy(false)
    transitionStream('CANCELLED')
    emitDashboardTelemetryV2({ event: 'DASHBOARD_SIDE_CHAT_CANCELLED', dashboard_id: props.detail.dashboard.identity.dashboard_id, reason_code: 'USER_CANCELLED' })
  }

  const resetSession = () => {
    controllerRef.current?.abort('DASHBOARD_SIDE_CHAT_SESSION_RESET')
    generationRef.current += 1
    setBusy(false)
    setMessages([])
    setPendingResult(undefined)
    setPendingSummary('')
    setLastQuestion('')
    setSessionId(messageId())
    setStreamHistory([])
    setStreamStatus('IDLE')
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 md:bg-transparent md:pointer-events-none">
      <aside role="dialog" aria-modal="true" aria-label="Side chat contextual do dashboard" className="pointer-events-auto flex h-full w-full flex-col border-l border-[rgb(var(--border))] bg-[rgb(var(--bg-surface))] shadow-2xl md:max-w-md" data-testid="dashboard-side-chat">
        <header className="flex items-center justify-between border-b border-[rgb(var(--border))] p-4"><div className="flex items-center gap-2"><Bot className="text-violet-500" /><div><h2 className="font-semibold">Side chat governado</h2><p className="text-[11px] text-[rgb(var(--text-muted))]">Contexto mínimo · sem SQL · sem publicação</p></div></div><div className="flex items-center gap-2"><button type="button" onClick={resetSession} aria-label="Reiniciar sessão do side chat"><RotateCcw className="h-4 w-4" /></button><button type="button" onClick={props.onClose} aria-label="Fechar side chat"><X /></button></div></header>
        <label className="border-b p-3 text-xs">Modo<select value={chatMode} onChange={event => setChatMode(event.target.value as DashboardSideChatModeV2)} className="ml-2 rounded-lg border bg-transparent px-2 py-1">{['ASK', 'EXPLAIN_WIDGET', 'EXPLAIN_VARIANCE', 'FILTER', 'NAVIGATE', 'VISUAL_EDIT'].map(value => <option value={value} key={value}>{value}</option>)}</select></label>
        {aiEditEnabled && revision && <div className="border-b p-3"><Link href={`/dashboard/v2/new?target=${encodeURIComponent(props.detail.dashboard.identity.dashboard_id)}&revision=${encodeURIComponent(revision.revision_id)}&kind=visual&origin=SIDE_CHAT`} onClick={props.onClose} className="block rounded-lg border border-violet-500/40 bg-violet-500/10 px-3 py-2 text-center text-xs font-semibold text-violet-500">Criar proposta visual assistida</Link><p className="mt-1 text-[10px] text-[rgb(var(--text-muted))]">Abre um workflow explícito; o side chat não aplica mudança sem confirmação.</p></div>}
        <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
          {!messages.length && <div className="rounded-xl bg-violet-500/10 p-4 text-sm"><ShieldAlert className="mb-2 text-violet-500" />Pergunte, peça explicações, filtros, foco ou ajustes exclusivamente visuais. Alterações semânticas, aprovação, publicação, rollback e colaboradores continuam humanos.</div>}
          {messages.map(message => <div key={message.message_id} className={`max-w-[90%] rounded-xl px-3 py-2 text-sm ${message.role === 'USER' ? 'ml-auto bg-violet-600 text-white' : 'bg-[rgb(var(--bg-elevated))]'}`}>{message.content}</div>)}
          <p role="status" data-testid="dashboard-side-chat-stream-status" data-stream-status={streamStatus.toLowerCase().replaceAll('_', '-')} data-stream-history={streamHistory.join(',')} className="text-xs text-[rgb(var(--text-muted))]">{STREAM_STATUS_LABEL[streamStatus]}</p>
          {streamStatus === 'RETRYABLE' && !busy && <button type="button" onClick={() => void submit(lastQuestion)} className="rounded-lg border px-3 py-2 text-xs">Tentar novamente</button>}
          {pendingResult?.preview_patch && <div className="rounded-xl border border-violet-500/40 bg-violet-500/10 p-4 text-sm" data-testid="dashboard-visual-patch-preview"><h3 className="font-semibold">Preview visual</h3><p className="mt-1">{pendingSummary}</p><p className="mt-2 text-xs">{pendingResult.preview_patch.operations.length} operação(ões); checksum semântico preservado.</p><div className="mt-3 flex gap-2"><button type="button" disabled={busy} onClick={confirmVisualPatch} className="rounded-lg bg-violet-600 px-3 py-2 text-xs font-semibold text-white"><Check className="mr-1 inline h-3 w-3" />Confirmar</button><button type="button" onClick={() => { setPendingResult(undefined); transitionStream('CANCELLED') }} className="rounded-lg border px-3 py-2 text-xs">Descartar</button></div></div>}
        </div>
        <form className="border-t border-[rgb(var(--border))] p-4" onSubmit={event => { event.preventDefault(); void submit() }}><textarea value={question} onChange={event => setQuestion(event.target.value)} maxLength={1000} rows={3} className="w-full resize-none rounded-xl border border-[rgb(var(--border))] bg-transparent p-3 text-sm" placeholder="Pergunte sobre este dashboard…" /><div className="mt-2 flex justify-end">{busy ? <button type="button" onClick={cancelActiveRequest} className="rounded-lg border px-3 py-2 text-xs"><Square className="mr-1 inline h-3 w-3" />Cancelar</button> : <button type="submit" className="rounded-lg bg-violet-600 px-3 py-2 text-xs font-semibold text-white"><Send className="mr-1 inline h-3 w-3" />Enviar</button>}</div></form>
      </aside>
    </div>
  )
}
