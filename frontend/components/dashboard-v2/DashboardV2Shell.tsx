'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { AlertTriangle, ArrowLeft, Bot, ChevronRight, Edit3, History, RefreshCw, ShieldCheck, X } from 'lucide-react'
import { DashboardWidgetRenderer } from './DashboardWidgetRenderer'
import type { DashboardBlueprintV2, DashboardBreakpointNameV2 } from '@/types/dashboard_blueprint_v2'
import type {
  DashboardDetailResponseV2,
  DashboardRuntimeProvenanceV2,
  DashboardRuntimeResultV2,
} from '@/types/dashboard_backend_v2'
import type {
  DashboardFilterStateV2,
  DashboardInteractionStateV2,
  DashboardRuntimeInteractionRequestV2,
  DashboardUiModeV2,
} from '@/types/dashboard_ui_sidechat_v2'

interface DashboardV2ShellProps {
  readonly mode: DashboardUiModeV2
  readonly detail: DashboardDetailResponseV2
  readonly runtime?: DashboardRuntimeResultV2
  readonly loadingRuntime: boolean
  readonly filterStates: readonly DashboardFilterStateV2[]
  readonly selectedWidgetId?: string
  readonly onSelectedWidget: (widgetId: string) => void
  readonly onFilterDraft: (filterId: string, values: readonly (string | number | boolean)[]) => void
  readonly onApplyFilters: () => void
  readonly onResetFilters: () => void
  readonly onRefresh: () => void
  readonly onOpenSideChat: () => void
  readonly interactionState: DashboardInteractionStateV2
  readonly drilldownBreadcrumb: readonly string[]
  readonly onInteraction: (interaction: DashboardRuntimeInteractionRequestV2) => void
  readonly onDrillBack: () => void
  readonly provenanceRequest?: { readonly key: number; readonly widget_id?: string }
  readonly onClearProvenanceRequest: () => void
}

function firstCanonicalValue(result: DashboardRuntimeResultV2['widgets'][number] | undefined): string | undefined {
  if (!result?.data || result.data.data_type !== 'TABULAR') return undefined
  const cell = result.data.rows[0]?.cells[0]
  return cell?.text_value ?? cell?.decimal_value
}

function DashboardInteractionBar({ blueprint, runtime, selectedWidgetId, state, breadcrumb, onInteraction, onBack }: {
  readonly blueprint: DashboardBlueprintV2
  readonly runtime?: DashboardRuntimeResultV2
  readonly selectedWidgetId?: string
  readonly state: DashboardInteractionStateV2
  readonly breadcrumb: readonly string[]
  readonly onInteraction: (interaction: DashboardRuntimeInteractionRequestV2) => void
  readonly onBack: () => void
}) {
  const interactions = blueprint.interactions.filter(item => item.enabled && item.source_widget_id === selectedWidgetId && (item.interaction_type === 'CROSS_FILTER' || item.interaction_type === 'DRILLDOWN'))
  if (!breadcrumb.length && !interactions.length) return null
  const sourceValue = firstCanonicalValue(runtime?.widgets.find(widget => widget.widget_id === selectedWidgetId))
  return (
    <section aria-label="Interações governadas" className="mb-5 flex flex-wrap items-center gap-2 rounded-xl border border-[rgb(var(--border)/0.6)] bg-[rgb(var(--bg-surface))] p-3 text-xs" data-testid="dashboard-interaction-bar">
      {breadcrumb.length > 0 && <><button type="button" onClick={onBack} className="rounded-lg border px-3 py-2">Voltar no drilldown</button><nav aria-label="Breadcrumb do drilldown" className="flex items-center gap-1">{breadcrumb.map((item, index) => <span className="flex items-center gap-1" key={`${item}-${index}`}>{index > 0 && <ChevronRight className="h-3 w-3" aria-hidden="true" />}{item}</span>)}</nav></>}
      {interactions.flatMap(interaction => {
        if (interaction.interaction_type === 'CROSS_FILTER') {
          return interaction.target_widget_ids.map(targetWidgetId => (
            <button
              type="button"
              key={`${interaction.interaction_id}-${targetWidgetId}`}
              disabled={!sourceValue || state.kind.endsWith('_PENDING')}
              className="rounded-lg border px-3 py-2 disabled:opacity-50"
              onClick={() => onInteraction({ interaction_id: interaction.interaction_id, action: 'CROSS_FILTER', source_widget_id: interaction.source_widget_id, target_widget_id: targetWidgetId, target_filter_id: interaction.target_filter_id, canonical_value: sourceValue })}
            >Cross-filter em {targetWidgetId}</button>
          ))
        }
        if (interaction.interaction_type !== 'DRILLDOWN') return []
        return [<button type="button" key={interaction.interaction_id} disabled={state.kind.endsWith('_PENDING')} className="rounded-lg border px-3 py-2 disabled:opacity-50" onClick={() => onInteraction({ interaction_id: interaction.interaction_id, action: 'DRILLDOWN', source_widget_id: interaction.source_widget_id, canonical_value: sourceValue, breadcrumb_label: interaction.target_dimension_id })}>Drilldown: {interaction.target_dimension_id}</button>]
      })}
      {state.kind === 'FAILED' && <p role="alert">{state.message}</p>}
    </section>
  )
}

