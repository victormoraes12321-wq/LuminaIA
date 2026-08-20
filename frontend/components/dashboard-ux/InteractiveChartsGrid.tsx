'use client'

import { useState } from 'react'
import {
  TrendingUp,
  Building2,
  Package,
  Users,
  UserCheck,
  Maximize2,
  Table as TableIcon,
  BarChart2,
  Sparkles,
  ChevronRight,
  ArrowUpRight,
  ShieldCheck,
  Flame,
  Award,
  Zap,
} from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import type {
  EvolutionItem,
  BranchItem,
  TopProductItem,
  TopSellerItem,
  TopClientItem,
  AnalyticalContext,
  AnalyticalEntity,
  DashboardChatAction,
  FocusWidgetState,
  GovernedInsight,
} from './types'

interface InteractiveChartsGridProps {
  evolution: EvolutionItem[]
  branchPerformance: BranchItem[]
  topProducts: TopProductItem[]
  topSellers: TopSellerItem[]
  topClients: TopClientItem[]
  insights: GovernedInsight[]
  loading?: boolean
  selectedFilial: string | null
  selectedVendedor?: AnalyticalEntity | null
  selectedProduto?: AnalyticalEntity | null
  selectedCliente?: AnalyticalEntity | null
  viewModes: Record<string, 'chart' | 'table'>
  onToggleViewMode: (widgetId: string) => void
  onDrilldownBranch: (filial: string) => void
  onDrilldownSeller: (seller: TopSellerItem) => void
  onDrilldownProduct: (product: TopProductItem) => void
  onDrilldownClient: (client: TopClientItem) => void
  onSelectInsight: (insight: GovernedInsight) => void
  onOpenFocusMode?: (title: string, dimension: string, data: any) => void
}

