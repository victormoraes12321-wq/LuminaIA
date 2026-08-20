'use client'

/**
 * DynamicRenderer v3.0 — Renderizador Dinâmico com Apache ECharts
 *
 * Troca os componentes antigos (recharts) pelos novos ECharts premium.
 * Também suporta: resposta_direta (resposta textual da IA), bloqueio de escopo,
 * e o novo SCATTER chart com ECharts.
 */

import { motion, AnimatePresence } from 'framer-motion'
import { BarChart3, TrendingUp, PieChart, Table2, Gauge, AreaChart, Download, MessageSquare, ScatterChart, Grid, Blocks, Filter } from 'lucide-react'
import { cn } from '@/lib/utils'
import { EKPICards } from '@/components/charts/EKPICards'
import { EBarChart } from '@/components/charts/EBarChart'
import { ELineChart } from '@/components/charts/ELineChart'
import { EAreaChart } from '@/components/charts/EAreaChart'
import { EPieChart } from '@/components/charts/EPieChart'
import { EScatterChart } from '@/components/charts/EScatterChart'
import { EHeatmapChart } from '@/components/charts/EHeatmapChart'
import { ETreemapChart } from '@/components/charts/ETreemapChart'
import { EFunnelChart } from '@/components/charts/EFunnelChart'
import { DataTable } from '@/components/charts/DataTable'
import { repairTextEncoding } from '@/lib/textEncoding'
import { ComparisonRenderer } from '@/components/comparison'
import type { ComparisonPresentationModel } from '@/components/comparison'
import {
  isChartDataBar,
  isChartDataKPI,
  isChartDataPie,
  isChartDataTable,
  isChartDataHeatmap,
  isChartDataScatter,
  isChartDataTreemap,
  isChartDataFunnel,
} from '@/types/lumina'
import type { AnyChartData, ChartResumo, ChartType } from '@/types/lumina'

// ── Chart Type Metadata ────────────────────────────────────────

const CHART_META: Record<
  ChartType,
  { label: string; icon: React.ComponentType<{ size?: number; className?: string }> }
> = {
  BAR:     { label: 'Gráfico de Barras',  icon: BarChart3 },
  LINE:    { label: 'Gráfico de Linhas',  icon: TrendingUp },
  PIE:     { label: 'Gráfico de Pizza',   icon: PieChart },
  TABLE:   { label: 'Tabela de Dados',    icon: Table2 },
  KPI:     { label: 'Painel de KPIs',     icon: Gauge },
  AREA:    { label: 'Gráfico de Área',    icon: AreaChart },
  SCATTER: { label: 'Dispersão',          icon: ScatterChart },
  HEATMAP: { label: 'Mapa de Calor',      icon: Grid },
  TREEMAP: { label: 'Treemap Hierárquico', icon: Blocks },
  FUNNEL:  { label: 'Funil de Conversão', icon: Filter },
}

// ── Chart Height by Type ────────────────────────────────────────

function getMinHeight(chartType: ChartType): string {
  switch (chartType) {
    case 'KPI':    return 'auto'
    case 'TABLE':  return 'auto'
    case 'PIE':    return '280px'
    default:       return '340px'
  }
}

// ── No Data Fallback ───────────────────────────────────────────

const formatSummaryValue = (key: string, val: string | number): string => {
  if (typeof val !== 'number') return repairTextEncoding(String(val))
  const keyUpper = key.toUpperCase()
  if (keyUpper.includes('VALOR') || keyUpper.includes('TICKET') || keyUpper.includes('RECEITA') || keyUpper.includes('FATURAMENTO') || keyUpper.includes('COMISSAO')) {
    return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  }
  if (keyUpper.includes('REGISTROS') || keyUpper.includes('QUANTIDADE') || keyUpper.includes('QTD') || keyUpper.includes('TOTAL_LINHAS')) {
    return Math.round(val).toLocaleString('pt-BR')
  }
  return val.toLocaleString('pt-BR')
}

function NoDataFallback({ chartType }: { chartType: ChartType }) {
  const meta = CHART_META[chartType]
  const Icon = meta.icon
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[200px] gap-3 opacity-40">
      <Icon size={36} className="text-lumina-400" />
      <p className="text-sm font-medium" style={{ color: 'rgb(var(--text-muted))' }}>
        Sem dados para exibir
      </p>
    </div>
  )
}

// ── Resposta Direta (resposta textual da IA) ───────────────────

function RespostaDireta({ texto }: { texto: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-3"
    >
      <div className="flex items-center gap-2 mb-1">
        <MessageSquare size={13} className="text-lumina-400" />
        <span className="text-xs font-medium" style={{ color: 'rgb(var(--text-muted))' }}>
          Resposta Direta
        </span>
      </div>
      <div
        className="rounded-xl p-4 leading-relaxed text-sm"
        style={{
          background: 'rgba(108,99,255,0.06)',
          border: '1px solid rgba(108,99,255,0.15)',
          color: 'rgb(var(--text-secondary))',
        }}
      >
          {repairTextEncoding(texto)}
      </div>
    </motion.div>
  )
}