function breakpointForWidth(width: number): DashboardBreakpointNameV2 {
  if (width >= 1720) return 'ULTRAWIDE'
  if (width >= 1180) return 'DESKTOP'
  if (width >= 700) return 'TABLET'
  return 'MOBILE'
}

function useDashboardBreakpoint(): DashboardBreakpointNameV2 {
  const [breakpoint, setBreakpoint] = useState<DashboardBreakpointNameV2>('DESKTOP')
  useEffect(() => {
    const update = () => setBreakpoint(breakpointForWidth(window.innerWidth))
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])
  return breakpoint
}

function DashboardStatusBanner({ detail, runtime }: { readonly detail: DashboardDetailResponseV2; readonly runtime?: DashboardRuntimeResultV2 }) {
  const messages: string[] = []
  if (detail.dashboard.lifecycle === 'ARCHIVED') messages.push('Dashboard arquivado: somente leitura histórica.')
  if (!detail.active_publication) messages.push('Dashboard ainda não possui publicação ativa.')
  if (runtime?.status === 'PARTIAL') messages.push('Resultado parcial: consulte os avisos e a proveniência antes de decidir.')
  if (runtime?.status === 'BLOCKED') messages.push('Execução bloqueada pela governança.')
  if (runtime?.status === 'UNAVAILABLE') messages.push('Runtime indisponível; nenhum valor foi sintetizado.')
  if (!messages.length) return null
  return (
    <div role="status" data-testid="dashboard-status-banner" className="mb-4 flex gap-3 rounded-xl border border-amber-500/35 bg-amber-500/10 p-4 text-sm">
      <AlertTriangle className="h-5 w-5 shrink-0 text-amber-500" aria-hidden="true" />
      <div>{messages.map(message => <p key={message}>{message}</p>)}</div>
    </div>
  )
}

