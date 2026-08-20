'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/context/AuthContext'
import {
  createDashboardIdempotencyKey,
  DashboardApiErrorV2,
  executeDashboardV2,
  getDashboardV2,
} from '@/lib/dashboard-v2/client'
import { DashboardV2Shell } from './DashboardV2Shell'
import { DashboardSideChatPanel } from './DashboardSideChatPanel'
import { emitDashboardTelemetryV2 } from '@/lib/dashboard-v2/telemetry'
import type {
  DashboardDetailResponseV2,
  DashboardRevisionRecordV2,
  DashboardRuntimeResultV2,
} from '@/types/dashboard_backend_v2'
import type {
  DashboardFilterStateV2,
  DashboardInteractionStateV2,
  DashboardRuntimeInteractionRequestV2,
  DashboardSideChatActionResultV2,
  DashboardUiModeV2,
} from '@/types/dashboard_ui_sidechat_v2'

function initialFilterStates(detail: DashboardDetailResponseV2): readonly DashboardFilterStateV2[] {
  return detail.head_revision?.blueprint.filters.map(filter => ({
    filter_id: filter.filter_id,
    filter_type: filter.filter_type,
    blueprint_default: filter.default.canonical_values,
    effective_server: [],
    local_draft: filter.default.canonical_values,
    submitted: [],
    runtime_confirmed: [],
    status: 'CLEAN',
  })) ?? []
}

