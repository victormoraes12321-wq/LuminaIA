'use client'

import { useState, useMemo } from 'react'
import { Search, ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react'
import { formatCurrency, formatDate, cn } from '@/lib/utils'
import { StatusBadge } from '@/components/ui/Badge'
import type { ChartDataTable, TableColumn } from '@/types/lumina'

// ── Cell Renderer ──────────────────────────────────────────────

function CellValue({ col, value }: { col: TableColumn; value: unknown }) {
  if (value === null || value === undefined) {
    return <span style={{ color: 'rgb(var(--text-muted))' }}>—</span>
  }

  switch (col.type) {
    case 'currency':
      return (
        <span className="font-mono text-xs font-semibold" style={{ color: 'rgb(var(--text-primary))' }}>
          {typeof value === 'number' ? formatCurrency(value) : String(value)}
        </span>
      )

    case 'badge':
      return <StatusBadge status={String(value)} />

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
        <span className="font-mono text-xs" style={{ color: 'rgb(var(--text-primary))' }}>
          {typeof value === 'number' ? value.toLocaleString('pt-BR') : String(value)}
        </span>
      )

    default:
      return (
        <span className="text-xs" style={{ color: 'rgb(var(--text-secondary))' }}>
          {String(value)}
        </span>
      )
  }
}

// ── DataTable ─────────────────────────────────────────────────

const PAGE_SIZE = 10

interface DataTableProps {
  data?: ChartDataTable | null
}

export function DataTable({ data }: DataTableProps) {
  const [query, setQuery]           = useState('')
  const [page, setPage]             = useState(1)
  const [sortKey, setSortKey]       = useState<string | null>(null)
  const [sortDir, setSortDir]       = useState<'asc' | 'desc'>('asc')
  const rows                         = useMemo(() => (Array.isArray(data?.rows) ? data.rows : []), [data])
  const columns                      = useMemo(() => (Array.isArray(data?.columns) ? data.columns : []), [data])
  const totalRows                    = typeof data?.total_rows === 'number' ? data.total_rows : rows.length
  const hasValidData                 = Boolean(data && Array.isArray(rows) && Array.isArray(columns))

  // ── Filter ────────────────────────────────────────────────

  const filtered = useMemo(() => {
    if (!query.trim()) return rows
    const q = query.toLowerCase()
    return rows.filter(row =>
      Object.values(row).some(v =>
        v !== null && v !== undefined && String(v).toLowerCase().includes(q),
      ),
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
  const safePage   = Math.min(page, totalPages)
  const pageRows   = sorted.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
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
        Nenhum dado disponivel
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
            onChange={e => handleSearch(e.target.value)}
            placeholder="Buscar na tabela..."
            className="lumina-input text-xs pl-8 pr-3 py-2 w-52"
          />
        </div>

        {/* Stats */}
        <p className="text-xs" style={{ color: 'rgb(var(--text-muted))' }}>
          <span className="font-semibold" style={{ color: 'rgb(var(--text-secondary))' }}>
            {sorted.length}
          </span>{' '}
          de {totalRows} registros
        </p>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto thin-scroll rounded-xl" style={{ border: '1px solid rgb(var(--border) / 0.5)' }}>
        <table className="w-full min-w-max border-collapse text-xs">
          {/* Header */}
          <thead>
            <tr style={{ background: 'rgb(var(--bg-elevated))' }}>
              {columns.map(col => (
                <th
                  key={col.key}
                  className={cn(
                    'px-4 py-3 text-left font-semibold whitespace-nowrap',
                    col.sortable && 'cursor-pointer select-none group',
                  )}
                  style={{
                    color: 'rgb(var(--text-muted))',
                    borderBottom: '1px solid rgb(var(--border) / 0.5)',
                    width: col.width ?? undefined,
                  }}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  <div className="flex items-center gap-1.5">
                    {col.label}
                    {col.sortable && (
                      <ArrowUpDown
                        size={11}
                        className={cn(
                          'opacity-0 group-hover:opacity-60 transition-opacity',
                          sortKey === col.key && 'opacity-100 text-lumina-400',
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
              pageRows.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className="transition-colors"
                  style={{
                    background:
                      rowIdx % 2 === 0
                        ? 'transparent'
                        : 'rgb(var(--bg-elevated) / 0.4)',
                  }}
                  onMouseEnter={e => {
                    ;(e.currentTarget as HTMLTableRowElement).style.background =
                      'rgb(var(--accent) / 0.05)'
                  }}
                  onMouseLeave={e => {
                    ;(e.currentTarget as HTMLTableRowElement).style.background =
                      rowIdx % 2 === 0
                        ? 'transparent'
                        : 'rgb(var(--bg-elevated) / 0.4)'
                  }}
                >
                  {columns.map(col => (
                    <td
                      key={col.key}
                      className="px-4 py-2.5 whitespace-nowrap"
                      style={{ borderBottom: '1px solid rgb(var(--border) / 0.25)' }}
                    >
                      <CellValue col={col} value={row[col.key]} />
                    </td>
                  ))}
                </tr>
              ))
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
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={safePage === 1}
              className={cn(
                'w-7 h-7 rounded-lg flex items-center justify-center transition-colors',
                'hover:bg-[rgb(var(--bg-elevated))] disabled:opacity-30 disabled:cursor-not-allowed',
              )}
              style={{ color: 'rgb(var(--text-secondary))' }}
            >
              <ChevronLeft size={14} />
            </button>

            {/* Page numbers */}
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const pageNum = Math.max(
                1,
                Math.min(totalPages - 4, safePage - 2),
              ) + i
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={cn(
                    'w-7 h-7 rounded-lg text-xs font-medium transition-colors',
                    pageNum === safePage
                      ? 'bg-lumina-500 text-white'
                      : 'hover:bg-[rgb(var(--bg-elevated))]',
                  )}
                  style={{
                    color: pageNum === safePage ? undefined : 'rgb(var(--text-secondary))',
                  }}
                >
                  {pageNum}
                </button>
              )
            })}

            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={safePage === totalPages}
              className={cn(
                'w-7 h-7 rounded-lg flex items-center justify-center transition-colors',
                'hover:bg-[rgb(var(--bg-elevated))] disabled:opacity-30 disabled:cursor-not-allowed',
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