function DashboardFilterBar({ blueprint, states, onDraft, onApply, onReset, disabled }: {
  readonly blueprint: DashboardBlueprintV2
  readonly states: readonly DashboardFilterStateV2[]
  readonly onDraft: (filterId: string, values: readonly (string | number | boolean)[]) => void
  readonly onApply: () => void
  readonly onReset: () => void
  readonly disabled: boolean
}) {
  const visibleFilters = blueprint.filters.filter(filter => filter.visible)
  if (!visibleFilters.length) return null
  return (
    <form className="mb-5 rounded-xl border border-[rgb(var(--border)/0.6)] bg-[rgb(var(--bg-surface))] p-3" onSubmit={event => { event.preventDefault(); onApply() }}>
      <div className="flex flex-wrap items-end gap-3">
        {visibleFilters.map(filter => {
          const state = states.find(item => item.filter_id === filter.filter_id)
          const displayValue = state?.local_draft.join(', ') ?? ''
          if (filter.filter_type === 'BOOLEAN') {
            return <label className="grid gap-1 text-xs" key={filter.filter_id}>{filter.accessibility_label}<select className="rounded-lg border bg-transparent px-3 py-2" value={displayValue} onChange={event => onDraft(filter.filter_id, event.target.value ? [event.target.value === 'true'] : [])}><option value="">Todos</option><option value="true">Sim</option><option value="false">Não</option></select></label>
          }
          return (
            <label className="grid min-w-40 flex-1 gap-1 text-xs" key={filter.filter_id}>
              {filter.accessibility_label}
              <input
                type={filter.filter_type === 'DATE_RANGE' ? 'date' : filter.filter_type === 'NUMBER_RANGE' ? 'number' : 'search'}
                className="rounded-lg border border-[rgb(var(--border))] bg-transparent px-3 py-2"
                value={displayValue}
                placeholder={filter.filter_type.replaceAll('_', ' ').toLowerCase()}
                onChange={event => {
                  const values = event.target.value.split(',').map(value => value.trim()).filter(Boolean).slice(0, filter.maximum_selections)
                  onDraft(filter.filter_id, filter.filter_type === 'NUMBER_RANGE' ? values.map(Number).filter(Number.isFinite) : values)
                }}
              />
            </label>
          )
        })}
        <button type="submit" disabled={disabled} className="rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50">Aplicar filtros</button>
        <button type="button" disabled={disabled} onClick={onReset} className="rounded-lg border px-4 py-2 text-xs font-semibold disabled:opacity-50">Limpar</button>
      </div>
    </form>
  )
}

function DashboardResponsiveGrid({ blueprint, runtime, selectedWidgetId, onSelectedWidget, onOpenProvenance }: {
  readonly blueprint: DashboardBlueprintV2
  readonly runtime?: DashboardRuntimeResultV2
  readonly selectedWidgetId?: string
  readonly onSelectedWidget: (widgetId: string) => void
  readonly onOpenProvenance: (widgetId: string) => void
}) {
  const breakpoint = useDashboardBreakpoint()
  const layout = blueprint.layout.breakpoints.find(candidate => candidate.breakpoint === breakpoint)
    ?? blueprint.layout.breakpoints.find(candidate => candidate.breakpoint === 'DESKTOP')
    ?? blueprint.layout.breakpoints[0]
  const placements = layout?.items.filter(item => item.visible).slice().sort((a, b) => a.reading_order - b.reading_order) ?? []
  const widgets = placements.flatMap(placement => {
    const widget = blueprint.widgets.find(candidate => candidate.identity.widget_id === placement.widget_id && candidate.visible)
    return widget ? [{ widget, placement }] : []
  })
  const unplaced = blueprint.widgets.filter(widget => widget.visible && !widgets.some(item => item.widget.identity.widget_id === widget.identity.widget_id))
  return (
    <div
      className="grid min-w-0 auto-rows-[92px] gap-4"
      style={{ gridTemplateColumns: `repeat(${layout?.grid.columns ?? 1}, minmax(0, 1fr))`, gap: layout?.grid.gap_px ?? 16 }}
      data-testid="dashboard-responsive-grid"
      data-breakpoint={breakpoint}
    >
      {widgets.map(({ widget, placement }) => (
        <div key={widget.identity.widget_id} className="min-w-0" style={{ gridColumn: `${placement.x + 1} / span ${placement.width}`, gridRow: `${placement.y + 1} / span ${placement.height}` }}>
          <DashboardWidgetRenderer widget={widget} result={runtime?.widgets.find(result => result.widget_id === widget.identity.widget_id)} selected={selectedWidgetId === widget.identity.widget_id} onSelect={onSelectedWidget} onOpenProvenance={onOpenProvenance} />
        </div>
      ))}
      {unplaced.map(widget => (
        <div key={widget.identity.widget_id} className="col-span-full min-w-0" data-testid="dashboard-layout-fallback">
          <DashboardWidgetRenderer widget={widget} result={runtime?.widgets.find(result => result.widget_id === widget.identity.widget_id)} selected={selectedWidgetId === widget.identity.widget_id} onSelect={onSelectedWidget} onOpenProvenance={onOpenProvenance} />
        </div>
      ))}
    </div>
  )
}

