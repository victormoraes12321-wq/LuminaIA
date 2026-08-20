import { jsPDF } from 'jspdf'
import * as XLSX from 'xlsx'
import { repairTextEncoding } from '@/lib/textEncoding'

export interface ExportReportOptions {
  title: string
  subtitle?: string
  queryText?: string
  summaryText?: string
  kpis?: Array<{ titulo: string; valor: string; comparacao?: string }>
  tableHeaders?: string[]
  tableRows?: Array<Array<string | number>>
  fileName?: string
}

/**
 * Gera e baixa um relatório executivo em PDF de alta qualidade para reuniões e diretoria.
 */
export function exportReportToPDF(options: ExportReportOptions) {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  })

  const pageWidth = doc.internal.pageSize.getWidth()
  const margin = 15
  const contentWidth = pageWidth - margin * 2
  let y = 18

  // ── 1. Cabeçalho Executivo Institucional ──
  doc.setFillColor(15, 23, 42) // Dark Navy slate-900
  doc.roundedRect(margin, y, contentWidth, 24, 3, 3, 'F')

  doc.setTextColor(6, 182, 212) // Cyan-400
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(14)
  doc.text('LUMINA AI  •  RELATÓRIO EXECUTIVO', margin + 6, y + 9)

  doc.setTextColor(226, 232, 240) // Slate-200
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  doc.text('Casa do Campo — Inteligência de Negócios & BI', margin + 6, y + 16)

  const dateStr = new Date().toLocaleString('pt-BR')
  doc.setTextColor(148, 163, 184)
  doc.setFontSize(8)
  doc.text(`Emitido em: ${dateStr}`, pageWidth - margin - 6, y + 16, { align: 'right' })

  y += 32

  // ── 2. Título do Relatório & Pergunta ──
  if (options.title) {
    doc.setTextColor(15, 23, 42)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(12)
    doc.text(repairTextEncoding(options.title), margin, y)
    y += 6
  }

  if (options.queryText) {
    doc.setTextColor(71, 85, 105)
    doc.setFont('helvetica', 'italic')
    doc.setFontSize(9)
    const splitQuery = doc.splitTextToSize(`" ${repairTextEncoding(options.queryText)} "`, contentWidth)
    doc.text(splitQuery, margin, y)
    y += splitQuery.length * 4.5 + 4
  }

  // ── 3. KPIs em Grid ──
  if (options.kpis && options.kpis.length > 0) {
    const kpiCount = Math.min(options.kpis.length, 4)
    const kpiWidth = (contentWidth - (kpiCount - 1) * 3) / kpiCount
    const kpiHeight = 16

    options.kpis.slice(0, 4).forEach((kpi, idx) => {
      const kpiX = margin + idx * (kpiWidth + 3)
      doc.setFillColor(241, 245, 249) // Slate-100
      doc.setDrawColor(203, 213, 225) // Slate-300
      doc.roundedRect(kpiX, y, kpiWidth, kpiHeight, 2, 2, 'FD')

      doc.setTextColor(100, 116, 139)
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(7)
      doc.text(repairTextEncoding(kpi.titulo).toUpperCase(), kpiX + 3, y + 5)

      doc.setTextColor(15, 23, 42)
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(10)
      doc.text(repairTextEncoding(kpi.valor), kpiX + 3, y + 12)
    })

    y += kpiHeight + 8
  }

  // ── 4. Resumo & Análise da IA ──
  if (options.summaryText) {
    doc.setFillColor(248, 250, 252)
    doc.setDrawColor(226, 232, 240)
    
    const cleanSummary = options.summaryText
      .replace(/##\s+\d\.\s+[^\n]+/g, '')
      .replace(/\*\*/g, '')
      .trim()
    
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8.5)
    doc.setTextColor(30, 41, 59)
    
    const splitSummary = doc.splitTextToSize(repairTextEncoding(cleanSummary), contentWidth - 8)
    const boxHeight = splitSummary.length * 4.2 + 8

    doc.roundedRect(margin, y, contentWidth, boxHeight, 2, 2, 'FD')
    doc.text(splitSummary, margin + 4, y + 6)
    y += boxHeight + 8
  }

  // ── 5. Tabela de Dados ──
  if (options.tableHeaders && options.tableRows && options.tableRows.length > 0) {
    doc.setTextColor(15, 23, 42)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(10)
    doc.text('EVIDÊNCIAS E REGISTROS CONSOLIDADOS', margin, y)
    y += 5

    const headers = options.tableHeaders.map(h => repairTextEncoding(h))
    const colWidth = contentWidth / headers.length
    const rowHeight = 6

    // Header da tabela
    doc.setFillColor(30, 41, 59)
    doc.rect(margin, y, contentWidth, rowHeight, 'F')
    doc.setTextColor(255, 255, 255)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(7.5)

    headers.forEach((header, idx) => {
      doc.text(header, margin + idx * colWidth + 2, y + 4.2)
    })
    y += rowHeight

    // Linhas da tabela (Max 25 no PDF para não estourar página)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(7)
    
    const rowsToRender = options.tableRows.slice(0, 28)
    rowsToRender.forEach((row, rowIdx) => {
      if (y > 275) {
        doc.addPage()
        y = 20
      }

      if (rowIdx % 2 === 1) {
        doc.setFillColor(248, 250, 252)
        doc.rect(margin, y, contentWidth, rowHeight, 'F')
      }

      doc.setTextColor(51, 65, 85)
      row.forEach((cell, colIdx) => {
        const valStr = repairTextEncoding(String(cell ?? ''))
        doc.text(valStr.substring(0, 35), margin + colIdx * colWidth + 2, y + 4.2)
      })

      y += rowHeight
    })

    if (options.tableRows.length > 28) {
      doc.setTextColor(148, 163, 184)
      doc.setFont('helvetica', 'italic')
      doc.setFontSize(7)
      doc.text(`* Exibindo as primeiras 28 de ${options.tableRows.length} linhas. A exportação completa está disponível em Excel.`, margin, y + 4)
    }
  }

  // ── Rodapé de Governança ──
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(6.5)
  doc.setTextColor(148, 163, 184)
  doc.text('LuminaAI v2.0 • Sistema de Inteligência Analítica e Decisão Corporativa • Casa do Campo', margin, 290)

  const fileName = (options.fileName || 'relatorio-executivo-luminaai').replace(/\.[^/.]+$/, '') + '.pdf'
  doc.save(fileName)
}

