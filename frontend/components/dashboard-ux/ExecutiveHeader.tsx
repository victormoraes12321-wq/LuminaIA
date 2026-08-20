'use client'

import { useState, useRef } from 'react'
import {
  Calendar,
  Building2,
  RefreshCw,
  MessageSquareText,
  SlidersHorizontal,
  ChevronDown,
  Check,
  Search,
  Sparkles,
  CalendarRange,
  Zap,
  Radio,
  ShieldCheck,
} from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { PortalOverlay } from '@/components/ui/PortalOverlay'

interface ExecutiveHeaderProps {
  startDate: string
  endDate: string
  periodPreset: string
  minAvailableDate?: string
  maxAvailableDate?: string
  selectedFilial: string | null
  availableBranches: string[]
  freshness: string
  sideChatOpen: boolean
  loading: boolean
  onSelectDateRange: (start: string, end: string, presetLabel: string) => void
  onSelectFilial: (filial: string | null) => void
  onToggleSideChat: () => void
  onRefresh: () => void
}

export function ExecutiveHeader({
  startDate,
  endDate,
  periodPreset,
  minAvailableDate = '2024-08-19',
  maxAvailableDate = '2026-08-18',
  selectedFilial,
  availableBranches = ['1', '2', '3', '4', '5'],
  freshness,
  sideChatOpen,
  loading,
  onSelectDateRange,
  onSelectFilial,
  onToggleSideChat,
  onRefresh,
}: ExecutiveHeaderProps) {
  const [datePopoverOpen, setDatePopoverOpen] = useState(false)
  const [branchPopoverOpen, setBranchPopoverOpen] = useState(false)
  const [branchSearch, setBranchSearch] = useState('')
  const [customStart, setCustomStart] = useState(startDate)
  const [customEnd, setCustomEnd] = useState(endDate)

  const dateRef = useRef<HTMLButtonElement>(null)
  const branchRef = useRef<HTMLButtonElement>(null)

  // Dynamic YTD end date: MIN(maxAvailableDate / freshness, '2026-12-31')
  const ytdEndDate = maxAvailableDate ? (maxAvailableDate < '2026-12-31' ? maxAvailableDate : '2026-12-31') : '2026-08-18'

  const DATE_PRESETS = [
    { label: 'Ano 2026 (YTD)', start: '2026-01-01', end: ytdEndDate },
    { label: 'Todo o Período Histórico', start: minAvailableDate, end: maxAvailableDate },
    { label: 'Últimos 30 Dias', start: '2026-07-19', end: '2026-08-18' },
    { label: 'Últimos 7 Dias', start: '2026-08-11', end: '2026-08-18' },
    { label: 'Fevereiro / 2026', start: '2026-02-01', end: '2026-02-28' },
    { label: 'Janeiro / 2026', start: '2026-01-01', end: '2026-01-31' },
    { label: 'Ano 2025 Completo', start: '2025-01-01', end: '2025-12-31' },
  ]

  const handleApplyCustomDate = (e: React.FormEvent) => {
    e.preventDefault()
    if (customStart && customEnd) {
      onSelectDateRange(customStart, customEnd, `De ${customStart} até ${customEnd}`)
      setDatePopoverOpen(false)
    }
  }

  const filteredBranches = availableBranches.filter(b =>
    `Filial ${b}`.toLowerCase().includes(branchSearch.toLowerCase()) || b.includes(branchSearch)
  )

  return (
    <header
      data-testid="executive-dashboard-header"
      className="sticky top-0 z-30 flex flex-col gap-3 pb-3 pt-2 border-b border-[rgb(var(--border)/0.6)] bg-[rgb(var(--bg-surface)/0.92)] backdrop-blur-2xl px-2 transition-all duration-200"
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Cockpit Brand & Status Indicator */}
        <div className="flex items-center gap-3.5">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 via-blue-500/10 to-indigo-500/20 border border-cyan-500/30 text-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.25)]">
            <Zap className="w-5 h-5 animate-pulse text-cyan-400" />
            <span className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
          </div>

          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-[rgb(var(--text-primary))] flex items-center gap-2">
                <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-300 bg-clip-text text-transparent">
                  LuminaAI
                </span>
                <span className="text-xs font-medium px-2 py-0.5 rounded-md bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                  Visão Executiva
                </span>
              </h1>
              <span
                title="Fonte analítica sincronizada • 100% de reconciliação real"
                className="hidden sm:inline-flex items-center gap-1 text-[11px] font-medium px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Dados Verificados
              </span>
            </div>
            <p className="text-xs text-[rgb(var(--text-muted))] flex items-center gap-2 mt-0.5">
              <span className="text-[rgb(var(--text-secondary))] font-semibold">Casa do Campo</span>
              <span>•</span>
              <span className="text-emerald-400/90 flex items-center gap-1">
                <Radio className="w-2.5 h-2.5 animate-pulse text-emerald-400" />
                Sincronizado: {freshness || '18/08/2026'}
              </span>
            </p>
          </div>
        </div>

        {/* Right: Command Controls with Portal Overlays */}
        <div className="flex items-center flex-wrap gap-2.5">
          {/* Date Range Popover Button */}
          <div>
            <button
              ref={dateRef}
              data-testid="date-range-popover-trigger"
              onClick={() => {
                setDatePopoverOpen(!datePopoverOpen)
                setBranchPopoverOpen(false)
              }}
              className={cn(
                'flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-xl border transition-all shadow-sm',
                datePopoverOpen
                  ? 'border-cyan-500/60 bg-cyan-500/10 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.25)] ring-1 ring-cyan-500/40'
                  : 'border-[rgb(var(--border)/0.8)] bg-[rgb(var(--bg-elevated))] hover:bg-[rgb(var(--bg-hover))] text-[rgb(var(--text-primary))]'
              )}
            >
              <Calendar className="w-3.5 h-3.5 text-cyan-400" />
              <span className="font-semibold">{periodPreset}</span>
              <ChevronDown className={cn('w-3.5 h-3.5 transition-transform duration-200 text-[rgb(var(--text-muted))]', datePopoverOpen && 'rotate-180 text-cyan-400')} />
            </button>

            {/* Global Portal Date Popover */}
            <PortalOverlay
              isOpen={datePopoverOpen}
              onClose={() => setDatePopoverOpen(false)}
              triggerRef={dateRef}
              placement="bottom-start"
              maxWidth={360}
            >
              <div
                data-testid="date-range-popover"
                className="w-80 sm:w-96 rounded-2xl border border-cyan-500/30 bg-zinc-950/95 dark:bg-zinc-950/98 backdrop-blur-2xl shadow-[0_20px_50px_rgba(0,0,0,0.8),0_0_25px_rgba(6,182,212,0.2)] p-4 text-[rgb(var(--text-primary))] ring-1 ring-white/10"
              >
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/10">
                  <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                    <CalendarRange className="w-4 h-4" />
                    Selecione o Período
                  </span>
                  <span className="text-[10px] font-mono text-zinc-400">
                    Max: {maxAvailableDate}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-1.5 mb-3">
                  {DATE_PRESETS.map((preset) => {
                    const active = periodPreset === preset.label
                    return (
                      <button
                        key={preset.label}
                        data-testid={`date-preset-${preset.label.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
                        onClick={() => {
                          onSelectDateRange(preset.start, preset.end, preset.label)
                          setDatePopoverOpen(false)
                        }}
                        className={cn(
                          'flex items-center justify-between px-2.5 py-1.5 text-xs rounded-lg transition-all text-left font-medium',
                          active
                            ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/50 text-cyan-300 font-semibold shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                            : 'hover:bg-white/5 border border-transparent text-zinc-300 hover:text-white'
                        )}
                      >
                        <span className="truncate">{preset.label}</span>
                        {active && <Check className="w-3.5 h-3.5 text-cyan-400 shrink-0" />}
                      </button>
                    )
                  })}
                </div>

                <form onSubmit={handleApplyCustomDate} className="pt-3 border-t border-white/10 flex flex-col gap-2.5">
                  <span className="text-[11px] font-semibold text-zinc-400">Intervalo Personalizado:</span>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] font-mono text-zinc-500 block mb-1">De:</label>
                      <input
                        type="date"
                        data-testid="custom-date-start"
                        value={customStart}
                        min={minAvailableDate}
                        max={maxAvailableDate}
                        onChange={(e) => setCustomStart(e.target.value)}
                        className="w-full text-xs px-2 py-1.5 rounded-lg bg-zinc-900 border border-white/10 text-white focus:outline-none focus:border-cyan-500/60"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-mono text-zinc-500 block mb-1">Até:</label>
                      <input
                        type="date"
                        data-testid="custom-date-end"
                        value={customEnd}
                        min={minAvailableDate}
                        max={maxAvailableDate}
                        onChange={(e) => setCustomEnd(e.target.value)}
                        className="w-full text-xs px-2 py-1.5 rounded-lg bg-zinc-900 border border-white/10 text-white focus:outline-none focus:border-cyan-500/60"
                      />
                    </div>
                  </div>
                  <div className="flex items-center justify-end gap-2 mt-1">
                    <button
                      type="button"
                      onClick={() => setDatePopoverOpen(false)}
                      className="px-3 py-1.5 text-xs text-zinc-400 hover:text-white rounded-lg transition-colors"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      data-testid="apply-custom-date-btn"
                      className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black shadow-[0_0_15px_rgba(6,182,212,0.4)] transition-all"
                    >
                      Aplicar
                    </button>
                  </div>
                </form>
              </div>
            </PortalOverlay>
          </div>

          {/* Branch Filter Popover Button */}
          <div>
            <button
              ref={branchRef}
              data-testid="branch-filter-trigger"
              onClick={() => {
                setBranchPopoverOpen(!branchPopoverOpen)
                setDatePopoverOpen(false)
              }}
              className={cn(
                'flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-xl border transition-all shadow-sm',
                selectedFilial
                  ? 'border-indigo-500/60 bg-indigo-500/10 text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.25)] ring-1 ring-indigo-500/40'
                  : 'border-[rgb(var(--border)/0.8)] bg-[rgb(var(--bg-elevated))] hover:bg-[rgb(var(--bg-hover))] text-[rgb(var(--text-primary))]'
              )}
            >
              <Building2 className="w-3.5 h-3.5 text-indigo-400" />
              <span className="font-semibold">
                {selectedFilial ? `Filial ${selectedFilial}` : 'Todas as Filiais'}
              </span>
              <ChevronDown className={cn('w-3.5 h-3.5 transition-transform duration-200 text-[rgb(var(--text-muted))]', branchPopoverOpen && 'rotate-180 text-indigo-400')} />
            </button>

            {/* Global Portal Branch Popover */}
            <PortalOverlay
              isOpen={branchPopoverOpen}
              onClose={() => setBranchPopoverOpen(false)}
              triggerRef={branchRef}
              placement="bottom-start"
              maxWidth={300}
            >
              <div
                data-testid="branch-filter-popover"
                className="w-64 rounded-2xl border border-indigo-500/30 bg-zinc-950/95 dark:bg-zinc-950/98 backdrop-blur-2xl shadow-[0_20px_50px_rgba(0,0,0,0.8),0_0_25px_rgba(99,102,241,0.2)] p-3 text-[rgb(var(--text-primary))] ring-1 ring-white/10"
              >
                <div className="relative mb-2">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-zinc-400" />
                  <input
                    type="text"
                    placeholder="Buscar filial..."
                    value={branchSearch}
                    onChange={(e) => setBranchSearch(e.target.value)}
                    className="w-full text-xs pl-8 pr-2.5 py-1.5 rounded-lg bg-zinc-900 border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500/60"
                  />
                </div>

                <div className="flex flex-col gap-1 max-h-52 overflow-y-auto pr-1">
                  <button
                    data-testid="branch-option-all"
                    onClick={() => {
                      onSelectFilial(null)
                      setBranchPopoverOpen(false)
                    }}
                    className={cn(
                      'flex items-center justify-between px-2.5 py-1.5 text-xs rounded-lg transition-all text-left font-medium',
                      selectedFilial === null
                        ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/50 text-indigo-300 font-semibold shadow-[0_0_10px_rgba(99,102,241,0.2)]'
                        : 'hover:bg-white/5 border border-transparent text-zinc-300 hover:text-white'
                    )}
                  >
                    <span>Todas as Filiais</span>
                    {selectedFilial === null && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                  </button>

                  {filteredBranches.map((filial) => {
                    const active = selectedFilial === filial
                    return (
                      <button
                        key={filial}
                        data-testid={`branch-option-${filial}`}
                        onClick={() => {
                          onSelectFilial(filial)
                          setBranchPopoverOpen(false)
                        }}
                        className={cn(
                          'flex items-center justify-between px-2.5 py-1.5 text-xs rounded-lg transition-all text-left font-medium',
                          active
                            ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/50 text-indigo-300 font-semibold shadow-[0_0_10px_rgba(99,102,241,0.2)]'
                            : 'hover:bg-white/5 border border-transparent text-zinc-300 hover:text-white'
                        )}
                      >
                        <span>Filial {filial}</span>
                        {active && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                      </button>
                    )
                  })}
                </div>
              </div>
            </PortalOverlay>
          </div>

          {/* Refresh Action */}
          <button
            data-testid="dashboard-refresh-btn"
            onClick={onRefresh}
            title="Atualizar Dados"
            disabled={loading}
            className="flex items-center justify-center w-9 h-9 rounded-xl border border-[rgb(var(--border)/0.8)] bg-[rgb(var(--bg-elevated))] hover:bg-[rgb(var(--bg-hover))] text-[rgb(var(--text-primary))] transition-all active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={cn('w-4 h-4 text-cyan-400', loading && 'animate-spin')} />
          </button>

          {/* AI Analytical Copilot Drawer Toggle */}
          <button
            data-testid="toggle-side-chat"
            onClick={onToggleSideChat}
            className={cn(
              'flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl border transition-all shadow-md active:scale-95',
              sideChatOpen
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-black border-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.4)]'
                : 'bg-gradient-to-r from-cyan-500/15 via-blue-500/10 to-indigo-500/15 text-cyan-300 border-cyan-500/40 hover:bg-cyan-500/20 hover:border-cyan-400'
            )}
          >
            <Sparkles className={cn('w-4 h-4', sideChatOpen ? 'text-black animate-spin' : 'text-cyan-400')} />
            <span>IA Analítica</span>
            <span className={cn(
              'px-1.5 py-0.2 rounded-full text-[10px] font-mono',
              sideChatOpen ? 'bg-black/20 text-black font-bold' : 'bg-cyan-500/20 text-cyan-300'
            )}>
              Copilot
            </span>
          </button>
        </div>
      </div>
    </header>
  )
}