export function DashboardProvenanceDrawer({ provenance, widgetId, onClose }: {
  readonly provenance?: DashboardRuntimeProvenanceV2
  readonly widgetId?: string
  readonly onClose: () => void
}) {
  const widgetWarning = provenance?.warnings.filter(warning => !widgetId || warning.widget_id === widgetId) ?? []
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" role="presentation" onMouseDown={event => { if (event.currentTarget === event.target) onClose() }}>
      <aside role="dialog" aria-modal="true" aria-label="Proveniência do dashboard" className="h-full w-full max-w-lg overflow-y-auto border-l border-[rgb(var(--border))] bg-[rgb(var(--bg-surface))] p-6 shadow-2xl" data-testid="dashboard-provenance-drawer">
        <header className="mb-6 flex items-center justify-between"><h2 className="text-lg font-semibold">Proveniência pública</h2><button type="button" aria-label="Fechar proveniência" onClick={onClose}><X /></button></header>
        {!provenance ? <p>Nenhuma execução disponível.</p> : (
          <dl className="grid gap-4 text-sm">
            <div><dt className="text-xs text-[rgb(var(--text-muted))]">Publicação</dt><dd className="font-mono">{provenance.publication_id}</dd></div>
            <div><dt className="text-xs text-[rgb(var(--text-muted))]">Revisão</dt><dd className="font-mono">{provenance.revision_id}</dd></div>
            {widgetId && <div><dt className="text-xs text-[rgb(var(--text-muted))]">Widget</dt><dd className="font-mono">{widgetId}</dd></div>}
            {provenance.binding_id && <div><dt className="text-xs text-[rgb(var(--text-muted))]">Binding</dt><dd className="font-mono">{provenance.binding_id}</dd></div>}
            <div><dt className="text-xs text-[rgb(var(--text-muted))]">Validação</dt><dd>{provenance.validation_status}</dd></div>
            <div><dt className="text-xs text-[rgb(var(--text-muted))]">Atualidade da fonte</dt><dd>{provenance.source_freshness}</dd></div>
            <div><dt className="text-xs text-[rgb(var(--text-muted))]">Cache/materialização</dt><dd>{provenance.cache_indicator}</dd></div>
            {provenance.period_summary && <div><dt className="text-xs text-[rgb(var(--text-muted))]">Período</dt><dd>{provenance.period_summary}</dd></div>}
            <div><dt className="text-xs text-[rgb(var(--text-muted))]">Filtros efetivos</dt><dd>{provenance.effective_filters.length ? provenance.effective_filters.map(filter => `${filter.filter_id}: ${filter.canonical_values.join(', ')}`).join('; ') : 'Nenhum'}</dd></div>
            <div><dt className="text-xs text-[rgb(var(--text-muted))]">Definições públicas</dt><dd>{provenance.metric_definition_references.join(', ') || 'Nenhuma'}</dd></div>
            <div><dt className="text-xs text-[rgb(var(--text-muted))]">Avisos</dt><dd>{widgetWarning.map(warning => warning.message).join('; ') || 'Nenhum'}</dd></div>
          </dl>
        )}
        <p className="mt-8 rounded-lg bg-emerald-500/10 p-3 text-xs"><ShieldCheck className="mr-2 inline h-4 w-4" />Detalhes técnicos e segredos operacionais nunca são exibidos.</p>
      </aside>
    </div>
  )
}