// ── DynamicRenderer ────────────────────────────────────────────

interface DynamicRendererProps {
  chartType: ChartType | null
  chartData: AnyChartData | null | Record<string, unknown>
  className?: string
  title?: string
  visualizations?: Array<{ chart_type: ChartType; chart_data: AnyChartData }> | null
  comparisonModel?: ComparisonPresentationModel | null
}

function hasDirectResponse(data: unknown): data is { resposta_direta: string } {
  return (
    typeof data === 'object' &&
    data !== null &&
    'resposta_direta' in data &&
    typeof (data as { resposta_direta?: unknown }).resposta_direta === 'string'
  )
}

function hasResumo(data: AnyChartData): data is AnyChartData & { resumo: ChartResumo } {
  return 'resumo' in data && typeof data.resumo === 'object' && data.resumo !== null
}

const easeOutQuint: [number, number, number, number] = [0.16, 1, 0.3, 1]

const containerVariants = {
  hidden:  { opacity: 0, scale: 0.97, y: 12 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.4, ease: easeOutQuint },
  },
  exit: {
    opacity: 0,
    scale: 0.97,
    y: -8,
    transition: { duration: 0.2 },
  },
}

// ── CSV Export ─────────────────────────────────────────────────

function downloadCSV(chartType: ChartType, chartData: AnyChartData, title?: string) {
  let csvContent = ''
  const cleanTitle = title ? title.trim() : 'dados_exportados'
  const filename = `${cleanTitle.toLowerCase().replace(/[^a-z0-9À-ÿ]/gi, '_')}.csv`

  const escapeCSV = (val: unknown): string => {
    if (val === null || val === undefined) return ''
    const str = String(val)
    if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
      return `"${str.replace(/"/g, '""')}"`
    }
    return str
  }

  if (chartType === 'KPI' && isChartDataKPI(chartData)) {
    const headers = ['Métrica', 'Valor', 'Valor Formatado', 'Unidade', 'Tendência', 'Rótulo da Tendência']
    csvContent += headers.map(escapeCSV).join(',') + '\n'
    for (const kpi of chartData.kpis) {
      const row = [kpi.label, kpi.value, kpi.value_formatado, kpi.unit, kpi.trend, kpi.trend_label]
      csvContent += row.map(escapeCSV).join(',') + '\n'
    }
  } else if (chartType === 'PIE' && isChartDataPie(chartData)) {
    const headers = ['Categoria', 'Valor (%)']
    csvContent += headers.map(escapeCSV).join(',') + '\n'
    for (let i = 0; i < chartData.labels.length; i++) {
      csvContent += [chartData.labels[i], chartData.values[i]].map(escapeCSV).join(',') + '\n'
    }
  } else if (chartType === 'TABLE' && isChartDataTable(chartData)) {
    const headers = chartData.columns.map(col => col.label)
    csvContent += headers.map(escapeCSV).join(',') + '\n'
    for (const rowObj of chartData.rows) {
      const row = chartData.columns.map(col => rowObj[col.key])
      csvContent += row.map(escapeCSV).join(',') + '\n'
    }
  } else if (isChartDataBar(chartData)) {
    const headers = ['Rótulo', ...chartData.datasets.map(ds => ds.label)]
    csvContent += headers.map(escapeCSV).join(',') + '\n'
    for (let i = 0; i < chartData.labels.length; i++) {
      const row = [chartData.labels[i], ...chartData.datasets.map(ds => ds.data[i] !== undefined ? ds.data[i] : '')]
      csvContent += row.map(escapeCSV).join(',') + '\n'
    }
  } else {
    return
  }

  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// ── Main Export ────────────────────────────────────────────────

