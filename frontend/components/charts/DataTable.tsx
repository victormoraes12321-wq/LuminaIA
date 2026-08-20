'use client'

import { useState, useMemo } from 'react'
import { Search, ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react'
import { formatCurrency, formatDate, cn } from '@/lib/utils'
import { repairTextEncoding } from '@/lib/textEncoding'
import { StatusBadge } from '@/components/ui/Badge'
import type { ChartDataTable, TableColumn } from '@/types/lumina'

// ── Cell Renderer ──────────────────────────────────────────────

function CellValue({
  col,
  value,
  row,
  isTopLeader,
}: {
  col: TableColumn
  value: unknown
  row: Record<string, unknown>
  isTopLeader?: boolean
}) {
  if (value === null || value === undefined) {
    return <span style={{ color: 'rgb(var(--text-muted))' }}>—</span>
  }

  const colKeyLower = col.key.toLowerCase()

  // ── Smart Visual Alert Badges ──
  if ((colKeyLower.includes('estoque') || colKeyLower === 'qtde' || colKeyLower === 'saldo') && typeof value === 'number') {
    if (value <= 0) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[11px] font-bold">
          🔴 Crítico ({value.toLocaleString('pt-BR')})
        </span>
      )
    }
    if (value <= 10) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[11px] font-bold">
          🟡 Reposição ({value.toLocaleString('pt-BR')})
        </span>
      )
    }
  }

  if ((colKeyLower.includes('margem') || colKeyLower.includes('markup')) && typeof value === 'number') {
    if (value < 15) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[11px] font-bold">
          ⚠️ {value.toFixed(1)}% (Baixa)
        </span>
      )
    }
  }

  switch (col.type) {
    case 'currency':
      return (
        <span className="font-mono text-xs font-semibold text-emerald-400">
          {typeof value === 'number' ? formatCurrency(value) : repairTextEncoding(String(value))}
        </span>
      )

    case 'badge':
      return <StatusBadge status={repairTextEncoding(String(value))} />

    case 'date':
      return (
        <span className="font-mono text-xs" style={{ color: 'rgb(var(--text-secondary))' }}>
          {formatDate(String(value))}
        </span>
      )

    case 'boolean':
      if (value === null || value === undefined) return <span>—</span>
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1 text-xs font-medium',
            value ? 'text-emerald-400' : 'text-red-400',
          )}
        >
          {value ? '✓ Sim' : '✗ Não'}
        </span>
      )

    case 'number':
      return (
        <span className="font-mono text-xs font-semibold" style={{ color: 'rgb(var(--text-primary))' }}>
          {typeof value === 'number' ? value.toLocaleString('pt-BR') : repairTextEncoding(String(value))}
        </span>
      )

    default:
      return (
        <div className="flex items-center gap-1.5">
          {isTopLeader && (
            <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[9px] font-black uppercase">
              Líder
            </span>
          )}
          <span className="text-xs font-medium text-zinc-200">
            {repairTextEncoding(String(value))}
          </span>
        </div>
      )
  }
}

// ── DataTable Component ─────────────────────────────────────────

const PAGE_SIZE = 10

interface DataTableProps {
  data?: ChartDataTable | null
  onRowClick?: (row: Record<string, unknown>) => void
}