export function InteractiveChartsGrid({
  evolution,
  branchPerformance,
  topProducts,
  topSellers,
  topClients,
  insights,
  loading = false,
  selectedFilial,
  selectedVendedor,
  selectedProduto,
  selectedCliente,
  viewModes,
  onToggleViewMode,
  onDrilldownBranch,
  onDrilldownSeller,
  onDrilldownProduct,
  onDrilldownClient,
  onSelectInsight,
  onOpenFocusMode,
}: InteractiveChartsGridProps) {
  const maxBranchVal = Math.max(...branchPerformance.map(b => b.value), 1)
  const maxEvoVal = Math.max(...evolution.map(e => e.value), 1)

  const getRankBadgeClass = (idx: number) => {
    if (idx === 0) return 'bg-amber-500/25 text-amber-300 border-amber-400/60 shadow-[0_0_12px_rgba(245,158,11,0.35)]'
    if (idx === 1) return 'bg-slate-400/25 text-slate-200 border-slate-300/50 shadow-[0_0_10px_rgba(203,213,225,0.25)]'
    if (idx === 2) return 'bg-orange-500/25 text-orange-300 border-orange-400/50 shadow-[0_0_10px_rgba(249,115,22,0.25)]'
    return 'bg-zinc-800/60 text-zinc-400 border-zinc-700/50'
  }

  return (
    <div className="space-y-4">
      {/* ── ROW 1: Business Momentum & Filiais Performance ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* 1.1 Temporal Evolution Chart (8 Cols) */}
        <section
          data-testid="widget-evolution"
          className="lg:col-span-8 relative flex flex-col justify-between p-5 rounded-2xl border border-amber-500/30 bg-zinc-950/80 dark:bg-zinc-950/90 backdrop-blur-xl shadow-[0_10px_35px_rgba(0,0,0,0.5)] transition-all"
        >
          {/* Ambient Top Glow Cap */}
          <div className="absolute top-0 left-8 right-8 h-[2px] bg-gradient-to-r from-transparent via-amber-400 to-transparent opacity-80" />

          <div className="flex items-center justify-between pb-3.5 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/40 shadow-[0_0_15px_rgba(245,158,11,0.25)]">
                <TrendingUp className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-xs font-bold uppercase tracking-wider text-[rgb(var(--text-primary))] flex items-center gap-2">
                  <span>Evolução do Faturamento</span>
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-amber-500/15 border border-amber-500/30 text-amber-300">
                    Mensal
                  </span>
                </h2>
                <p className="text-[11px] text-[rgb(var(--text-muted))]">
                  Receita líquida consolidada por mês no período
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                data-testid="toggle-view-evolution"
                onClick={() => onToggleViewMode('evolution')}
                title="Alternar entre Gráfico e Tabela"
                className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border border-white/10 bg-white/5 hover:bg-white/15 text-zinc-300 hover:text-white transition-all font-medium"
              >
                {viewModes.evolution === 'table' ? (
                  <>
                    <BarChart2 className="w-3.5 h-3.5 text-amber-400" />
                    <span className="hidden sm:inline">Gráfico</span>
                  </>
                ) : (
                  <>
                    <TableIcon className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="hidden sm:inline">Tabela</span>
                  </>
                )}
              </button>

              <button
                type="button"
                data-testid="focus-widget-evolution"
                onClick={() => onOpenFocusMode?.('Evolução do Faturamento', 'temporal', evolution)}
                title="Modo Foco Fullscreen"
                className="flex items-center justify-center w-7 h-7 rounded-lg border border-white/10 bg-white/5 hover:bg-white/15 text-zinc-400 hover:text-white transition-all hover:border-amber-500/40 hover:text-amber-400"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Chart / Table Body */}
          <div className="py-4 min-h-[260px] flex flex-col justify-center">
            {viewModes.evolution === 'table' ? (
              <div data-testid="table-view-evolution" className="overflow-x-auto max-h-64">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="sticky top-0 bg-zinc-900 border-b border-white/10 text-zinc-400">
                    <tr>
                      <th className="p-2">Data / Período</th>
                      <th className="p-2 text-right">Faturamento (R$)</th>
                      <th className="p-2 text-right">Volume (Un)</th>
                      <th className="p-2 text-right">Notas (NF-e)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-zinc-300">
                    {evolution.map((item, idx) => (
                      <tr key={idx} className="hover:bg-white/5 transition-colors">
                        <td className="p-2 font-medium text-white">{item.label || item.date}</td>
                        <td className="p-2 text-right text-amber-300 font-semibold">{item.formatted}</td>
                        <td className="p-2 text-right text-cyan-300">{item.formatted_volume || item.volume}</td>
                        <td className="p-2 text-right text-zinc-400">{item.invoices}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-end gap-1.5 sm:gap-2.5 h-44 pt-4 px-2">
                  {evolution.map((item, idx) => {
                    const heightPct = Math.max(8, Math.round((item.value / maxEvoVal) * 100))
                    return (
                      <div
                        key={idx}
                        className="group/bar relative flex-1 flex flex-col items-center justify-end h-full cursor-pointer"
                      >
                        {/* Hover Tooltip Card */}
                        <div className="absolute -top-12 z-20 hidden group-hover/bar:flex flex-col items-center pointer-events-none transition-all">
                          <div className="px-2.5 py-1.5 rounded-lg bg-zinc-950 border border-amber-500/50 shadow-[0_5px_20px_rgba(0,0,0,0.8)] text-[11px] font-mono whitespace-nowrap text-amber-300">
                            <span className="font-bold">{item.formatted}</span>
                            <span className="text-[10px] text-zinc-400 block">{item.label}</span>
                          </div>
                          <div className="w-2 h-2 rotate-45 bg-zinc-950 border-r border-b border-amber-500/50 -mt-1" />
                        </div>

                        {/* Bar Body with Gradient & Top Glow Cap */}
                        <div className="w-full relative flex flex-col justify-end items-center h-full">
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: `${heightPct}%` }}
                            transition={{ duration: 0.5, delay: idx * 0.02 }}
                            className="w-full rounded-t-lg bg-gradient-to-t from-amber-600/70 via-amber-400/90 to-amber-300 border-t border-amber-200 shadow-[0_0_15px_rgba(245,158,11,0.25)] group-hover/bar:brightness-125 transition-all"
                          />
                        </div>

                        {/* X-Axis Label */}
                        <span className="text-[10px] text-zinc-400 group-hover/bar:text-amber-300 mt-1.5 truncate max-w-full font-medium">
                          {item.label}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-white/5 flex items-center justify-between text-[11px] text-zinc-400">
            <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <Zap className="w-3.5 h-3.5" />
              <span>Valores consolidados por período</span>
            </span>
            <span className="text-zinc-500">Passe o cursor sobre as barras para detalhes</span>
          </div>
        </section>

        {/* 1.2 Filiais Performance Grid (4 Cols) */}
        <section
          data-testid="widget-branch-performance"
          className="lg:col-span-4 relative flex flex-col justify-between p-5 rounded-2xl border border-indigo-500/30 bg-zinc-950/80 dark:bg-zinc-950/90 backdrop-blur-xl shadow-[0_10px_35px_rgba(0,0,0,0.5)] transition-all"
        >
          {/* Ambient Top Glow Cap */}
          <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-transparent via-indigo-400 to-transparent opacity-80" />

          <div className="flex items-center justify-between pb-3.5 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 shadow-[0_0_15px_rgba(99,102,241,0.25)]">
                <Building2 className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-xs font-bold uppercase tracking-wider text-[rgb(var(--text-primary))]">
                  {selectedFilial ? `Filial ${selectedFilial} (Filtro Ativo)` : 'Faturamento por Filial'}
                </h2>
                <p className="text-[11px] text-[rgb(var(--text-muted))]">
                  {selectedFilial ? `Métricas consolidadas da Filial ${selectedFilial}` : 'Clique na filial para aplicar drill-down'}
                </p>
              </div>
            </div>

            <button
              type="button"
              data-testid="focus-widget-branch-performance"
              onClick={() => onOpenFocusMode?.(selectedFilial ? `Performance da Filial ${selectedFilial}` : 'Performance por Filial', 'filiais', branchPerformance)}
              title="Modo Foco Fullscreen"
              className="flex items-center justify-center w-7 h-7 rounded-lg border border-white/10 bg-white/5 hover:bg-white/15 text-zinc-400 hover:text-white transition-all hover:border-indigo-500/40 hover:text-indigo-400"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Branch List */}
          <div className="py-3 flex flex-col gap-2.5">
            {branchPerformance.map((branch) => {
              const isSelected = selectedFilial === branch.filial
              const pct = Math.round((branch.value / maxBranchVal) * 100)

              return (
                <div
                  key={branch.filial}
                  data-testid={`branch-drilldown-row-${branch.filial}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => onDrilldownBranch(branch.filial)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onDrilldownBranch(branch.filial)
                    }
                  }}
                  className={cn(
                    'group p-2.5 rounded-xl border transition-all cursor-pointer flex flex-col gap-1.5',
                    isSelected
                      ? 'border-indigo-400 bg-indigo-500/15 shadow-[0_0_20px_rgba(99,102,241,0.3)] ring-1 ring-indigo-400/40'
                      : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.06] hover:border-indigo-500/40'
                  )}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-white group-hover:text-indigo-300 transition-colors flex items-center gap-1.5">
                      <span>Filial {branch.filial}</span>
                      {isSelected && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/30 text-indigo-200 border border-indigo-500/40">
                          FILTRADA
                        </span>
                      )}
                    </span>
                    <span className="font-mono font-semibold text-amber-300 tabular-nums">{branch.formatted}</span>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.5 }}
                      className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-indigo-400 to-cyan-400 shadow-[0_0_8px_rgba(99,102,241,0.5)]"
                    />
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-zinc-400">
                    <span>{branch.percentage.toFixed(1)}% da receita total</span>
                    <span className="text-indigo-400 flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform font-medium">
                      Filtrar <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="pt-2.5 border-t border-white/5 text-[10px] text-zinc-500 text-right">
            5 Filiais Operacionais Registradas
          </div>
        </section>
      </div>

      {/* ── ROW 2: Commercial Rankings & Client Concentration ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* 2.1 Top Sellers Leaderboard */}
        <section
          data-testid="widget-top-sellers"
          className="relative flex flex-col justify-between p-4 sm:p-5 rounded-2xl border border-cyan-500/30 bg-zinc-950/80 dark:bg-zinc-950/90 backdrop-blur-xl shadow-[0_10px_35px_rgba(0,0,0,0.5)]"
        >
          {/* Ambient Top Glow Cap */}
          <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80" />

          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-[0_0_12px_rgba(6,182,212,0.25)]">
                <Users className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-xs font-bold uppercase tracking-wider text-[rgb(var(--text-primary))] truncate">
                  {selectedVendedor ? `Vendas por Filial: ${selectedVendedor.name}` : 'Top Vendedores'}
                </h2>
                <p className="text-[10px] text-[rgb(var(--text-muted))] truncate">
                  {selectedVendedor ? `Distribuição de vendas de ${selectedVendedor.name} por filial` : 'Líderes comerciais com drill-down'}
                </p>
              </div>
            </div>

            <button
              type="button"
              data-testid="focus-widget-top-sellers"
              onClick={() => onOpenFocusMode?.(selectedVendedor ? `Vendas por Filial: ${selectedVendedor.name}` : 'Top Vendedores', 'vendedores', topSellers)}
              title="Modo Foco Fullscreen"
              className="flex items-center justify-center w-6 h-6 rounded-lg border border-white/10 bg-white/5 hover:bg-white/15 text-zinc-400 hover:text-white transition-all hover:border-cyan-500/40 hover:text-cyan-400"
            >
              <Maximize2 className="w-3 h-3" />
            </button>
          </div>

          <div className="py-2.5 flex flex-col gap-2">
            {topSellers.slice(0, 5).map((seller, idx) => (
              <div
                key={seller.id || idx}
                title={seller.name}
                data-testid={`seller-drilldown-row-${seller.rca || idx}`}
                role="button"
                tabIndex={0}
                onClick={() => onDrilldownSeller(seller)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onDrilldownSeller(seller)
                  }
                }}
                className="group flex items-center justify-between p-2 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.06] hover:border-cyan-500/40 transition-all cursor-pointer"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span
                    className={cn(
                      'flex items-center justify-center w-5 h-5 rounded-md text-[10px] font-mono font-bold border shrink-0',
                      getRankBadgeClass(idx)
                    )}
                  >
                    {idx + 1}
                  </span>
                  <div className="truncate">
                    <span className="text-xs font-semibold text-white group-hover:text-cyan-300 transition-colors truncate block">
                      {seller.name}
                    </span>
                    <span className="text-[10px] text-zinc-400">
                      RCA {seller.rca} • {seller.filial}
                    </span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-xs font-mono font-bold text-amber-300 block tabular-nums">
                    {seller.formatted}
                  </span>
                  <span className="text-[9px] font-medium text-cyan-400 group-hover:underline">
                    Drill-down →
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-2 border-t border-white/5 text-[10px] text-zinc-500 text-right">
            Classificação por Volume Financeiro
          </div>
        </section>

        {/* 2.2 Top Products Mix */}
        <section
          data-testid="widget-top-products"
          className="relative flex flex-col justify-between p-4 sm:p-5 rounded-2xl border border-rose-500/30 bg-zinc-950/80 dark:bg-zinc-950/90 backdrop-blur-xl shadow-[0_10px_35px_rgba(0,0,0,0.5)]"
        >
          {/* Ambient Top Glow Cap */}
          <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-transparent via-rose-400 to-transparent opacity-80" />

          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-rose-500/20 text-rose-400 border border-rose-500/40 shadow-[0_0_12px_rgba(244,63,94,0.25)]">
                <Package className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-xs font-bold uppercase tracking-wider text-[rgb(var(--text-primary))] truncate">
                  {selectedProduto ? `Detalhamento: ${selectedProduto.name}` : 'Top Produtos'}
                </h2>
                <p className="text-[10px] text-[rgb(var(--text-muted))] truncate">
                  {selectedProduto ? `Histórico de vendas do produto ${selectedProduto.name}` : 'Itens com maior faturamento'}
                </p>
              </div>
            </div>

            <button
              type="button"
              data-testid="focus-widget-top-products"
              onClick={() => onOpenFocusMode?.(selectedProduto ? `Detalhamento: ${selectedProduto.name}` : 'Top Produtos', 'produtos', topProducts)}
              title="Modo Foco Fullscreen"
              className="flex items-center justify-center w-6 h-6 rounded-lg border border-white/10 bg-white/5 hover:bg-white/15 text-zinc-400 hover:text-white transition-all hover:border-rose-500/40 hover:text-rose-400"
            >
              <Maximize2 className="w-3 h-3" />
            </button>
          </div>

          <div className="py-2.5 flex flex-col gap-2">
            {topProducts.slice(0, 5).map((product, idx) => (
              <div
                key={product.codprod || idx}
                title={product.name}
                data-testid={`product-drilldown-row-${product.codprod || idx}`}
                role="button"
                tabIndex={0}
                onClick={() => onDrilldownProduct(product)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onDrilldownProduct(product)
                  }
                }}
                className="group flex items-center justify-between p-2 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.06] hover:border-rose-500/40 transition-all cursor-pointer"
              >
                <div className="flex items-center gap-2.5 min-w-0 pr-2">
                  <span
                    className={cn(
                      'flex items-center justify-center w-5 h-5 rounded-md text-[10px] font-mono font-bold border shrink-0',
                      getRankBadgeClass(idx)
                    )}
                  >
                    {idx + 1}
                  </span>
                  <div className="min-w-0">
                    <span className="text-xs font-semibold text-white group-hover:text-rose-300 transition-colors line-clamp-1 block">
                      {product.name}
                    </span>
                    <span className="text-[10px] text-zinc-400 block truncate">
                      Cód {product.codprod} • {product.quantity_formatted || product.quantity} un
                    </span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-xs font-mono font-bold text-amber-300 block tabular-nums">
                    {product.formatted}
                  </span>
                  <span className="text-[9px] font-medium text-rose-400 group-hover:underline">
                    Drill-down →
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-2 border-t border-white/5 text-[10px] text-zinc-500 text-right">
            Top Itens por Receita Bruta
          </div>
        </section>

        {/* 2.3 Top Clients & AI Signals */}
        <section
          data-testid="widget-top-clients"
          className="relative flex flex-col justify-between p-4 sm:p-5 rounded-2xl border border-purple-500/30 bg-zinc-950/80 dark:bg-zinc-950/90 backdrop-blur-xl shadow-[0_10px_35px_rgba(0,0,0,0.5)] md:col-span-2 lg:col-span-1"
        >
          {/* Ambient Top Glow Cap */}
          <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-transparent via-purple-400 to-transparent opacity-80" />

          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-purple-500/20 text-purple-400 border border-purple-500/40 shadow-[0_0_12px_rgba(168,85,247,0.25)]">
                <UserCheck className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-xs font-bold uppercase tracking-wider text-[rgb(var(--text-primary))] truncate">
                  {selectedCliente ? `Perfil do Cliente: ${selectedCliente.name}` : 'Top Clientes'}
                </h2>
                <p className="text-[10px] text-[rgb(var(--text-muted))] truncate">
                  {selectedCliente ? `Compras e histórico de ${selectedCliente.name}` : 'Concentração de compras por cliente'}
                </p>
              </div>
            </div>

            <button
              type="button"
              data-testid="focus-widget-top-clients"
              onClick={() => onOpenFocusMode?.(selectedCliente ? `Perfil do Cliente: ${selectedCliente.name}` : 'Top Clientes', 'clientes', topClients)}
              title="Modo Foco Fullscreen"
              className="flex items-center justify-center w-6 h-6 rounded-lg border border-white/10 bg-white/5 hover:bg-white/15 text-zinc-400 hover:text-white transition-all hover:border-purple-500/40 hover:text-purple-400"
            >
              <Maximize2 className="w-3 h-3" />
            </button>
          </div>

          <div className="py-2.5 flex flex-col gap-2">
            {topClients.slice(0, 5).map((client, idx) => (
              <div
                key={client.id || idx}
                title={client.name}
                data-testid={`client-drilldown-row-${client.codcliente || idx}`}
                role="button"
                tabIndex={0}
                onClick={() => onDrilldownClient(client)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onDrilldownClient(client)
                  }
                }}
                className="group flex items-center justify-between p-2 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.06] hover:border-purple-500/40 transition-all cursor-pointer"
              >
                <div className="flex items-center gap-2.5 min-w-0 pr-2">
                  <span
                    className={cn(
                      'flex items-center justify-center w-5 h-5 rounded-md text-[10px] font-mono font-bold border shrink-0',
                      getRankBadgeClass(idx)
                    )}
                  >
                    {idx + 1}
                  </span>
                  <div className="min-w-0">
                    <span className="text-xs font-semibold text-white group-hover:text-purple-300 transition-colors truncate block">
                      {client.name}
                    </span>
                    <span className="text-[10px] text-zinc-400 block truncate">
                      Cód {client.codcliente} • {client.invoices_count} pedidos
                    </span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-xs font-mono font-bold text-amber-300 block tabular-nums">
                    {client.formatted}
                  </span>
                  <span className="text-[9px] font-medium text-purple-400 group-hover:underline">
                    Drill-down →
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-2 border-t border-white/5 text-[10px] text-zinc-500 text-right">
            Carteira Ativa de Compradores
          </div>
        </section>
      </div>
    </div>
  )
}
