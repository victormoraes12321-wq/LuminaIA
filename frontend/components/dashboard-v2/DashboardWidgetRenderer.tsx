'use client'

import React, { Component, type ReactNode, useEffect, useRef, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AlertTriangle, CheckCircle2, ShieldCheck } from 'lucide-react'
import type {
  DashboardChartWidgetV2,
  DashboardResultShapeV2,
  DashboardWidgetV2,
} from '@/types/dashboard_blueprint_v2'
import type {
  DashboardTabularDataV2,
  DashboardWidgetRuntimeResultV2,
} from '@/types/dashboard_backend_v2'

interface WidgetRendererProps {
  readonly widget: DashboardWidgetV2
  readonly result?: DashboardWidgetRuntimeResultV2
  readonly selected?: boolean
  readonly onSelect?: (widgetId: string) => void
  readonly onOpenProvenance?: (widgetId: string) => void
}

interface WidgetComponentProps {
  readonly widget: DashboardWidgetV2
  readonly result?: DashboardWidgetRuntimeResultV2
}

interface RegistryEntry {
  readonly component: React.ComponentType<WidgetComponentProps>
  readonly supported_result_shapes: readonly DashboardResultShapeV2[]
  readonly binding_required: boolean
  readonly accessibility_strategy: 'TEXT' | 'TEXT_AND_TABLE' | 'LANDMARK'
  readonly loading_strategy: 'SKELETON' | 'TEXT'
  readonly empty_strategy: 'CONTRACT_MESSAGE'
  readonly partial_strategy: 'VISIBLE_NOTICE'
  readonly stale_strategy: 'VISIBLE_NOTICE'
}

type TabularCell = DashboardTabularDataV2['rows'][number]['cells'][number]

function cellText(cell: TabularCell): string {
  if (cell.text_value !== undefined) return cell.text_value
  if (cell.decimal_value !== undefined) return cell.decimal_value
  return 'Sem valor'
}

function formatScalar(result: DashboardWidgetRuntimeResultV2 | undefined): string {
  if (!result?.data || result.data.data_type !== 'SCALAR') return 'Sem valor'
  const value = result.data.value
  const unit = result.data.currency ?? result.data.unit
  return `${value}${unit ? ` ${unit}` : ''}`
}

function asTabular(result: DashboardWidgetRuntimeResultV2 | undefined): DashboardTabularDataV2 | undefined {
  return result?.data?.data_type === 'TABULAR' ? result.data : undefined
}

function columnIds(data: DashboardTabularDataV2): readonly string[] {
  return data.rows[0]?.cells.map(cell => cell.column_id) ?? []
}

function cellFor(row: DashboardTabularDataV2['rows'][number], columnId: string): TabularCell | undefined {
  return row.cells.find(cell => cell.column_id === columnId)
}