/**
 * Gera e baixa uma planilha do Excel (.xlsx) formatada com colunas ajustadas e tipos numéricos.
 */
export function exportDataToExcel(options: ExportReportOptions) {
  const wb = XLSX.utils.book_new()

  const data: Array<Array<string | number>> = []

  // Título e Metadados
  data.push(['LUMINA AI - RELATÓRIO ANALÍTICO'])
  if (options.title) data.push([repairTextEncoding(options.title)])
  if (options.queryText) data.push([`Consulta: ${repairTextEncoding(options.queryText)}`])
  data.push([`Gerado em: ${new Date().toLocaleString('pt-BR')}`])
  data.push([]) // Linha em branco

  // KPIs
  if (options.kpis && options.kpis.length > 0) {
    data.push(['INDICADORES PRINCIPAIS (KPIS)'])
    options.kpis.forEach(k => {
      data.push([repairTextEncoding(k.titulo), repairTextEncoding(k.valor), k.comparacao ? repairTextEncoding(k.comparacao) : ''])
    })
    data.push([]) // Linha em branco
  }

  // Tabela Principal
  if (options.tableHeaders && options.tableRows) {
    data.push(options.tableHeaders.map(h => repairTextEncoding(h)))
    options.tableRows.forEach(row => {
      data.push(row.map(cell => (typeof cell === 'string' ? repairTextEncoding(cell) : cell)))
    })
  }

  const ws = XLSX.utils.aoa_to_sheet(data)

  // Ajusta larguras de colunas automaticamente
  const maxColLength: number[] = []
  data.forEach(row => {
    row.forEach((cell, colIdx) => {
      const len = String(cell ?? '').length
      maxColLength[colIdx] = Math.max(maxColLength[colIdx] || 10, Math.min(len + 2, 50))
    })
  })
  ws['!cols'] = maxColLength.map(w => ({ wch: w }))

  XLSX.utils.book_append_sheet(wb, ws, 'Relatório LuminaAI')

  const fileName = (options.fileName || 'relatorio-luminaai').replace(/\.[^/.]+$/, '') + '.xlsx'
  XLSX.writeFile(wb, fileName)
}
