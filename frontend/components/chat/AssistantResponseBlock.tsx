'use client'

import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Compass,
  CheckCircle2,
  Download,
  Copy,
  ChevronRight,
  Maximize2,
  Star,
  StarOff,
  X,
  FileSpreadsheet,
  FileText,
  Grid,
  Clock3,
  Database,
  ShieldCheck,
  UserRoundCog,
  Wrench,
  ChevronDown,
  ChevronUp,
  BarChart3,
  PieChart,
  Table2,
  AreaChart,
  Gauge,
  RotateCcw,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { DynamicRenderer } from '@/components/DynamicRenderer'
import { DataTable } from '@/components/charts/DataTable'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { exportToCSV, exportToExcel, exportToPDF } from '@/lib/exportUtils'
import { InlineDashboardRuntime } from '@/components/chat/InlineDashboardRuntime'
import { ClarificationPanel } from '@/components/chat/ClarificationPanel'
import { FeedbackControls } from '@/components/chat/FeedbackControls'
import { repairTextEncoding } from '@/lib/textEncoding'
import { isChartDataTable } from '@/types/lumina'
import type { AnyChartData, BIAnomaly, ChartDataClarification, ChartType, ChatMessage, QueryResponse } from '@/types/lumina'
import { useAuth } from '@/context/AuthContext'

// ── Markdown Parser for Bold Text ──────────────────────────────
function parseMarkdownBold(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} className="font-bold text-white">
          {part.slice(2, -2)}
        </strong>
      )
    }
    return part
  })
}

function isClarificationData(data: AnyChartData | null | undefined): data is ChartDataClarification {
  return Boolean(data && 'clarification_required' in data)
}

// ── BI Analysis Text Splitter / Parser ─────────────────────────
function parseBIAnalysis(content: string) {
  const sections: Record<string, string> = {
    resumo: '',
    kpis: '',
    comparativa: '',
    insights: '',
    riscos: '',
    oportunidades: '',
    recomendacoes: '',
    observacoes: ''
  }

  const headerRegex = /##\s+(\d)\.\s+([^\n\r]+)/g
  const matches = Array.from(content.matchAll(headerRegex))

  if (matches.length === 0) {
    sections.resumo = content
    return { sections, isStructured: false }
  }

  const sectionKeys = [
    'resumo',
    'kpis',
    'comparativa',
    'insights',
    'riscos',
    'oportunidades',
    'recomendacoes',
    'observacoes'
  ]

  for (let i = 0; i < matches.length; i++) {
    const match = matches[i]
    const num = parseInt(match[1], 10)
    const key = sectionKeys[num - 1]
    if (!key) continue

    const startIndex = match.index! + match[0].length
    const endIndex = i + 1 < matches.length ? matches[i + 1].index : content.length
    sections[key] = content.substring(startIndex, endIndex).trim()
  }

  return { sections, isStructured: true }
}

// ── KPI Bullet Points Parser ───────────────────────────────────
interface ParsedKPI {
  titulo: string
  valor: string
  variacao?: string
  comparacao?: string
  isPositive?: boolean
}