export function DataTable({ data, onRowClick }: DataTableProps) {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const rows = useMemo(() => (Array.isArray(data?.rows) ? data.rows : []), [data])
  const columns = useMemo(() => (Array.isArray(data?.columns) ? data.columns : []), [data])
  const totalRows = typeof data?.total_rows === 'number' ? data.total_rows : rows.length
  const hasValidData = Boolean(data && Array.isArray(rows) && Array.isArray(columns))

  // ── Filter ────────────────────────────────────────────────
  const filtered = useMemo(() => {
    if (!query.trim()) return rows
    const q = query.toLowerCase()
    return rows.filter((row) =>
      Object.values(row).some(
        (v) => v !== null && v !== undefined && String(v).toLowerCase().includes(q)
      )
    )
  }, [rows, query])

  // ── Sort ──────────────────────────────────────────────────
  const sorted = useMemo(() => {
    if (!sortKey) return filtered
    return [...filtered].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (av === null || av === undefined) return 1
      if (bv === null || bv === undefined) return -1
      const cmp = String(av).localeCompare(String(bv), 'pt-BR', { numeric: true })
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortKey, sortDir])

  // ── Paginate ──────────────────────────────────────────────
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE))
  const safePage = Math.min(page, totalPages)
  const pageRows = sorted.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
    setPage(1)
  }

  const handleSearch = (v: string) => {
    setQuery(v)
    setPage(1)
  }

  if (!hasValidData) {
    return (
      <div className="flex items-center justify-center h-full text-xs" style={{ color: 'rgb(var(--text-muted))' }}>
        Nenhum dado disponível
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Search + stats */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        {/* Search */}
        <div className="relative">
          <Search
            size={13}
            className="absolute left-3 top-1/2 -translate-y-1/2"
            style={{ color: 'rgb(var(--text-muted))' }}
          />
          <input
            type="text"
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Buscar na tabela..."
            className="lumina-input text-xs pl-8 pr-3 py-2 w-52"
          />
        </div>

        {/* Stats and Drill-down tooltip */}
        <div className="flex items-center gap-2">
          {onRowClick && (
            <span className="text-[10px] text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded-full font-medium">
              💡 Dica: Clique na linha para detalhar
            </span>
          )}
          <p className="text-xs" style={{ color: 'rgb(var(--text-muted))' }}>
            <span className="font-semibold" style={{ color: 'rgb(var(--text-secondary))' }}>
              {sorted.length}
            </span>{' '}
            de {totalRows} registros
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto thin-scroll rounded-xl" style={{ border: '1px solid rgb(var(--border) / 0.5)' }}>
        <table className="w-full min-w-max border-collapse text-xs">
          {/* Header */}
          <thead>
            <tr style={{ background: 'rgb(var(--bg-elevated))' }}>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-4 py-3 text-left font-semibold whitespace-nowrap',
                    col.sortable && 'cursor-pointer select-none group'
                  )}
                  style={{
                    color: 'rgb(var(--text-muted))',
                    borderBottom: '1px solid rgb(var(--border) / 0.5)',
                    width: col.width ?? undefined,
                  }}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  <div className="flex items-center gap-1.5">
                    {repairTextEncoding(col.label)}
                    {col.sortable && (
                      <ArrowUpDown
                        size={11}
                        className={cn(
                          'opacity-0 group-hover:opacity-60 transition-opacity',
                          sortKey === col.key && 'opacity-100 text-lumina-400'
                        )}
                      />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          {/* Body */}
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-10 text-center"
                  style={{ color: 'rgb(var(--text-muted))' }}
                >
                  Nenhum resultado encontrado para &quot;{query}&quot;
                </td>
              </tr>
            ) : (
              pageRows.map((row, rowIdx) => {
                const isGlobalLeader = page === 1 && rowIdx === 0 && !query.trim()
                return (
                  <tr
                    key={rowIdx}
                    onClick={() => onRowClick?.(row)}
                    className={cn(
                      'transition-colors',
                      onRowClick && 'cursor-pointer hover:bg-cyan-500/10 active:bg-cyan-500/20'
                    )}
                    style={{
                      background:
                        rowIdx % 2 === 0
                          ? 'transparent'
                          : 'rgb(var(--bg-elevated) / 0.4)',
                    }}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className="px-4 py-2.5 whitespace-nowrap"
                        style={{ borderBottom: '1px solid rgb(var(--border) / 0.25)' }}
                      >
                        <CellValue
                          col={col}
                          value={row[col.key]}
                          row={row}
                          isTopLeader={isGlobalLeader && col === columns[0]}
                        />
                      </td>
                    ))}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs" style={{ color: 'rgb(var(--text-muted))' }}>
            Página {safePage} de {totalPages}
          </p>

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={safePage === 1}
              className={cn(
                'w-7 h-7 rounded-lg flex items-center justify-center transition-colors',
                'hover:bg-[rgb(var(--bg-elevated))] disabled:opacity-30 disabled:cursor-not-allowed'
              )}
              style={{ color: 'rgb(var(--text-secondary))' }}
            >
              <ChevronLeft size={14} />
            </button>

            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const pageNum = Math.max(1, Math.min(totalPages - 4, safePage - 2)) + i
              return (
                <button
                  type="button"
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={cn(
                    'w-7 h-7 rounded-lg text-xs font-medium transition-colors',
                    pageNum === safePage
                      ? 'bg-lumina-500 text-white font-semibold'
                      : 'hover:bg-[rgb(var(--bg-elevated))] text-[rgb(var(--text-secondary))]'
                  )}
                >
                  {pageNum}
                </button>
              )
            })}

            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage === totalPages}
              className={cn(
                'w-7 h-7 rounded-lg flex items-center justify-center transition-colors',
                'hover:bg-[rgb(var(--bg-elevated))] disabled:opacity-30 disabled:cursor-not-allowed'
              )}
              style={{ color: 'rgb(var(--text-secondary))' }}
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