export function DashboardRuntimePage({ dashboardId, mode }: { readonly dashboardId: string; readonly mode: DashboardUiModeV2 }) {
  const { user } = useAuth()
  const [detail, setDetail] = useState<DashboardDetailResponseV2 | undefined>()
  const [runtime, setRuntime] = useState<DashboardRuntimeResultV2 | undefined>()
  const [filters, setFilters] = useState<readonly DashboardFilterStateV2[]>([])
  const [screen, setScreen] = useState<'LOADING' | 'READY' | 'NOT_FOUND' | 'ERROR'>('LOADING')
  const [message, setMessage] = useState('')
  const [runtimeLoading, setRuntimeLoading] = useState(false)
  const [selectedWidgetId, setSelectedWidgetId] = useState<string | undefined>()
  const [sideChatOpen, setSideChatOpen] = useState(false)
  const [interactionState, setInteractionState] = useState<DashboardInteractionStateV2>({ kind: 'IDLE' })
  const [drilldownBreadcrumb, setDrilldownBreadcrumb] = useState<readonly string[]>([])
  const [provenanceRequest, setProvenanceRequest] = useState<{ readonly key: number; readonly widget_id?: string }>()
  const detailController = useRef<AbortController | null>(null)
  const runtimeController = useRef<AbortController | null>(null)
  const runtimeGeneration = useRef(0)

  const runRuntime = useCallback(async (
    activeDetail: DashboardDetailResponseV2,
    activeFilters: readonly DashboardFilterStateV2[],
    activeInteractions: readonly DashboardRuntimeInteractionRequestV2[] = [],
  ) => {
    if (!activeDetail.active_publication || !activeDetail.effective_capabilities.includes('dashboard:execute')) return
    const generation = ++runtimeGeneration.current
    runtimeController.current?.abort()
    const controller = new AbortController()
    runtimeController.current = controller
    setRuntimeLoading(true)
    try {
      const result = await executeDashboardV2(activeDetail.dashboard.identity.dashboard_id, {
        publication_id: activeDetail.active_publication.publication_id,
        blueprint_checksum: activeDetail.active_publication.revision.blueprint_checksum,
        filters: activeFilters.flatMap(filter => filter.local_draft.length ? [{ filter_id: filter.filter_id, values: filter.local_draft }] : []),
        interactions: activeInteractions.map(interaction => ({
          interaction_id: interaction.interaction_id,
          action: interaction.action,
          source_widget_id: interaction.source_widget_id,
          ...(interaction.target_widget_id ? { target_widget_id: interaction.target_widget_id } : {}),
        })),
        requested_widget_ids: [],
        deadline_ms: 15_000,
        allow_partial: true,
      }, createDashboardIdempotencyKey(), controller.signal)
      if (generation !== runtimeGeneration.current || controller.signal.aborted) return
      setRuntime(result)
      setFilters(current => current.map(filter => ({ ...filter, effective_server: filter.local_draft, submitted: filter.local_draft, runtime_confirmed: filter.local_draft, status: 'APPLIED' })))
      if (activeInteractions[0]) setInteractionState({ kind: 'APPLIED', interaction_id: activeInteractions[0].interaction_id })
    } catch (error) {
      if (controller.signal.aborted) return
      setMessage(error instanceof DashboardApiErrorV2 ? error.message : 'O runtime governado está indisponível.')
      if (activeInteractions[0]) setInteractionState({ kind: 'FAILED', interaction_id: activeInteractions[0].interaction_id, message: error instanceof DashboardApiErrorV2 ? error.message : 'Interação recusada pelo runtime governado.' })
    } finally {
      if (generation === runtimeGeneration.current) setRuntimeLoading(false)
    }
  }, [])

  const load = useCallback(() => {
    detailController.current?.abort()
    runtimeController.current?.abort()
    const controller = new AbortController()
    detailController.current = controller
    setScreen('LOADING')
    setMessage('')
    getDashboardV2(dashboardId, controller.signal).then(result => {
      if (controller.signal.aborted) return
      if (!result.effective_capabilities.includes('dashboard:view')) {
        setScreen('NOT_FOUND')
        return
      }
      const nextFilters = initialFilterStates(result)
      setDetail(result)
      setFilters(nextFilters)
      setScreen('READY')
      void runRuntime(result, nextFilters)
    }).catch(error => {
      if (controller.signal.aborted) return
      if (error instanceof DashboardApiErrorV2 && (error.status === 403 || error.status === 404)) {
        setScreen('NOT_FOUND')
      } else {
        setScreen('ERROR')
        setMessage(error instanceof DashboardApiErrorV2 ? error.message : 'Não foi possível carregar o dashboard.')
      }
    })
  }, [dashboardId, runRuntime])

  useEffect(() => {
    void Promise.resolve().then(load)
    emitDashboardTelemetryV2({ event: 'DASHBOARD_UI_OPENED', dashboard_id: dashboardId, mode })
    return () => {
      detailController.current?.abort()
      runtimeController.current?.abort()
      runtimeGeneration.current += 1
      emitDashboardTelemetryV2({ event: 'DASHBOARD_UI_CLOSED', dashboard_id: dashboardId, mode })
    }
  }, [dashboardId, load, mode, user?.id, user?.tenant_id])

  if (screen === 'LOADING') return <div className="grid min-h-screen place-items-center bg-[rgb(var(--bg-base))]" role="status">Carregando dashboard governado…</div>
  if (screen === 'NOT_FOUND') return <div className="grid min-h-screen place-items-center bg-[rgb(var(--bg-base))] p-6 text-center"><div><h1 className="text-2xl font-semibold">Dashboard não encontrado</h1><p className="mt-2 text-sm text-[rgb(var(--text-muted))]">O recurso não existe ou não está disponível para esta sessão.</p><Link href="/dashboard/v2" className="mt-5 inline-block rounded-lg bg-violet-600 px-4 py-2 text-sm text-white">Voltar à biblioteca</Link></div></div>
  if (screen === 'ERROR' || !detail) return <div className="grid min-h-screen place-items-center p-6"><div role="alert" className="max-w-md rounded-2xl border border-red-500/40 bg-red-500/10 p-6"><h1 className="font-semibold">Falha ao carregar</h1><p className="mt-2 text-sm">{message}</p><button type="button" onClick={load} className="mt-4 rounded-lg border px-4 py-2 text-sm">Tentar novamente</button></div></div>

  const changeDraft = (filterId: string, values: readonly (string | number | boolean)[]) => setFilters(current => current.map(filter => filter.filter_id === filterId ? { ...filter, local_draft: values, status: 'DIRTY' } : filter))
  const reset = () => {
    const next = filters.map(filter => ({ ...filter, local_draft: filter.blueprint_default, status: 'DIRTY' as const }))
    setFilters(next)
    void runRuntime(detail, next)
  }
  const applySideChatFilter = (filterId: string, values: readonly (string | number | boolean)[]) => {
    const next = filters.map(filter => filter.filter_id === filterId ? { ...filter, local_draft: values, status: 'DIRTY' as const } : filter)
    setFilters(next)
    void runRuntime(detail, next)
  }
  const revisionChanged = (revision: DashboardRevisionRecordV2, outcome: DashboardSideChatActionResultV2) => {
    if (outcome.outcome !== 'UI_MODIFIED') return
    setDetail(current => current ? { ...current, dashboard: { ...current.dashboard, head_revision_id: revision.revision_id }, head_revision: revision } : current)
  }
  const applyInteraction = (interaction: DashboardRuntimeInteractionRequestV2) => {
    if (interaction.action === 'CROSS_FILTER') {
      if (!interaction.target_filter_id || !interaction.canonical_value || !filters.some(filter => filter.filter_id === interaction.target_filter_id)) {
        setInteractionState({ kind: 'FAILED', interaction_id: interaction.interaction_id, message: 'Cross-filter incompatível com a revisão ativa.' })
        return
      }
      const next = filters.map(filter => filter.filter_id === interaction.target_filter_id ? { ...filter, local_draft: [interaction.canonical_value!], status: 'DIRTY' as const } : filter)
      setInteractionState({ kind: 'CROSS_FILTER_PENDING', interaction_id: interaction.interaction_id, source_widget_id: interaction.source_widget_id })
      setFilters(next)
      void runRuntime(detail, next, [interaction])
      return
    }
    setInteractionState({ kind: 'DRILLDOWN_PENDING', interaction_id: interaction.interaction_id, breadcrumb: drilldownBreadcrumb })
    setDrilldownBreadcrumb(current => [...current, interaction.breadcrumb_label ?? interaction.interaction_id])
    void runRuntime(detail, filters, [interaction])
  }
  const resetDrilldown = () => {
    setDrilldownBreadcrumb([])
    setInteractionState({ kind: 'IDLE' })
    void runRuntime(detail, filters)
  }

  return (
    <>
      <DashboardV2Shell mode={mode} detail={detail} runtime={runtime} loadingRuntime={runtimeLoading} filterStates={filters} selectedWidgetId={selectedWidgetId} onSelectedWidget={setSelectedWidgetId} onFilterDraft={changeDraft} onApplyFilters={() => void runRuntime(detail, filters)} onResetFilters={reset} onRefresh={() => void runRuntime(detail, filters)} onOpenSideChat={() => setSideChatOpen(true)} interactionState={interactionState} drilldownBreadcrumb={drilldownBreadcrumb} onInteraction={applyInteraction} onDrillBack={resetDrilldown} provenanceRequest={provenanceRequest} onClearProvenanceRequest={() => setProvenanceRequest(undefined)} />
      <DashboardSideChatPanel key={`${user?.tenant_id ?? 'none'}:${user?.id ?? 'none'}`} open={sideChatOpen} mode={mode} detail={detail} runtime={runtime} selectedWidgetId={selectedWidgetId} filters={filters} onClose={() => setSideChatOpen(false)} onFocusWidget={widgetId => { setSelectedWidgetId(widgetId); setSideChatOpen(false); window.setTimeout(() => document.querySelector<HTMLElement>(`[data-widget-id="${CSS.escape(widgetId)}"]`)?.focus(), 0) }} onOpenProvenance={widgetId => { if (widgetId) setSelectedWidgetId(widgetId); setProvenanceRequest(current => ({ key: (current?.key ?? 0) + 1, ...(widgetId ? { widget_id: widgetId } : {}) })); setSideChatOpen(false) }} onApplyFilter={applySideChatFilter} onResetFilters={reset} onDrilldown={(interactionId, sourceWidgetId, canonicalValue) => { const definition = detail.head_revision?.blueprint.interactions.find(item => item.interaction_type === 'DRILLDOWN' && item.interaction_id === interactionId); applyInteraction({ interaction_id: interactionId, action: 'DRILLDOWN', source_widget_id: sourceWidgetId, canonical_value: canonicalValue, breadcrumb_label: definition && definition.interaction_type === 'DRILLDOWN' ? definition.target_dimension_id : interactionId }); setSideChatOpen(false) }} onRevisionChanged={revisionChanged} />
    </>
  )
}