function parseKPIsFromMarkdown(kpisMarkdown: string): ParsedKPI[] {
  if (!kpisMarkdown) return []
  const lines = kpisMarkdown.split('\n')
  const kpis: ParsedKPI[] = []

  for (const line of lines) {
    const cleanLine = line.trim().replace(/^[-*+]\s+/, '')
    if (!cleanLine) continue

    // Regex match e.g. **Faturamento:** R$ 150.000 (+15% vs mês anterior)
    const match = cleanLine.match(/\*\*(.*?)\*\*[:\s]*([^\(]+)(?:\((.*?)\))?/)
    if (match) {
      const titulo = match[1].trim()
      const valor = match[2].trim()
      const extra = match[3] ? match[3].trim() : undefined

      let variacao: string | undefined
      let comparacao: string | undefined
      let isPositive: boolean | undefined

      if (extra) {
        const vsIndex = extra.toLowerCase().indexOf('vs')
        if (vsIndex !== -1) {
          variacao = extra.substring(0, vsIndex).trim()
          comparacao = extra.substring(vsIndex).trim()
        } else {
          variacao = extra
        }
        isPositive = !variacao.startsWith('-')
      }

      kpis.push({
        titulo,
        valor,
        variacao,
        comparacao,
        isPositive
      })
    }
  }
  return kpis
}

function getIconForKPI(title: string) {
  const lower = title.toLowerCase()
  if (lower.includes('faturamento') || lower.includes('receita') || lower.includes('venda')) return '💰'
  if (lower.includes('ticket') || lower.includes('medio') || lower.includes('médio')) return '🎟️'
  if (lower.includes('quantidade') || lower.includes('volume') || lower.includes('pedido') || lower.includes('transa')) return '📦'
  if (lower.includes('meta') || lower.includes('atingimento')) return '🎯'
  if (lower.includes('margem') || lower.includes('lucro') || lower.includes('custo')) return '📈'
  if (lower.includes('estoque') || lower.includes('critico') || lower.includes('mínimo')) return '⚠️'
  if (lower.includes('cliente') || lower.includes('comprador') || lower.includes('nps') || lower.includes('satisfa')) return '👥'
  return '📊'
}

// ── Programmatic Suggestion Generator ──────────────────────────
function generateSuggestions(queryResponse?: QueryResponse): string[] {
  if (!queryResponse) return []
  
  // Banim mocks estáticos em telas de clarificação/ambiguidade/erro
  if (
    queryResponse.status === 'AMBIGUOUS'
    || queryResponse.status === 'MISSING_INFORMATION'
    || queryResponse.status === 'CLARIFICATION_REQUIRED'
  ) {
    return []
  }
  
  const suggestions: string[] = []
  const params = queryResponse.parametros_extraidos || {}

  if (params.vendedor_nome) {
    suggestions.push(`Comparar ${params.vendedor_nome} com a média`)
    suggestions.push(`Quais produtos o vendedor ${params.vendedor_nome} mais vendeu?`)
    suggestions.push(`Qual é a comissão de ${params.vendedor_nome}?`)
  } else if (params.produto_nome) {
    suggestions.push(`Ver estoque de ${params.produto_nome}`)
    suggestions.push(`Qual região comprou mais ${params.produto_nome}?`)
    suggestions.push(`Evolução mensal de vendas de ${params.produto_nome}`)
  } else if (params.cliente_nome) {
    suggestions.push(`Últimas compras de ${params.cliente_nome}`)
    suggestions.push(`Qual o produto favorito de ${params.cliente_nome}?`)
  }

  if ((params.mes || params.ano) && suggestions.length > 0) {
    suggestions.push('Comparar com o mesmo período do ano passado')
  }

  return suggestions.slice(0, 4)
}

interface ConsistencyError {
  message: string
  type: string
}

function validateResponseConsistency(response: QueryResponse): ConsistencyError[] {
  const errors: ConsistencyError[] = []

  // 1. Rastreabilidade
  if (!response.request_id || !response.query_id) {
    errors.push({
      type: 'TRACEABILITY',
      message: 'ID de requisição (request_id) ou ID de consulta ausente.'
    })
  }

  // Se não há dados de BI, não há o que validar numericamente
  if (!response.bi_intelligence) return errors

  const kpis = response.bi_intelligence.kpis
  if (!kpis) return errors

  const iaText = response.ia_analise || ''
  const iaTextLower = iaText.toLowerCase()

  // 2. Validação de KPI de Receita/Faturamento
  const userAskedAboutRevenue = /faturamento|receita|faturado|arrecadado|ganho/i.test(response.pergunta_original || '')
  if (userAskedAboutRevenue && kpis.receita_total !== undefined && kpis.receita_total > 0) {
    const valRaw = Math.round(kpis.receita_total)
    const mentionsRevenue = /receita|faturamento/i.test(iaText)
    const mentionsMoney = /R\$/i.test(iaText)
    if (mentionsRevenue && mentionsMoney) {
      const searchStr = valRaw.toString()
      const isPresent = iaText.replace(/[\s\.,]/g, '').includes(searchStr)
      if (!isPresent && valRaw > 1000) {
        // Tenta abreviação em milhares
        const valK = `${Math.round(valRaw / 1000)}k`
        
        // Tenta abreviação em milhões
        const valM = (valRaw / 1000000).toFixed(2).replace('.', ',')
        const valM_dot = (valRaw / 1000000).toFixed(2)
        const hasM = iaTextLower.includes(`${valM} m`) || iaTextLower.includes(`${valM}mi`) || iaTextLower.includes(`${valM} milh`) ||
                    iaTextLower.includes(`${valM_dot} m`) || iaTextLower.includes(`${valM_dot}mi`) || iaTextLower.includes(`${valM_dot} milh`)
        
        // Tenta abreviação em bilhões
        const valB = (valRaw / 1000000000).toFixed(2).replace('.', ',')
        const valB_dot = (valRaw / 1000000000).toFixed(2)
        const hasB = iaTextLower.includes(`${valB} b`) || iaTextLower.includes(`${valB}bi`) || iaTextLower.includes(`${valB} bilh`) ||
                    iaTextLower.includes(`${valB_dot} b`) || iaTextLower.includes(`${valB_dot}bi`) || iaTextLower.includes(`${valB_dot} bilh`)
                    
        // Arredondamento alternativo para 1 casa decimal
        const valB_1 = (valRaw / 1000000000).toFixed(1).replace('.', ',')
        const valB_1_dot = (valRaw / 1000000000).toFixed(1)
        const hasB_1 = iaTextLower.includes(`${valB_1} b`) || iaTextLower.includes(`${valB_1}bi`) || iaTextLower.includes(`${valB_1} bilh`) ||
                      iaTextLower.includes(`${valB_1_dot} b`) || iaTextLower.includes(`${valB_1_dot}bi`) || iaTextLower.includes(`${valB_1_dot} bilh`)

        if (!iaText.toLowerCase().includes(valK) && !hasM && !hasB && !hasB_1) {
          errors.push({
            type: 'KPI_MISMATCH',
            message: `Inconsistência Numérica: O relatório da IA menciona faturamento/receita, mas o valor real do backend (R$ ${kpis.receita_total.toLocaleString('pt-BR')}) não foi citado.`
          })
        }
      }
    }
  }

  // 3. Validação de Ticket Médio
  const userAskedAboutTicket = /ticket|médio|medio/i.test(response.pergunta_original || '')
  if (userAskedAboutTicket && kpis.ticket_medio !== undefined && kpis.ticket_medio > 0) {
    const valRaw = Math.round(kpis.ticket_medio)
    const mentionsTicket = /ticket/i.test(iaText)
    const mentionsMoney = /R\$/i.test(iaText)
    if (mentionsTicket && mentionsMoney) {
      const searchStr = valRaw.toString()
      const isPresent = iaText.replace(/[\s\.,]/g, '').includes(searchStr)
      if (!isPresent) {
        errors.push({
          type: 'TICKET_MISMATCH',
          message: `Inconsistência Numérica: O relatório da IA menciona ticket médio, mas o valor real do backend (R$ ${kpis.ticket_medio.toLocaleString('pt-BR')}) não foi citado.`
        })
      }
    }
  }

  return errors
}

// ── Universal Chart Data Converter ─────────────────────────────
function convertDataToTargetChartType(baseData: any, targetType: ChartType): any {
  if (!baseData) return baseData

  if (targetType === 'PIE') {
    if (baseData.labels && baseData.datasets?.[0]?.data) {
      return {
        labels: baseData.labels,
        values: baseData.datasets[0].data,
      }
    }
    if (baseData.columns && baseData.rows) {
      const colKey0 = baseData.columns[0]?.key || 'label'
      const colKey1 = baseData.columns[1]?.key || 'value'
      return {
        labels: baseData.rows.map((r: any) => String(r[colKey0])),
        values: baseData.rows.map((r: any) => Number(r[colKey1]) || 0),
      }
    }
    return baseData
  }

  if (targetType === 'BAR' || targetType === 'LINE' || targetType === 'AREA') {
    if (baseData.labels && baseData.values) {
      return {
        labels: baseData.labels,
        datasets: [{ label: 'Total', data: baseData.values }],
      }
    }
    if (baseData.columns && baseData.rows) {
      const colKey0 = baseData.columns[0]?.key || 'label'
      const colKey1 = baseData.columns[1]?.key || 'value'
      return {
        labels: baseData.rows.map((r: any) => String(r[colKey0])),
        datasets: [{ label: baseData.columns[1]?.label || 'Valor', data: baseData.rows.map((r: any) => Number(r[colKey1]) || 0) }],
      }
    }
    return baseData
  }

  if (targetType === 'TABLE') {
    if (baseData.labels && baseData.datasets) {
      const columns = [
        { key: 'item', label: 'Item / Rótulo' },
        ...baseData.datasets.map((ds: any, i: number) => ({ key: `val_${i}`, label: ds.label || `Valor ${i + 1}` })),
      ]
      const rows = baseData.labels.map((lbl: string, idx: number) => {
        const row: any = { item: lbl }
        baseData.datasets.forEach((ds: any, i: number) => {
          row[`val_${i}`] = ds.data?.[idx] ?? 0
        })
        return row
      })
      return { columns, rows }
    }
    if (baseData.labels && baseData.values) {
      return {
        columns: [{ key: 'categoria', label: 'Categoria' }, { key: 'valor', label: 'Valor Total' }],
        rows: baseData.labels.map((lbl: string, i: number) => ({ categoria: lbl, valor: baseData.values[i] })),
      }
    }
    return baseData
  }

  if (targetType === 'KPI') {
    let total = 0
    if (baseData.datasets?.[0]?.data) {
      total = baseData.datasets[0].data.reduce((a: number, b: number) => a + Number(b || 0), 0)
    } else if (baseData.values) {
      total = baseData.values.reduce((a: number, b: number) => a + Number(b || 0), 0)
    }
    return {
      kpis: [
        {
          label: 'Total Consolidado',
          value: total,
          value_formatado: 'R$ ' + total.toLocaleString('pt-BR', { minimumFractionDigits: 2 }),
          unit: 'BRL',
          trend: 'up',
          trend_label: 'Soma dos registros exibidos',
        },
      ],
    }
  }

  return baseData
}

// ── Main Component ─────────────────────────────────────────────
interface AssistantResponseBlockProps {
  msg: ChatMessage
  onFavorite: () => void
  isFavorited: boolean
  onSendQuery: (pergunta: string) => void
  isLatest?: boolean
}

export function AssistantResponseBlock({
  msg,
  onFavorite,
  isFavorited,
  onSendQuery,
  isLatest = true,
}: AssistantResponseBlockProps) {
  const { user } = useAuth()
  const displayContent = repairTextEncoding(msg.content)
  const { sections, isStructured } = parseBIAnalysis(displayContent)
  const [activeTab, setActiveTab] = useState<'visual' | 'table'>('visual')
  const [selectedFormat, setSelectedFormat] = useState<ChartType | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [drillDownKey, setDrillDownKey] = useState<string | null>(null)
  const [showTrendLine, setShowTrendLine] = useState(false)
  const [showOutliers, setShowOutliers] = useState(false)
  const [showAdminDiagnostics, setShowAdminDiagnostics] = useState(false)
  const [showAppliedPreferences, setShowAppliedPreferences] = useState(true)

  const response = msg.queryResponse
  const uniqueId = `response-block-${msg.id}`

  const drillDownData = useMemo(() => {
    if (!drillDownKey || !response?.bi_intelligence?.datasets?.[drillDownKey]) {
      return response?.chart_data
    }
    const groupData = response.bi_intelligence.datasets[drillDownKey] as Array<{ segmento: string; total: number }>
    const labels = groupData.map(item => item.segmento)
    const values = groupData.map(item => item.total)
    return {
      labels,
      datasets: [
        {
          label: `Total por ${drillDownKey.replace('_', ' ').toUpperCase()}`,
          data: values,
          backgroundColor: 'rgba(108, 99, 255, 0.8)',
          borderColor: '#6C63FF',
          borderWidth: 2
        }
      ],
      resumo: {
        total_periodo: values.reduce((a, b) => a + b, 0),
        media_mensal: values.reduce((a, b) => a + b, 0) / (values.length || 1)
      }
    }
  }, [drillDownKey, response])

  // Dados adaptados dinamicamente para o modelo escolhido pelo usuário
  const adaptedDataForFormat = useMemo(() => {
    if (!selectedFormat) return drillDownData
    return convertDataToTargetChartType(drillDownData, selectedFormat)
  }, [drillDownData, selectedFormat])

  const chartDataWithTrend = useMemo(() => {
    const baseData = drillDownData
    if (!showTrendLine || !baseData || !response?.bi_intelligence?.time_series?.media_movel_3p) {
      return baseData
    }
    if (!baseData || !('datasets' in baseData) || !('labels' in baseData)) {
      return baseData
    }
    const maData = response.bi_intelligence.time_series.media_movel_3p
    if (maData.length === baseData.labels.length) {
      return {
        ...baseData,
        datasets: [
          ...baseData.datasets,
          {
            label: 'Média Móvel (3p)',
            data: maData,
            borderColor: '#FF6B6B',
            backgroundColor: 'rgba(255, 107, 107, 0.1)',
            type: 'line',
            tension: 0.4,
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 3
          }
        ]
      }
    }
    return baseData
  }, [drillDownData, showTrendLine, response])

  const finalChartData = useMemo(() => {
    const data = chartDataWithTrend
    if (!showOutliers || !data || !response?.bi_intelligence?.anomalies?.length) {
      return data
    }
    if (!data || !('datasets' in data) || !('labels' in data)) {
      return data
    }
    const anomalies = response.bi_intelligence.anomalies as Array<{ item: string }>
    const anomalyLabels = new Set(anomalies.map(a => a.item))
    
    const newDatasets = data.datasets.map(ds => {
      if (ds.type === 'line') return ds
      const colors = data.labels.map(lbl => 
        anomalyLabels.has(lbl) ? '#EF4444' : (ds.borderColor || '#6C63FF')
      )
      return {
        ...ds,
        backgroundColor: colors
      }
    })
    return {
      ...data,
      datasets: newDatasets
    }
  }, [chartDataWithTrend, showOutliers, response])

  const handleCopy = () => {
    navigator.clipboard.writeText(displayContent)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleCSVExport = () => {
    if (!response?.chart_data) return
    const tableData = response.visualizations?.find(v => v.chart_type === 'TABLE')?.chart_data || response.chart_data
    if ('columns' in tableData && 'rows' in tableData) {
      exportToCSV(response.view_name || 'relatorio', tableData.columns, tableData.rows)
    }
  }

  const handleExcelExport = () => {
    if (!response?.chart_data) return
    const tableData = response.visualizations?.find(v => v.chart_type === 'TABLE')?.chart_data || response.chart_data
    if ('columns' in tableData && 'rows' in tableData) {
      exportToExcel(response.view_name || 'relatorio', tableData.columns, tableData.rows)
    }
  }

  const handlePDFExport = () => {
    exportToPDF(uniqueId, response?.view_name || 'Relatorio Executivo LuminaAI')
  }

  // Helper properties
  const consistencyErrors = useMemo(() => {
    if (!response) return []
    const errs = validateResponseConsistency(response)
    if (errs.length > 0) {
      console.warn("[WARN] LuminaAI Consistency notice:", errs)
    }
    return errs
  }, [response])

  const kpis = parseKPIsFromMarkdown(sections.kpis)
  const showTabs =
    response?.chart_type &&
    response.chart_type !== 'TABLE' &&
    response.chart_type !== 'KPI' &&
    !!response.visualizations?.some(v => v.chart_type === 'TABLE')

  const hasData = Boolean(response?.chart_data && response?.chart_type)

  // Se a resposta exigir esclarecimentos ou escolhas (AMBIGUOUS / MISSING_INFORMATION),
  // exibe EXCLUSIVAMENTE a janela popup flutuante (via Portal), sem concatenar bolhas no chat.
  const isClarificationRequired =
    isLatest &&
    (response?.status === 'AMBIGUOUS' ||
      response?.status === 'MISSING_INFORMATION' ||
      response?.status === 'CLARIFICATION_REQUIRED' ||
      (isClarificationData(response?.chart_data) && Boolean(response.chart_data.clarification_required)))

  if (isClarificationRequired) {
    const ambOptions =
      response?.ambiguities && response.ambiguities.length > 0
        ? response.ambiguities
        : isClarificationData(response?.chart_data) && Array.isArray(response?.chart_data?.options)
          ? response.chart_data.options
          : []

    return (
      <ClarificationPanel
        status={response?.status || 'AMBIGUOUS'}
        ambiguities={ambOptions}
        missingInformation={response?.missing_information || []}
        semanticClarification={response?.semantic_clarification}
        perguntaOriginal={response?.pergunta_original || displayContent}
        onResolve={onSendQuery}
      />
    )
  }

  return (
    <div className="flex items-start gap-4 animate-fade-in w-full max-w-5xl mx-auto">
      {/* Sparkles / Assistant Avatar */}
      <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 bg-zinc-900 border border-zinc-800/80 shadow-md">
        <Sparkles size={16} className="text-indigo-400 animate-pulse" />
      </div>

      {/* Main Response Container */}
      <div
        id={uniqueId}
        className="lumina-response-theme-scope flex-1 min-w-0 border rounded-3xl p-4 sm:p-6 shadow-xl space-y-6"
        style={{
          background: 'rgb(var(--bg-surface) / 0.86)',
          borderColor: 'rgb(var(--border) / 0.55)',
        }}
      >
        
        {/* Header toolbar */}
        <div
          className="flex items-center justify-between pb-3 border-b no-print"
          style={{ borderColor: 'rgb(var(--border) / 0.45)' }}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-zinc-400 uppercase tracking-widest">
              LuminaAI BI Core
            </span>
            {response?.view_name && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 font-semibold border border-indigo-900/40">
                {response.view_name.replace('VW_', '')}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Copy button */}
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900/60 transition-all duration-200"
              title="Copiar relatório"
            >
              {copied ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}
            </button>

            {/* Export options */}
            {hasData && (
              <>
                <button
                  onClick={handleCSVExport}
                  className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900/60 transition-all duration-200"
                  title="Exportar CSV"
                >
                  <FileSpreadsheet size={14} />
                </button>
                <button
                  onClick={handleExcelExport}
                  className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900/60 transition-all duration-200"
                  title="Exportar Excel"
                >
                  <FileText size={14} />
                </button>
              </>
            )}

            {/* PDF print button */}
            <button
              onClick={handlePDFExport}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900/60 transition-all duration-200"
              title="Imprimir PDF"
            >
              <Download size={14} />
            </button>

            {/* Favorite button */}
            {response?.pode_favoritar && (
              <button
                onClick={onFavorite}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-yellow-400 hover:bg-zinc-900/60 transition-all duration-200"
                title={isFavorited ? 'Remover Favorito' : 'Salvar nos Favoritos'}
              >
                {isFavorited ? (
                  <Star size={14} className="fill-yellow-400 text-yellow-400" />
                ) : (
                  <StarOff size={14} />
                )}
              </button>
            )}
          </div>
        </div>

        {response?.data_status && (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] no-print">
            <span className="inline-flex items-center gap-1.5 text-zinc-400">
              <Database size={12} className="text-cyan-400" />
              {repairTextEncoding(response.data_status.source_label)}
            </span>
            <span className="inline-flex items-center gap-1.5 text-zinc-400">
              <Clock3 size={12} />
              {response.data_status.synced_at
                ? `Atualizado em ${new Date(response.data_status.synced_at).toLocaleString('pt-BR')}`
                : 'Horário de atualização indisponível'}
            </span>
            {response.validation_summary && (
              <span className={cn(
                'inline-flex items-center gap-1.5 font-semibold',
                response.validation_summary.status === 'PASSED' ? 'text-emerald-400' : 'text-red-400',
              )}>
                <ShieldCheck size={12} />
                {response.validation_summary.status === 'PASSED'
                  ? `${response.validation_summary.checks_passed} verificações aprovadas`
                  : `${response.validation_summary.checks_failed} verificações falharam`}
              </span>
            )}
          </div>
        )}

        {/* ── 0. Erro de Consistência (Single Source of Truth) ── */}
        {response?.public_context_summary && (
          <div
            className="flex flex-wrap items-center gap-x-4 gap-y-2 border-y py-2.5 text-[11px] no-print"
            style={{ borderColor: 'rgb(var(--border) / 0.35)' }}
            data-testid="public-context-summary"
          >
            <span className="inline-flex items-center gap-1.5 font-semibold text-zinc-300">
              <Compass size={12} className="text-indigo-400" />
              Contexto {response.context_relationship === 'NEW_TOPIC' ? 'iniciado' : 'mantido'}
            </span>
            {response.public_context_summary.active_metrics.map(metric => (
              <span key={`metric-${metric}`} className="text-zinc-400">
                {repairTextEncoding(metric)}
              </span>
            ))}
            {response.public_context_summary.active_periods.map(period => (
              <span key={`period-${period}`} className="text-zinc-400">
                {repairTextEncoding(period)}
              </span>
            ))}
            {response.public_context_summary.active_dimensions.length > 0 && (
              <span className="text-zinc-400">
                Por {response.public_context_summary.active_dimensions.map(repairTextEncoding).join(', ')}
              </span>
            )}
            {response.public_context_summary.inherited_filters.map(filter => (
              <span key={`filter-${filter}`} className="text-cyan-400">
                {repairTextEncoding(filter)}
              </span>
            ))}
            {response.public_context_summary.replaced_fields.length > 0 && (
              <span className="text-amber-400">Filtros atualizados</span>
            )}
            {response.public_context_summary.removed_fields.length > 0 && (
              <span className="text-red-400">Filtros removidos</span>
            )}
          </div>
        )}

        {response?.applied_preference_summary?.applied.length && showAppliedPreferences ? (
          <div
            className="flex flex-wrap items-center gap-2 border-y py-2.5 text-[11px] no-print"
            style={{ borderColor: 'rgb(var(--border) / 0.35)' }}
            data-testid="applied-preference-summary"
            role="status"
            aria-label="Preferências aplicadas do seu perfil"
          >
            <span className="inline-flex items-center gap-1.5 font-semibold text-zinc-300">
              <UserRoundCog size={12} className="text-cyan-400" />
              Aplicado do seu perfil:
            </span>
            {response.applied_preference_summary.applied.map(item => (
              <span key={`${item.preference_type}-${item.label}`} className="text-cyan-300">
                {repairTextEncoding(item.label)}: {repairTextEncoding(item.value_label)}
              </span>
            ))}
            <button
              type="button"
              className="inline-flex h-7 w-7 items-center justify-center rounded-md text-zinc-400 hover:bg-zinc-800 hover:text-white"
              onClick={() => {
                const labels = response.applied_preference_summary?.applied
                  .filter(item => item.removable_this_turn)
                  .map(item => item.label)
                  .join(', ')
                if (labels) onSendQuery(`Nesta análise, não use as preferências: ${labels}.`)
                setShowAppliedPreferences(false)
              }}
              title="Remover preferências desta análise"
              aria-label="Remover preferências desta análise"
            >
              <X size={13} />
            </button>
            <a
              href="/dashboard/settings/profile"
              className="font-semibold text-zinc-300 underline decoration-zinc-600 underline-offset-2 hover:text-white"
            >
              Gerenciar
            </a>
          </div>
        ) : null}

        {consistencyErrors.length > 0 && (
          <div className="bg-red-950/20 border border-red-500/30 rounded-3xl p-6 flex flex-col gap-3">
            <div className="flex items-center gap-2 text-red-400 font-bold text-sm">
              <AlertTriangle size={18} />
              <span>Erro de Consistência de Dados (Single Source of Truth)</span>
            </div>
            <p className="text-xs text-zinc-400">
              O LuminaAI bloqueou a renderização deste painel analítico pois foi detectada uma divergência entre a camada estatística do backend e a interpretação textual gerada pelo modelo de linguagem.
            </p>
            <div className="text-xs font-mono text-red-300/80 bg-red-950/30 rounded-xl p-3 border border-red-900/40 whitespace-pre-line">
              {consistencyErrors.map((e, idx) => `[${e.type}] ${idx + 1}. ${e.message}`).join('\n')}
            </div>
          </div>
        )}

        {consistencyErrors.length === 0 ? (
          <>
            {/* ── 1. Indicadores Principais (KPIs) ── */}
        {isStructured && kpis.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 pt-2">
            {kpis.map((kpi, idx) => (
              <div
                key={idx}
                className="bg-zinc-900/30 border border-zinc-800/40 rounded-2xl p-4 flex flex-col justify-between min-h-[100px] shadow-sm hover:border-zinc-700/60 transition-all duration-300"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider line-clamp-2">
                    {kpi.titulo}
                  </span>
                  <span className="text-lg flex-shrink-0" role="img" aria-label="Icon">
                    {getIconForKPI(kpi.titulo)}
                  </span>
                </div>
                <div className="mt-2 flex items-baseline justify-between gap-2">
                  <span className="text-lg font-bold text-white truncate">
                    {kpi.valor}
                  </span>
                  {kpi.variacao && (
                    <div
                      className={cn(
                        "flex items-center gap-0.5 text-xs font-bold px-1.5 py-0.5 rounded-lg flex-shrink-0",
                        kpi.isPositive ? "bg-emerald-950 text-emerald-400 border border-emerald-900/30" : "bg-red-950/60 text-red-400 border border-red-900/30"
                      )}
                    >
                      {kpi.isPositive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                      <span>{kpi.variacao}</span>
                    </div>
                  )}
                </div>
                {kpi.comparacao && (
                  <span className="text-[10px] text-zinc-500 mt-1 truncate">
                    {kpi.comparacao}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* ── 2. Resumo Executivo (Max 5 lines) ── */}
        <div className="space-y-2">
          <p className="text-sm md:text-base leading-relaxed text-zinc-200 line-clamp-5 hover:line-clamp-none transition-all duration-300 cursor-help whitespace-pre-wrap break-words">
            {isStructured ? parseMarkdownBold(sections.resumo) : parseMarkdownBold(displayContent)}
          </p>
        </div>



        {/* ── 3. Análise Comparativa (Subtítulo ou Notas Extras) ── */}
        {isStructured && sections.comparativa && (
          <div className="bg-zinc-900/10 border border-zinc-800/20 rounded-2xl p-4 space-y-1.5">
            <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest flex items-center gap-1.5">
              <ChevronRight size={12} /> Análise Comparativa
            </span>
            <p className="text-xs md:text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap break-words">
              {parseMarkdownBold(sections.comparativa)}
            </p>
          </div>
        )}

        {/* ── 4. Dashboard (Tabelas ou Gráficos) ── */}
        {hasData && (
          <div className="bg-zinc-900/40 border border-white/10 rounded-3xl p-5 flex flex-col gap-4 shadow-xl backdrop-blur-xl">
            
            {/* Toolbar interna do Dashboard com Seletor Interativo de Modelos */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3.5 no-print">
              <div className="flex items-center gap-2">
                <Grid size={15} className="text-cyan-400" />
                <span className="text-xs font-black uppercase tracking-wider text-white">
                  Painel Analítico Interativo
                </span>
                {selectedFormat && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold">
                    Modo: {selectedFormat}
                  </span>
                )}
              </div>

              {/* Controles de Modelo Visual */}
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider hidden sm:inline mr-1">
                  Alterar Visualização:
                </span>

                <button
                  type="button"
                  onClick={() => setSelectedFormat('BAR')}
                  className={cn(
                    "px-2.5 py-1 text-xs rounded-lg border transition-all cursor-pointer flex items-center gap-1.5",
                    selectedFormat === 'BAR' || (!selectedFormat && response?.chart_type === 'BAR')
                      ? "border-cyan-500 bg-cyan-500/20 text-cyan-300 font-bold shadow-[0_0_10px_rgba(6,182,212,0.3)]"
                      : "border-white/10 bg-zinc-900/60 text-zinc-400 hover:text-white hover:border-white/20"
                  )}
                  title="Gráfico de Barras"
                >
                  <BarChart3 size={13} />
                  <span>Barras</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedFormat('LINE')}
                  className={cn(
                    "px-2.5 py-1 text-xs rounded-lg border transition-all cursor-pointer flex items-center gap-1.5",
                    selectedFormat === 'LINE' || (!selectedFormat && response?.chart_type === 'LINE')
                      ? "border-cyan-500 bg-cyan-500/20 text-cyan-300 font-bold shadow-[0_0_10px_rgba(6,182,212,0.3)]"
                      : "border-white/10 bg-zinc-900/60 text-zinc-400 hover:text-white hover:border-white/20"
                  )}
                  title="Gráfico de Linhas"
                >
                  <TrendingUp size={13} />
                  <span>Linhas</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedFormat('PIE')}
                  className={cn(
                    "px-2.5 py-1 text-xs rounded-lg border transition-all cursor-pointer flex items-center gap-1.5",
                    selectedFormat === 'PIE' || (!selectedFormat && response?.chart_type === 'PIE')
                      ? "border-cyan-500 bg-cyan-500/20 text-cyan-300 font-bold shadow-[0_0_10px_rgba(6,182,212,0.3)]"
                      : "border-white/10 bg-zinc-900/60 text-zinc-400 hover:text-white hover:border-white/20"
                  )}
                  title="Gráfico de Pizza / Donut"
                >
                  <PieChart size={13} />
                  <span>Pizza</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedFormat('TABLE')}
                  className={cn(
                    "px-2.5 py-1 text-xs rounded-lg border transition-all cursor-pointer flex items-center gap-1.5",
                    selectedFormat === 'TABLE' || (!selectedFormat && response?.chart_type === 'TABLE')
                      ? "border-cyan-500 bg-cyan-500/20 text-cyan-300 font-bold shadow-[0_0_10px_rgba(6,182,212,0.3)]"
                      : "border-white/10 bg-zinc-900/60 text-zinc-400 hover:text-white hover:border-white/20"
                  )}
                  title="Planilha / Tabela Dinâmica"
                >
                  <Table2 size={13} />
                  <span>Planilha</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedFormat('KPI')}
                  className={cn(
                    "px-2.5 py-1 text-xs rounded-lg border transition-all cursor-pointer flex items-center gap-1.5",
                    selectedFormat === 'KPI' || (!selectedFormat && response?.chart_type === 'KPI')
                      ? "border-cyan-500 bg-cyan-500/20 text-cyan-300 font-bold shadow-[0_0_10px_rgba(6,182,212,0.3)]"
                      : "border-white/10 bg-zinc-900/60 text-zinc-400 hover:text-white hover:border-white/20"
                  )}
                  title="Cards de Indicadores"
                >
                  <Gauge size={13} />
                  <span>Cards</span>
                </button>

                {selectedFormat && (
                  <button
                    type="button"
                    onClick={() => setSelectedFormat(null)}
                    className="p-1 rounded-lg border border-white/10 bg-zinc-800/80 text-zinc-400 hover:text-white hover:bg-zinc-700 transition-all cursor-pointer"
                    title="Restaurar layout original da IA"
                  >
                    <RotateCcw size={13} />
                  </button>
                )}

                {/* Expand button */}
                <button
                  onClick={() => setIsModalOpen(true)}
                  className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white ml-1 cursor-pointer"
                  title="Expandir em tela cheia"
                >
                  <Maximize2 size={14} />
                </button>
              </div>
            </div>

            {/* ── Motor de Renderização Interativo ── */}
            <ErrorBoundary>
              {selectedFormat ? (
                <div className="w-full min-h-[300px]">
                  <DynamicRenderer
                    chartType={selectedFormat}
                    chartData={adaptedDataForFormat}
                    title={response?.view_name ?? undefined}
                  />
                </div>
              ) : (
                <InlineDashboardRuntime
                  response={response!}
                  className="w-full"
                />
              )}
            </ErrorBoundary>

            {/* ── Painel Proativo de Clarificação e Perguntas Essenciais de Negócio ── */}
            <div className="mt-2 p-4 rounded-2xl border border-cyan-500/30 bg-zinc-950/80 backdrop-blur-md flex flex-col gap-3 no-print">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-xs font-bold text-cyan-300">
                  <Sparkles size={14} className="text-cyan-400 animate-pulse" />
                  <span>Personalize o Modelo ou Explore Regras de Negócio:</span>
                </div>
                <span className="text-[10px] text-zinc-500 font-mono">1-Clique IA</span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => onSendQuery(`Apresentar estes mesmos dados com cálculo de faturamento líquido (deduzindo devoluções e cancelamentos): ${response?.pergunta_original || displayContent.slice(0, 35)}`)}
                  className="px-3 py-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-xs font-semibold text-emerald-300 transition-all hover:scale-102 cursor-pointer flex items-center gap-1.5"
                >
                  <span>💵 Faturamento Líquido</span>
                </button>

                <button
                  type="button"
                  onClick={() => onSendQuery(`Apresentar com base no faturamento bruto total de emissão: ${response?.pergunta_original || displayContent.slice(0, 35)}`)}
                  className="px-3 py-1.5 rounded-xl border border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20 text-xs font-semibold text-blue-300 transition-all hover:scale-102 cursor-pointer flex items-center gap-1.5"
                >
                  <span>💰 Faturamento Bruto</span>
                </button>

                <button
                  type="button"
                  onClick={() => onSendQuery(`Apresentar em formato de planilha detalhada com todas as colunas: ${response?.pergunta_original || displayContent.slice(0, 35)}`)}
                  className="px-3 py-1.5 rounded-xl border border-purple-500/30 bg-purple-500/10 hover:bg-purple-500/20 text-xs font-semibold text-purple-300 transition-all hover:scale-102 cursor-pointer flex items-center gap-1.5"
                >
                  <Table2 size={12} />
                  <span>Planilha Completa</span>
                </button>

                <button
                  type="button"
                  onClick={() => onSendQuery(`Comparar estes resultados distribuídos por filial: ${response?.pergunta_original || displayContent.slice(0, 35)}`)}
                  className="px-3 py-1.5 rounded-xl border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 text-xs font-semibold text-cyan-300 transition-all hover:scale-102 cursor-pointer flex items-center gap-1.5"
                >
                  <span>🏢 Segmentar por Filial</span>
                </button>

                <button
                  type="button"
                  onClick={() => onSendQuery(`Ver ranking dos vendedores envolvidos nesta métrica: ${response?.pergunta_original || displayContent.slice(0, 35)}`)}
                  className="px-3 py-1.5 rounded-xl border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-xs font-semibold text-indigo-300 transition-all hover:scale-102 cursor-pointer flex items-center gap-1.5"
                >
                  <span>👥 Top Vendedores</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {!!response?.interaction_options?.length && (
          <div className="flex flex-wrap items-center gap-2 no-print">
            {response.interaction_options.map(option => (
              <button
                key={option.id}
                type="button"
                onClick={() => onSendQuery(option.prompt)}
                className="px-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900/40 text-xs text-zinc-300 hover:text-white hover:border-indigo-700 transition-colors"
              >
                {repairTextEncoding(option.label)}
              </button>
            ))}
          </div>
        )}

        {response && <FeedbackControls response={response} />}

        {user?.role === 'ADMIN' && response?.admin_diagnostics && (
          <div className="border border-zinc-800 rounded-xl overflow-hidden no-print">
            <button
              type="button"
              onClick={() => setShowAdminDiagnostics(value => !value)}
              className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-zinc-900/40 transition-colors"
            >
              <span className="inline-flex items-center gap-2 text-xs font-semibold text-zinc-300">
                <Wrench size={13} className="text-indigo-400" />
                Diagnóstico técnico da resposta
              </span>
              {showAdminDiagnostics ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {showAdminDiagnostics && (
              <pre className="max-h-96 overflow-auto border-t border-zinc-800 p-4 text-[11px] leading-relaxed text-zinc-400 whitespace-pre-wrap break-words">
                {JSON.stringify(response.admin_diagnostics, null, 2)}
              </pre>
            )}
          </div>
        )}

        {/* ── 5. Insights Estratégicos ── */}
        {isStructured && (sections.insights || sections.riscos || sections.oportunidades) && (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
            {/* Insights panel */}
            {sections.insights && (
              <div className="bg-indigo-950/15 border border-indigo-900/30 rounded-2xl p-5 space-y-2 shadow-sm">
                <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest flex items-center gap-1.5">
                  <ChevronRight size={12} /> Insights Estratégicos
                </span>
                <p className="text-xs md:text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap break-words">
                  {parseMarkdownBold(sections.insights)}
                </p>
              </div>
            )}

            {/* Riscos panel */}
            {sections.riscos && (
              <div className="bg-rose-950/10 border border-rose-900/30 rounded-2xl p-5 space-y-2 shadow-sm">
                <span className="text-[10px] font-bold text-rose-400 uppercase tracking-widest flex items-center gap-1.5">
                  <AlertTriangle size={12} className="text-rose-400" /> Riscos e Desvios
                </span>
                <p className="text-xs md:text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap break-words">
                  {parseMarkdownBold(sections.riscos)}
                </p>
              </div>
            )}

            {/* Oportunidades panel */}
            {sections.oportunidades && (
              <div className="bg-emerald-950/10 border border-emerald-900/30 rounded-2xl p-5 space-y-2 shadow-sm">
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest flex items-center gap-1.5">
                  <Compass size={12} className="text-emerald-400" /> Oportunidades
                </span>
                <p className="text-xs md:text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap break-words">
                  {parseMarkdownBold(sections.oportunidades)}
                </p>
              </div>
            )}
          </div>
        )}

        {/* ── 6. Recomendações Executivas ── */}
        {isStructured && sections.recomendacoes && (
          <div className="bg-violet-950/10 border border-violet-900/30 rounded-2xl p-5 space-y-3">
            <span className="text-[10px] font-bold text-violet-400 uppercase tracking-widest flex items-center gap-1.5">
              <CheckCircle2 size={12} className="text-violet-400" /> Recomendações Práticas
            </span>
            <p className="text-xs md:text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap break-words">
              {parseMarkdownBold(sections.recomendacoes)}
            </p>
          </div>
        )}

        {/* ── 7. Observações Finais ── */}
        {isStructured && sections.observacoes && (
          <div className="text-[11px] text-zinc-500 italic border-l-2 border-zinc-800 pl-3 leading-relaxed whitespace-pre-wrap break-words">
            {parseMarkdownBold(sections.observacoes)}
          </div>
        )}

        {/* ── 8. Sugestões de Próximas Perguntas (no-print) ── */}
        {(() => {
          const suggestions = generateSuggestions(response)
          if (suggestions.length === 0) return null
          return (
            <div className="pt-4 border-t border-zinc-900/60 no-print">
              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-2.5">
                Investigar aprofundamento do cenário:
              </span>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((sug, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSendQuery(sug)}
                    className="text-xs px-3.5 py-2 rounded-xl bg-zinc-900/40 hover:bg-zinc-900 border border-zinc-850 hover:border-zinc-700/80 text-zinc-300 hover:text-white cursor-pointer transition-all duration-250 active:scale-95 flex items-center gap-1.5 shadow-sm"
                  >
                    <span>{sug}</span>
                    <ChevronRight size={12} className="text-zinc-500 group-hover:text-white" />
                  </button>
                ))}
              </div>
            </div>
          )
        })()}
          </>
        ) : (
          <div className="text-xs text-zinc-500 italic pt-2">
            Rastreabilidade da sessão: ID {response?.request_id || 'N/A'}. A visualização analítica foi suprimida para preservar a integridade das métricas do negócio.
          </div>
        )}

      </div>

      {/* ── Modal Expandido em Tela Cheia ── */}
      <AnimatePresence>
        {isModalOpen && response && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 md:p-8 no-print">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-7xl max-h-[94vh] rounded-3xl border border-zinc-800 bg-zinc-950 p-6 md:p-8 overflow-y-auto flex flex-col gap-6 shadow-2xl"
            >
              {/* Modal Top Bar */}
              <div className="flex items-center justify-between gap-4 pb-4 border-b border-zinc-900">
                <div>
                  <h2 className="text-lg font-bold text-white">
                    {response.view_name ? response.view_name.replace('VW_', '') : 'Painel Analítico'}
                  </h2>
                  <p className="text-xs text-zinc-400 mt-1">
                    Visualização estendida dos dados reais e ferramentas analíticas interativas.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setIsModalOpen(false)
                    setDrillDownKey(null)
                    setShowTrendLine(false)
                    setShowOutliers(false)
                  }}
                  className="w-10 h-10 rounded-xl flex items-center justify-center transition-all bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Grid Layout: Left Panel (75%) vs Right Sidebar (25%) */}
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
                
                {/* Left Panel: Chart & Table (3 cols) */}
                <div className="lg:col-span-3 flex flex-col gap-6 w-full">
                  
                  {/* Graphic container */}
                  <div className="w-full min-h-[400px] bg-zinc-900/10 rounded-2xl p-6 border border-zinc-900/80">
                    <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-widest mb-4">
                      Visualização Gráfica Ampliada
                    </h4>
                    <div className="w-full h-[400px]">
                      <DynamicRenderer
                        chartType={drillDownKey ? 'BAR' : response.chart_type!}
                        chartData={finalChartData as AnyChartData | null}
                        visualizations={drillDownKey ? null : response.visualizations}
                        title={response.view_name || 'Gráfico'}
                      />
                    </div>
                  </div>

                  {/* Data Table */}
                  <div className="w-full flex flex-col gap-4 border-t border-zinc-900 pt-6">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Tabela Detalhada
                      </h3>
                      <p className="text-xs text-zinc-400">
                        Todos os registros correspondentes da consulta analítica do banco.
                      </p>
                    </div>
                    <div className="w-full overflow-hidden rounded-2xl border border-zinc-900 bg-zinc-900/10">
                      {(() => {
                        const tableData = response.visualizations?.find(v => v.chart_type === 'TABLE')?.chart_data ?? response.chart_data
                        if (tableData && isChartDataTable(tableData)) {
                          return <DataTable data={tableData} />
                        }
                        return (
                          <p className="text-xs text-center p-8 text-zinc-500">
                            Nenhuma tabela de dados disponível para esta visualização.
                          </p>
                        )
                      })()}
                    </div>
                  </div>

                </div>

                {/* Right Panel: Control Sidebar (1 col) */}
                <div className="bg-zinc-900/20 border border-zinc-800/40 rounded-3xl p-5 flex flex-col gap-5">
                  <h4 className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest border-b border-zinc-900 pb-2.5">
                    Plugins BI & Interações
                  </h4>

                  {/* Drill-down Key Selection */}
                  {response.bi_intelligence?.datasets && Object.keys(response.bi_intelligence.datasets).length > 0 && (
                    <div className="space-y-2.5">
                      <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block">
                        Drill-down Hierárquico:
                      </span>
                      <div className="flex flex-col gap-1.5">
                        <button
                          onClick={() => setDrillDownKey(null)}
                          className={cn(
                            "w-full text-left text-xs py-2 px-3 rounded-xl border transition-all cursor-pointer",
                            drillDownKey === null
                              ? "bg-indigo-950/20 border-indigo-500/40 text-indigo-300 font-semibold"
                              : "bg-zinc-900/40 border-transparent text-zinc-400 hover:bg-zinc-900 hover:text-white"
                          )}
                        >
                          ● Visão Original
                        </button>
                        {Object.keys(response.bi_intelligence.datasets).map((catKey) => (
                          <button
                            key={catKey}
                            onClick={() => setDrillDownKey(catKey)}
                            className={cn(
                              "w-full text-left text-xs py-2 px-3 rounded-xl border transition-all cursor-pointer",
                              drillDownKey === catKey
                                ? "bg-indigo-950/20 border-indigo-500/40 text-indigo-300 font-semibold"
                                : "bg-zinc-900/40 border-transparent text-zinc-400 hover:bg-zinc-900 hover:text-white"
                            )}
                          >
                            ↳ Agrupar por {catKey.replace('_', ' ').toUpperCase()}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Trend line Toggle */}
                  {response.bi_intelligence?.time_series?.media_movel_3p && (
                    <div className="space-y-2 pt-2 border-t border-zinc-900">
                      <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block">
                        Filtros de Tendência:
                      </span>
                      <label className="flex items-center gap-2.5 text-xs text-zinc-300 hover:text-white cursor-pointer py-1">
                        <input
                          type="checkbox"
                          checked={showTrendLine}
                          onChange={(e) => setShowTrendLine(e.target.checked)}
                          className="w-4 h-4 rounded border-zinc-800 bg-zinc-900 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        <span>Exibir Média Móvel (3p)</span>
                      </label>
                    </div>
                  )}

                  {/* Outliers highlighting */}
                  {response.bi_intelligence?.anomalies && (
                    <div className="space-y-2 pt-2 border-t border-zinc-900">
                      <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block">
                        Detecção Estatística:
                      </span>
                      <label className="flex items-center gap-2.5 text-xs text-zinc-300 hover:text-white cursor-pointer py-1">
                        <input
                          type="checkbox"
                          checked={showOutliers}
                          onChange={(e) => setShowOutliers(e.target.checked)}
                          className="w-4 h-4 rounded border-zinc-800 bg-zinc-900 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        <span>Destacar Outliers (Z &gt; 1.5)</span>
                      </label>

                      {/* Outliers detailed list */}
                      {response.bi_intelligence.anomalies.length > 0 ? (
                        <div className="max-h-[160px] overflow-y-auto space-y-1.5 mt-2 pr-1 scrollbar-thin">
                          {response.bi_intelligence.anomalies.map((anom: BIAnomaly, aIdx: number) => (
                            <div key={aIdx} className="bg-rose-950/20 border border-rose-900/30 rounded-xl p-2.5 space-y-1 shadow-sm">
                              <div className="flex items-center justify-between text-[10px] font-bold text-rose-400">
                                <span>{anom.item}</span>
                                <span>Z = {anom.desvio_z}</span>
                              </div>
                              <p className="text-[10px] text-zinc-400 leading-normal">
                                {anom.tipo}: {anom.justificativa}
                              </p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-[10px] text-zinc-500 italic mt-1">
                          Nenhum outlier detectado neste cenário.
                        </p>
                      )}
                    </div>
                  )}

                  {/* IA Deep Analysis Button */}
                  <div className="pt-3 border-t border-zinc-900 flex flex-col gap-2">
                    <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block">
                      Aprofundamento IA:
                    </span>
                    <button
                      onClick={() => {
                        const view = response.view_name ? response.view_name.replace('VW_', '') : 'cenário';
                        const metric = drillDownKey ? `agrupada por ${drillDownKey}` : 'original';
                        onSendQuery(`Quero uma análise preditiva e de comportamento estratégico para a análise de ${view} (${metric})`);
                        setIsModalOpen(false);
                      }}
                      className="w-full text-center text-xs py-2 px-3 rounded-xl bg-indigo-650 hover:bg-indigo-600 active:scale-95 font-semibold text-white shadow-md transition-all cursor-pointer flex items-center justify-center gap-1.5"
                    >
                      <Sparkles size={12} />
                      <span>Gerar Insight Drill-down</span>
                    </button>
                  </div>

                </div>

              </div>

            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  )
}
