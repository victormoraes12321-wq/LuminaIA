/**
 * LuminaAI — Client-Side Export Utilities (v4.5)
 * Allows CSV, Excel (styled XML/TSV), and print-styled exports directly in browser.
 */

interface Column {
  key: string
  label: string
  type: string
}

type ExportRow = Record<string, unknown>

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function sanitizePrintableHtml(element: HTMLElement) {
  const clone = element.cloneNode(true) as HTMLElement
  clone.querySelectorAll('script, iframe, object, embed, style').forEach(node => node.remove())
  clone.querySelectorAll<HTMLElement>('*').forEach(node => {
    for (const attr of Array.from(node.attributes)) {
      const name = attr.name.toLowerCase()
      const value = attr.value.trim().toLowerCase()
      if (name.startsWith('on') || value.startsWith('javascript:')) {
        node.removeAttribute(attr.name)
      }
    }
  })
  return clone.innerHTML
}

export function exportToCSV(filename: string, columns: Column[], rows: ExportRow[]) {
  if (!rows || rows.length === 0) return
  
  const headers = columns.map(c => `"${c.label.replace(/"/g, '""')}"`).join(',')
  const csvRows = rows.map(row => 
    columns.map(col => {
      const val = row[col.key]
      const formatted = val === null || val === undefined ? '' : String(val)
      return `"${formatted.replace(/"/g, '""')}"`
    }).join(',')
  )

  const csvContent = '\uFEFF' + [headers, ...csvRows].join('\n') // UTF-8 BOM
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', `${filename}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export function exportToExcel(filename: string, columns: Column[], rows: ExportRow[]) {
  if (!rows || rows.length === 0) return

  // Format as clean HTML spreadsheet that Excel opens natively with proper styling
  const tableHeaders = columns.map(c => `<th style="background-color: #4F46E5; color: #FFFFFF; font-weight: bold; border: 1px solid #D1D5DB; padding: 8px;">${escapeHtml(c.label)}</th>`).join('')
  const tableRows = rows.map(row => 
    `<tr>${columns.map(col => {
      const val = row[col.key]
      const formatted = val === null || val === undefined ? '' : String(val)
      const isNumber = col.type === 'number' || col.type === 'currency'
      const align = isNumber ? 'right' : 'left'
      return `<td style="border: 1px solid #D1D5DB; padding: 6px; text-align: ${align};">${escapeHtml(formatted)}</td>`
    }).join('')}</tr>`
  ).join('')

  const htmlContent = `
    <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
    <head>
      <meta charset="utf-8" />
      <!--[if gte mso 9]>
      <xml>
        <x:ExcelWorkbook>
          <x:ExcelWorksheets>
            <x:ExcelWorksheet>
              <x:Name>LuminaAI Data</x:Name>
              <x:WorksheetOptions>
                <x:DisplayGridlines/>
              </x:WorksheetOptions>
            </x:ExcelWorksheet>
          </x:ExcelWorksheets>
        </x:ExcelWorkbook>
      </xml>
      <![endif]-->
    </head>
    <body style="font-family: sans-serif;">
      <h2 style="color: #4F46E5;">Relatório de Dados Executivos — LuminaAI</h2>
      <table style="border-collapse: collapse; border: 1px solid #D1D5DB;">
        <thead>
          <tr>${tableHeaders}</tr>
        </thead>
        <tbody>
          ${tableRows}
        </tbody>
      </table>
    </body>
    </html>
  `

  const blob = new Blob([htmlContent], { type: 'application/vnd.ms-excel;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', `${filename}.xls`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export function exportToPDF(elementId: string, title: string) {
  const element = document.getElementById(elementId)
  if (!element) return

  // Create a printable window with C-level styles replicating the query card exactly
  const printWindow = window.open('', '_blank', 'width=1000,height=800')
  if (!printWindow) return

  const cleanHTML = sanitizePrintableHtml(element)
  const safeTitle = escapeHtml(title)

  printWindow.document.write(`
    <html>
      <head>
        <title>${safeTitle} - LuminaAI</title>
        <meta charset="utf-8" />
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
          @media print {
            body { background: white; color: black; }
            .no-print { display: none; }
          }
          body { font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; padding: 40px; }
        </style>
      </head>
      <body class="bg-slate-50 text-slate-900">
        <div class="max-w-4xl mx-auto space-y-6">
          <div class="flex items-center justify-between border-b pb-4">
            <div>
              <h1 class="text-2xl font-bold text-indigo-600">LuminaAI</h1>
              <p class="text-sm text-slate-500">Business Intelligence Conversacional Corporativo</p>
            </div>
            <button onclick="window.print();" class="no-print bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-2 rounded-xl shadow-md transition-all text-sm">
              Imprimir Relatório (PDF)
            </button>
          </div>
          <div class="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-8">
            ${cleanHTML}
          </div>
        </div>
        <script>
          // Automatically hide print buttons or expand modal elements in print layout
          document.querySelectorAll('.no-print').forEach(e => e.style.display = 'none');
        </script>
      </body>
    </html>
  `)
  printWindow.document.close()
}