export function DashboardV2Shell(props: DashboardV2ShellProps) {
  const { detail, runtime } = props
  const blueprint = detail.head_revision?.blueprint
  const [provenanceWidget, setProvenanceWidget] = useState<string | undefined>()
  const [provenanceOpen, setProvenanceOpen] = useState(false)
  const canEdit = props.mode !== 'V2_READ' && props.mode !== 'V2_PREVIEW' && detail.effective_capabilities.includes('dashboard:edit_visual')
  const title = detail.dashboard.identity.title
  const runtimeProvenance = useMemo(() => {
    if (!runtime) return undefined
    const activeWidget = props.provenanceRequest?.widget_id ?? provenanceWidget
    if (activeWidget) return runtime.widgets.find(widget => widget.widget_id === activeWidget)?.provenance ?? runtime.provenance
    return runtime.provenance
  }, [props.provenanceRequest?.widget_id, provenanceWidget, runtime])
  if (!blueprint) return <div role="status" className="p-8">Dashboard sem revisão disponível.</div>
  return (
    <div className="min-h-screen bg-[rgb(var(--bg-base))] text-[rgb(var(--text-primary))]" data-testid="dashboard-v2-shell">
      <header className="sticky top-0 z-30 border-b border-[rgb(var(--border)/0.6)] bg-[rgb(var(--bg-base)/0.92)] px-4 py-3 backdrop-blur-xl sm:px-8">
        <div className="mx-auto flex max-w-[1800px] flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3"><Link href="/dashboard/v2" aria-label="Voltar à biblioteca"><ArrowLeft className="h-5 w-5" /></Link><div className="min-w-0"><h1 className="truncate text-lg font-semibold">{title}</h1><p className="text-xs text-[rgb(var(--text-muted))]">{detail.dashboard.lifecycle} · revisão {detail.head_revision?.revision_id}</p></div></div>
          <nav className="flex flex-wrap items-center gap-2" aria-label="Ações do dashboard">
            <button type="button" onClick={props.onRefresh} disabled={props.loadingRuntime} className="rounded-lg border px-3 py-2 text-xs"><RefreshCw className={`mr-1 inline h-3.5 w-3.5 ${props.loadingRuntime ? 'animate-spin' : ''}`} />Atualizar</button>
            <button type="button" onClick={() => { setProvenanceWidget(undefined); setProvenanceOpen(true) }} className="rounded-lg border px-3 py-2 text-xs"><ShieldCheck className="mr-1 inline h-3.5 w-3.5" />Proveniência</button>
            {canEdit && <Link href={`/dashboard/v2/${encodeURIComponent(detail.dashboard.identity.dashboard_id)}/edit`} className="rounded-lg border px-3 py-2 text-xs"><Edit3 className="mr-1 inline h-3.5 w-3.5" />Editar</Link>}
            {canEdit && <Link href={`/dashboard/v2/${encodeURIComponent(detail.dashboard.identity.dashboard_id)}/history`} className="rounded-lg border px-3 py-2 text-xs"><History className="mr-1 inline h-3.5 w-3.5" />Histórico</Link>}
            {props.mode === 'V2_SIDE_CHAT' && <button type="button" onClick={props.onOpenSideChat} className="rounded-lg bg-violet-600 px-3 py-2 text-xs font-semibold text-white"><Bot className="mr-1 inline h-3.5 w-3.5" />Side chat</button>}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-[1800px] p-4 sm:p-8">
        <DashboardStatusBanner detail={detail} runtime={runtime} />
        <DashboardFilterBar blueprint={blueprint} states={props.filterStates} onDraft={props.onFilterDraft} onApply={props.onApplyFilters} onReset={props.onResetFilters} disabled={props.loadingRuntime} />
        <DashboardInteractionBar blueprint={blueprint} runtime={runtime} selectedWidgetId={props.selectedWidgetId} state={props.interactionState} breadcrumb={props.drilldownBreadcrumb} onInteraction={props.onInteraction} onBack={props.onDrillBack} />
        {props.loadingRuntime && !runtime ? <div className="grid gap-4 md:grid-cols-2"><div className="h-48 animate-pulse rounded-2xl bg-[rgb(var(--bg-elevated))]" /><div className="h-48 animate-pulse rounded-2xl bg-[rgb(var(--bg-elevated))]" /></div> : <DashboardResponsiveGrid blueprint={blueprint} runtime={runtime} selectedWidgetId={props.selectedWidgetId} onSelectedWidget={props.onSelectedWidget} onOpenProvenance={widgetId => { setProvenanceWidget(widgetId); setProvenanceOpen(true) }} />}
      </main>
      {(provenanceOpen || Boolean(props.provenanceRequest)) && <DashboardProvenanceDrawer provenance={runtimeProvenance} widgetId={props.provenanceRequest?.widget_id ?? provenanceWidget} onClose={() => { setProvenanceOpen(false); props.onClearProvenanceRequest() }} />}
    </div>
  )
}