export function DynamicRenderer({
  chartType,
  chartData,
  className,
  title,
  visualizations,
  comparisonModel,
}: DynamicRendererProps) {
  if (comparisonModel) {
    return <ComparisonRenderer model={comparisonModel} className={className} />
  }

  // Handle resposta_direta (textual answer from AI without chart)
  if (!chartType && hasDirectResponse(chartData)) {
    const texto = chartData.resposta_direta
    return (
      <div className={cn('flex flex-col h-full', className)}>
        <RespostaDireta texto={texto} />
      </div>
    )
  }

  // Se houver múltiplas visualizações, renderiza em sequência de forma recursiva
  if (visualizations && visualizations.length > 1) {
    return (
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 w-full h-full">
        {visualizations.map((vis, idx) => (
          <div
            key={`${vis.chart_type}-${idx}`}
            className="w-full rounded-2xl p-6 border border-zinc-200/50 dark:border-zinc-800/40 bg-zinc-50/20 dark:bg-zinc-950/20 backdrop-blur-sm shadow-sm"
          >
            <DynamicRenderer
              chartType={vis.chart_type}
              chartData={vis.chart_data}
              title={`${title || ''} (${CHART_META[vis.chart_type]?.label || vis.chart_type})`}
            />
          </div>
        ))}
      </div>
    )
  }

  if (!chartType || !chartData) {
    return null
  }

  const typedData = chartData as AnyChartData
  const minH = getMinHeight(chartType)

  const content = (): React.ReactNode => {
    switch (chartType) {
      // ── KPI ─────────────────────────────────────────────────
      case 'KPI':
        if (!isChartDataKPI(typedData)) return <NoDataFallback chartType={chartType} />
        return <EKPICards data={typedData} />

      // ── Bar ─────────────────────────────────────────────────
      case 'BAR':
        if (!isChartDataBar(typedData)) return <NoDataFallback chartType={chartType} />
        return (
          <div style={{ height: '100%', minHeight: 300 }}>
            <EBarChart data={typedData} height="100%" />
          </div>
        )

      // ── Line ────────────────────────────────────────────────
      case 'LINE':
        if (!isChartDataBar(typedData)) return <NoDataFallback chartType={chartType} />
        return (
          <div style={{ height: '100%', minHeight: 300 }}>
            <ELineChart data={typedData} height="100%" />
          </div>
        )

      // ── Area ────────────────────────────────────────────────
      case 'AREA':
        if (!isChartDataBar(typedData)) return <NoDataFallback chartType={chartType} />
        return (
          <div style={{ height: '100%', minHeight: 300 }}>
            <EAreaChart data={typedData} height="100%" />
          </div>
        )

      // ── Pie ─────────────────────────────────────────────────
      case 'PIE':
        if (!isChartDataPie(typedData)) return <NoDataFallback chartType={chartType} />
        return (
          <div style={{ height: '100%', minHeight: 260 }}>
            <EPieChart data={typedData} height="100%" />
          </div>
        )

      // ── Scatter ─────────────────────────────────────────────
      case 'SCATTER':
        if (!isChartDataScatter(typedData)) {
          return <NoDataFallback chartType={chartType} />
        }
        return (
          <div style={{ height: '100%', minHeight: 300 }}>
            <EScatterChart data={typedData} height="100%" />
          </div>
        )

      // ── Heatmap ─────────────────────────────────────────────
      case 'HEATMAP':
        if (!isChartDataHeatmap(typedData)) return <NoDataFallback chartType={chartType} />
        return (
          <div style={{ height: '100%', minHeight: 300 }}>
            <EHeatmapChart data={typedData} height="100%" />
          </div>
        )

      // ── Treemap ─────────────────────────────────────────────
      case 'TREEMAP':
        if (!isChartDataTreemap(typedData)) return <NoDataFallback chartType={chartType} />
        return (
          <div style={{ height: '100%', minHeight: 300 }}>
            <ETreemapChart data={typedData} height="100%" />
          </div>
        )

      // ── Funnel ──────────────────────────────────────────────
      case 'FUNNEL':
        if (!isChartDataFunnel(typedData)) return <NoDataFallback chartType={chartType} />
        return (
          <div style={{ height: '100%', minHeight: 300 }}>
            <EFunnelChart data={typedData} height="100%" />
          </div>
        )

      // ── Table ───────────────────────────────────────────────
      case 'TABLE':
        if (!isChartDataTable(typedData)) return <NoDataFallback chartType={chartType} />
        return <DataTable data={typedData} />

      default:
        return <NoDataFallback chartType={chartType} />
    }
  }

  const canExport = ['KPI', 'PIE', 'TABLE', 'BAR', 'LINE', 'AREA', 'HEATMAP', 'TREEMAP', 'FUNNEL'].includes(chartType)

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={`${chartType}-renderer`}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        className={cn('flex flex-col h-full', className)}
        style={{ minHeight: minH !== 'auto' ? minH : undefined }}
      >
        {/* Export action only (No technical chart type label or debug badges) */}
        {canExport && typedData && (
          <div className="flex justify-end mb-2 flex-shrink-0">
            <button
              type="button"
              onClick={() => downloadCSV(chartType, typedData, title)}
              className="flex items-center gap-1 text-[10px] font-semibold py-1 px-2 rounded-lg border border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 hover:text-zinc-900 dark:hover:text-zinc-200 transition-colors"
              title="Exportar dados para CSV"
            >
              <Download size={11} />
              <span>Exportar CSV</span>
            </button>
          </div>
        )}

        {/* Chart content */}
        <div className={cn(
          'flex-1 min-h-0',
          chartType !== 'KPI' && chartType !== 'TABLE' && 'h-full',
        )}>
          {content()}
        </div>

        {/* Resumo footer */}
        {hasResumo(typedData) && Object.keys(typedData.resumo).length > 0 && (
          <div
            className="mt-4 pt-3 flex flex-wrap gap-x-5 gap-y-1 flex-shrink-0"
            style={{ borderTop: '1px solid rgb(var(--border) / 0.4)' }}
          >
            {Object.entries(typedData.resumo).slice(0, 4).map(([key, val]) => (
              <div key={key} className="flex items-center gap-1.5">
                <span className="text-[10px] uppercase tracking-wider" style={{ color: 'rgb(var(--text-muted))' }}>
                  {repairTextEncoding(key.replace(/_/g, ' '))}
                </span>
                <span className="text-xs font-semibold" style={{ color: 'rgb(var(--text-secondary))' }}>
                  {formatSummaryValue(key, val)}
                </span>
              </div>
            ))}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