function TextualTable({ data, caption }: { readonly data: DashboardTabularDataV2; readonly caption: string }) {
  const columns = columnIds(data)
  return (
    <div className="overflow-auto max-h-72 rounded-lg border border-[rgb(var(--border)/0.55)]">
      <table className="w-full border-collapse text-xs" data-testid="dashboard-widget-table">
        <caption className="sr-only">{caption}</caption>
        <thead className="sticky top-0 bg-[rgb(var(--bg-elevated))]">
          <tr>{columns.map(column => <th scope="col" className="px-3 py-2 text-left" key={column}>{column}</th>)}</tr>
        </thead>
        <tbody>
          {data.rows.map((row, rowIndex) => (
            <tr className="border-t border-[rgb(var(--border)/0.4)]" key={`${caption}-${rowIndex}`}>
              {columns.map(column => <td className="px-3 py-2 font-mono" key={column}>{cellFor(row, column) ? cellText(cellFor(row, column)!) : 'Sem registro'}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function KpiWidget({ result }: WidgetComponentProps) {
  return <p className="font-mono text-3xl font-semibold tracking-tight" data-testid="dashboard-kpi-value">{formatScalar(result)}</p>
}

function ComparisonKpiWidget({ result }: WidgetComponentProps) {
  const data = asTabular(result)
  if (!data) return <KpiWidget widget={{} as DashboardWidgetV2} result={result} />
  return <TextualTable data={data} caption="Comparação certificada" />
}

const CHART_COLORS = ['#6C63FF', '#00B8A9', '#F59E0B', '#EC4899', '#38BDF8', '#A78BFA'] as const

interface ChartPoint {
  readonly label: string
  readonly series: readonly { readonly key: string; readonly value: number }[]
}

function chartPoints(data: DashboardTabularDataV2): readonly ChartPoint[] {
  const columns = columnIds(data)
  const labelColumn = columns[0]
  return data.rows.map((row, rowIndex) => ({
    label: labelColumn && cellFor(row, labelColumn) ? cellText(cellFor(row, labelColumn)!) : `Item ${rowIndex + 1}`,
    series: columns.slice(1).flatMap(column => {
      const cell = cellFor(row, column)
      if (cell?.decimal_value === undefined) return []
      const parsed = Number(cell.decimal_value)
      return Number.isFinite(parsed) ? [{ key: column, value: parsed }] : []
    }),
  }))
}

function chartRows(points: readonly ChartPoint[]): readonly { label: string; values: readonly number[] }[] {
  return points.map(point => ({ label: point.label, values: point.series.map(series => series.value) }))
}

function GovernedResponsiveChart({ children, label, testId }: {
  readonly children: ReactNode
  readonly label: string
  readonly testId: string
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState<{ readonly width: number; readonly height: number } | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const update = () => {
      const bounds = container.getBoundingClientRect()
      if (bounds.width > 0 && bounds.height > 0) {
        setDimensions({ width: bounds.width, height: bounds.height })
      }
    }
    update()
    const observer = new ResizeObserver(update)
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={containerRef}
      className="h-64 min-w-0"
      role="img"
      aria-label={label}
      data-testid={testId}
    >
      {dimensions ? (
        <ResponsiveContainer width="100%" height="100%" initialDimension={dimensions}>{children}</ResponsiveContainer>
      ) : (
        <span className="sr-only">Preparando visualização certificada</span>
      )}
    </div>
  )
}

function GovernedChart({ widget, result }: WidgetComponentProps) {
  const chartWidget = widget as DashboardChartWidgetV2
  const data = asTabular(result)
  if (!data || data.rows.length === 0) return <p>{widget.states.empty.message}</p>
  const points = chartPoints(data).slice(0, chartWidget.maximum_points)
  const series = points[0]?.series.slice(0, chartWidget.maximum_series) ?? []
  const rows = chartRows(points)
  const common = {
    data: rows,
    margin: { top: 8, right: 10, bottom: 4, left: 4 },
  }
  let chart: ReactNode
  if (widget.widget_type === 'LINE_CHART') {
    chart = <LineChart {...common}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" /><YAxis /><Tooltip /><Legend />{series.map((item, index) => <Line key={item.key} name={item.key} dataKey={`values.${index}`} stroke={CHART_COLORS[index % CHART_COLORS.length]} isAnimationActive={false} />)}</LineChart>
  } else if (widget.widget_type === 'AREA_CHART') {
    chart = <AreaChart {...common}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" /><YAxis /><Tooltip /><Legend />{series.map((item, index) => <Area key={item.key} name={item.key} dataKey={`values.${index}`} stroke={CHART_COLORS[index % CHART_COLORS.length]} fill={CHART_COLORS[index % CHART_COLORS.length]} fillOpacity={0.2} isAnimationActive={false} />)}</AreaChart>
  } else if (widget.widget_type === 'PIE_CHART' || widget.widget_type === 'DONUT_CHART') {
    const slices = points.flatMap(point => point.series[0] ? [{ name: point.label, value: point.series[0].value }] : [])
    chart = <PieChart><Pie data={slices} dataKey="value" nameKey="name" innerRadius={widget.widget_type === 'DONUT_CHART' ? 58 : 0} outerRadius={90} isAnimationActive={false}>{slices.map((slice, index) => <Cell key={slice.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart>
  } else {
    const stacked = widget.widget_type === 'STACKED_BAR_CHART'
    chart = <BarChart {...common}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" /><YAxis /><Tooltip /><Legend />{series.map((item, index) => <Bar key={item.key} name={item.key} dataKey={`values.${index}`} stackId={stacked ? 'certified-series' : undefined} fill={CHART_COLORS[index % CHART_COLORS.length]} isAnimationActive={false} />)}</BarChart>
  }
  return (
    <div className="space-y-3">
      <GovernedResponsiveChart
        label={widget.accessibility.summary_template}
        testId={`dashboard-chart-${widget.widget_type.toLowerCase()}`}
      >
        {chart}
      </GovernedResponsiveChart>
      <details className="text-xs">
        <summary className="cursor-pointer font-medium">Alternativa textual do gráfico</summary>
        <TextualTable data={data} caption={widget.accessibility.accessible_name} />
      </details>
    </div>
  )
}

function TableWidget({ widget, result }: WidgetComponentProps) {
  const data = asTabular(result)
  return data ? <TextualTable data={data} caption={widget.accessibility.accessible_name} /> : <p>{widget.states.empty.message}</p>
}

function RankingWidget(props: WidgetComponentProps) {
  const data = asTabular(props.result)
  return data ? <TextualTable data={data} caption="Ranking certificado; posições não são recalculadas no navegador" /> : <p>{props.widget.states.empty.message}</p>
}

function StatusWidget({ widget, result }: WidgetComponentProps) {
  return <div className="flex items-center gap-3"><CheckCircle2 className="text-emerald-500" aria-hidden="true" /><span className="font-mono text-xl">{formatScalar(result)}</span><span className="text-xs">{widget.widget_type === 'PROGRESS' ? 'Progresso certificado' : 'Status certificado'}</span></div>
}

function FilterPanelWidget({ widget }: WidgetComponentProps) {
  return <p className="text-sm">{widget.widget_type === 'FILTER_PANEL' ? `${widget.filter_ids.length} filtros governados disponíveis na barra superior.` : ''}</p>
}

function TextBlockWidget({ widget }: WidgetComponentProps) {
  return widget.widget_type === 'TEXT_BLOCK' ? <p className="whitespace-pre-wrap text-sm leading-6">{widget.content}</p> : null
}

function DividerWidget({ widget }: WidgetComponentProps) {
  return widget.widget_type === 'DIVIDER' ? <hr aria-orientation={widget.orientation === 'VERTICAL' ? 'vertical' : 'horizontal'} className="border-[rgb(var(--border))]" /> : null
}

function ProvenanceSummaryWidget({ result }: WidgetComponentProps) {
  const provenance = result?.provenance
  return (
    <dl className="grid gap-2 text-xs sm:grid-cols-2">
      <div><dt>Validação</dt><dd className="font-semibold">{provenance?.validation_status ?? 'Sem resultado'}</dd></div>
      <div><dt>Atualidade</dt><dd className="font-semibold">{provenance?.source_freshness ?? 'Sem resultado'}</dd></div>
      <div><dt>Cache</dt><dd className="font-semibold">{provenance?.cache_indicator ?? 'Sem resultado'}</dd></div>
      <div><dt>Revisão</dt><dd className="font-mono">{provenance?.revision_id ?? 'Sem resultado'}</dd></div>
    </dl>
  )
}

const ANALYTICAL = ['SCALAR', 'COMPARISON', 'TIME_SERIES', 'GROUPED_SERIES', 'RANKING', 'TABLE', 'STATUS_SUMMARY', 'FACT_SET'] as const
const registry: Readonly<Record<DashboardWidgetV2['widget_type'], RegistryEntry>> = Object.freeze({
  KPI: { component: KpiWidget, supported_result_shapes: ['SCALAR', 'COMPARISON'], binding_required: true, accessibility_strategy: 'TEXT', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  COMPARISON_KPI: { component: ComparisonKpiWidget, supported_result_shapes: ['COMPARISON'], binding_required: true, accessibility_strategy: 'TEXT_AND_TABLE', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  LINE_CHART: { component: GovernedChart, supported_result_shapes: ['TIME_SERIES', 'GROUPED_SERIES'], binding_required: true, accessibility_strategy: 'TEXT_AND_TABLE', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  BAR_CHART: { component: GovernedChart, supported_result_shapes: ['TIME_SERIES', 'GROUPED_SERIES'], binding_required: true, accessibility_strategy: 'TEXT_AND_TABLE', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  STACKED_BAR_CHART: { component: GovernedChart, supported_result_shapes: ['TIME_SERIES', 'GROUPED_SERIES'], binding_required: true, accessibility_strategy: 'TEXT_AND_TABLE', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  AREA_CHART: { component: GovernedChart, supported_result_shapes: ['TIME_SERIES', 'GROUPED_SERIES'], binding_required: true, accessibility_strategy: 'TEXT_AND_TABLE', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  PIE_CHART: { component: GovernedChart, supported_result_shapes: ['TIME_SERIES', 'GROUPED_SERIES'], binding_required: true, accessibility_strategy: 'TEXT_AND_TABLE', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  DONUT_CHART: { component: GovernedChart, supported_result_shapes: ['TIME_SERIES', 'GROUPED_SERIES'], binding_required: true, accessibility_strategy: 'TEXT_AND_TABLE', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  TABLE: { component: TableWidget, supported_result_shapes: ['TABLE', 'FACT_SET'], binding_required: true, accessibility_strategy: 'TEXT_AND_TABLE', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  RANKING: { component: RankingWidget, supported_result_shapes: ['RANKING'], binding_required: true, accessibility_strategy: 'TEXT_AND_TABLE', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  STATUS_SUMMARY: { component: StatusWidget, supported_result_shapes: ['STATUS_SUMMARY'], binding_required: true, accessibility_strategy: 'TEXT', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  PROGRESS: { component: StatusWidget, supported_result_shapes: ['COMPARISON'], binding_required: true, accessibility_strategy: 'TEXT', loading_strategy: 'SKELETON', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  FILTER_PANEL: { component: FilterPanelWidget, supported_result_shapes: ANALYTICAL, binding_required: false, accessibility_strategy: 'LANDMARK', loading_strategy: 'TEXT', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  TEXT_BLOCK: { component: TextBlockWidget, supported_result_shapes: ANALYTICAL, binding_required: false, accessibility_strategy: 'TEXT', loading_strategy: 'TEXT', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  DIVIDER: { component: DividerWidget, supported_result_shapes: ANALYTICAL, binding_required: false, accessibility_strategy: 'LANDMARK', loading_strategy: 'TEXT', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
  PROVENANCE_SUMMARY: { component: ProvenanceSummaryWidget, supported_result_shapes: ANALYTICAL, binding_required: false, accessibility_strategy: 'LANDMARK', loading_strategy: 'TEXT', empty_strategy: 'CONTRACT_MESSAGE', partial_strategy: 'VISIBLE_NOTICE', stale_strategy: 'VISIBLE_NOTICE' },
})

export const DASHBOARD_WIDGET_REGISTRY_V2 = registry

class DashboardWidgetBoundary extends Component<{ readonly children: ReactNode; readonly title: string }, { readonly failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (this.state.failed) return <div role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-sm">O widget “{this.props.title}” falhou isoladamente. Os demais widgets continuam disponíveis.</div>
    return this.props.children
  }
}

export function DashboardWidgetRenderer({ widget, result, selected, onSelect, onOpenProvenance }: WidgetRendererProps) {
  if (!Object.prototype.hasOwnProperty.call(registry, widget.widget_type)) {
    return <article role="alert" className="h-full rounded-2xl border border-red-500/40 bg-red-500/10 p-4" data-testid="dashboard-widget-unknown">Tipo de widget não certificado; renderização bloqueada sem afetar o dashboard.</article>
  }
  const entry = registry[widget.widget_type]
  const expectedShape = 'expected_result_shape' in widget ? widget.expected_result_shape : undefined
  const incompatible = Boolean(result && expectedShape && (
    result.expected_result_shape !== expectedShape || !entry.supported_result_shapes.includes(expectedShape)
  ))
  const ComponentType = entry.component
  return (
    <DashboardWidgetBoundary title={widget.title.title}>
      <article
        className={`min-w-0 h-full rounded-2xl border p-4 shadow-sm transition ${selected ? 'border-violet-500 ring-2 ring-violet-500/20' : 'border-[rgb(var(--border)/0.65)]'} bg-[rgb(var(--bg-surface))]`}
        aria-label={widget.accessibility.accessible_name}
        data-testid={`dashboard-widget-${widget.widget_type.toLowerCase()}`}
        data-widget-id={widget.identity.widget_id}
        tabIndex={widget.accessibility.focus_behavior === 'NOT_FOCUSABLE' ? -1 : 0}
        onClick={() => onSelect?.(widget.identity.widget_id)}
      >
        <header className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            {widget.title.visible && <h2 className="truncate text-sm font-semibold">{widget.title.title}</h2>}
            {widget.title.subtitle && <p className="mt-1 text-xs text-[rgb(var(--text-muted))]">{widget.title.subtitle}</p>}
          </div>
          {result?.certification_reference && <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-500" aria-label="Resultado certificado" />}
        </header>
        {result?.partial && <p role="status" className="mb-3 rounded-md bg-amber-500/10 px-3 py-2 text-xs">{widget.states.partial_message}</p>}
        {result?.truncated && <p role="status" className="mb-3 rounded-md bg-amber-500/10 px-3 py-2 text-xs">{widget.states.truncated_message}</p>}
        {result && /STALE/i.test(result.freshness) && <p role="status" className="mb-3 rounded-md bg-amber-500/10 px-3 py-2 text-xs">{widget.states.stale_message}</p>}
        {result?.status === 'BLOCKED' && <p role="alert">{widget.states.permission_denied_message}</p>}
        {result?.status === 'UNAVAILABLE' && <p role="alert">{widget.states.unavailable_message}</p>}
        {incompatible ? (
          <div role="alert" className="flex gap-2 rounded-lg bg-red-500/10 p-3 text-xs" data-testid="dashboard-widget-contract-error"><AlertTriangle className="h-4 w-4" />Shape de resultado incompatível; o widget foi bloqueado sem afetar o dashboard.</div>
        ) : result?.status !== 'BLOCKED' && result?.status !== 'UNAVAILABLE' ? (
          <ComponentType widget={widget} result={result} />
        ) : null}
        <footer className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-[rgb(var(--border)/0.4)] pt-3 text-[11px] text-[rgb(var(--text-muted))]">
          <span>{result?.freshness ?? 'Sem execução'}</span>
          <button type="button" className="font-medium text-violet-500 hover:underline" onClick={event => { event.stopPropagation(); onOpenProvenance?.(widget.identity.widget_id) }}>Proveniência</button>
        </footer>
      </article>
    </DashboardWidgetBoundary>
  )
}
