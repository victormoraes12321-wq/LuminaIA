'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { getApiBase } from '@/lib/utils'
import { ExecutiveHeader } from './ExecutiveHeader'
import { InteractiveKpiGrid } from './InteractiveKpiGrid'
import { ActiveFiltersAndBreadcrumb } from './ActiveFiltersAndBreadcrumb'
import { InteractiveChartsGrid } from './InteractiveChartsGrid'
import { ContextualSideChat } from './ContextualSideChat'
import { AnalyticalFocusMode } from './AnalyticalFocusMode'
import { PinnedWidgetsSection } from './PinnedWidgetsSection'
import { useAuth } from '@/context/AuthContext'
import type {
  AnalyticalContext,
  ActiveFilter,
  BreadcrumbLevel,
  DashboardChatAction,
  ExecutiveDashboardData,
  GovernedInsight,
  TopProductItem,
  TopSellerItem,
  TopClientItem,
  FocusWidgetState,
} from './types'

export function ExecutiveDashboardWorkspace() {
  const { token, user } = useAuth()
  const [sideChatOpen, setSideChatOpen] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // ── Context State ──
  const [context, setContext] = useState<AnalyticalContext>({
    metric: 'faturamento',
    filial: null,
    startDate: '2026-01-01',
    endDate: '2026-08-18',
    periodPreset: 'Ano 2026 (YTD)',
    vendedor: null,
    produto: null,
    cliente: null,
    breadcrumb: [{ id: 'home', label: 'Visão Geral', level: 0, context: {} }],
    activeFilters: [{ id: 'period-default', label: 'Ano 2026 (YTD)', dimension: 'period', value: '2026-01-01:2026-08-18' }],
    focusedWidget: null,
    viewModes: { evolution: 'chart', branches: 'chart' },
  })

  // ── Real API Data State ──
  const [dashboardData, setDashboardData] = useState<ExecutiveDashboardData>({
    metadata: {
      min_available_date: '2024-08-19',
      max_available_date: '2026-08-18',
      effective_start_date: '2026-01-01',
      effective_end_date: '2026-08-18',
      freshness: '18/08/2026 (PostgreSQL Clone)',
      available_branches: ['1', '2', '3', '4', '5'],
    },
    kpis: {
      faturamento: 0,
      quantidade: 0,
      total_notas: 0,
      total_pedidos: 0,
      clientes_ativos: 0,
      vendedores_ativos: 0,
      produtos_distintos: 0,
      filiais_ativas: 0,
      ticket_medio: 0,
      faturamento_formatted: 'R$ 0,00',
      quantidade_formatted: '0 un',
      ticket_medio_formatted: 'R$ 0,00',
      notas_formatted: '0',
      pedidos_formatted: '0',
    },
    evolution: [],
    branch_performance: [],
    top_sellers: [],
    top_products: [],
    top_clients: [],
    insights: [],
    loading: true,
  })

  // ── Fetch Real Data from Backend API ──
  const fetchMetrics = useCallback(async (currentCtx: AnalyticalContext) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (currentCtx.startDate) params.set('start_date', currentCtx.startDate)
      if (currentCtx.endDate) params.set('end_date', currentCtx.endDate)
      if (currentCtx.filial) params.set('filial', currentCtx.filial)
      if (currentCtx.vendedor?.id) params.set('rca', currentCtx.vendedor.id)
      if (currentCtx.produto?.id) params.set('codprod', currentCtx.produto.id)
      if (currentCtx.cliente?.id) params.set('codcli', currentCtx.cliente.id)

      const activeToken =
        token && token !== '__lumina_cookie_session__'
          ? token
          : typeof window !== 'undefined'
            ? localStorage.getItem('lumina_jwt_token')
            : null

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }

      if (activeToken && activeToken !== '__lumina_cookie_session__') {
        headers['Authorization'] = `Bearer ${activeToken}`
      }

      let res = await fetch(`${getApiBase()}/api/v1/dashboard/executive-metrics?${params.toString()}`, {
        method: 'GET',
        headers,
        credentials: 'include',
      })

      // If 401 occurs (e.g. stale Bearer in header), retry with cookie-only session
      if (res.status === 401 && headers['Authorization']) {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('lumina_jwt_token')
        }
        res = await fetch(`${getApiBase()}/api/v1/dashboard/executive-metrics?${params.toString()}`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        })
      }

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Falha ao buscar métricas analíticas.`)
      }

      const json = await res.json()
      if (json.success && json.data) {
        setDashboardData(json.data)
      } else {
        throw new Error('Formato inválido retornado pelo backend.')
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar dados do clone PostgreSQL.')
    } finally {
      setLoading(false)
    }
  }, [token])

  // Refetch when context filters or token change
  useEffect(() => {
    fetchMetrics(context)
  }, [
    token,
    context.startDate,
    context.endDate,
    context.filial,
    context.vendedor?.id,
    context.produto?.id,
    context.cliente?.id,
    fetchMetrics,
  ])

  // ── Filter Handlers ──
  const handleSelectDateRange = (start: string, end: string, presetLabel: string) => {
    setContext(prev => ({
      ...prev,
      startDate: start,
      endDate: end,
      periodPreset: presetLabel,
      activeFilters: [
        ...prev.activeFilters.filter(f => f.dimension !== 'period'),
        { id: `period-${start}-${end}`, label: presetLabel, dimension: 'period', value: `${start}:${end}` },
      ],
    }))
  }

  const handleSelectFilial = (filial: string | null) => {
    if (!filial) {
      setContext(prev => ({
        ...prev,
        filial: null,
        activeFilters: prev.activeFilters.filter(f => f.dimension !== 'filial'),
        breadcrumb: prev.breadcrumb.filter(b => b.level === 0),
      }))
      return
    }

    setContext(prev => ({
      ...prev,
      filial,
      activeFilters: [
        ...prev.activeFilters.filter(f => f.dimension !== 'filial'),
        { id: `filial-${filial}`, label: `Filial ${filial}`, dimension: 'filial', value: filial },
      ],
      breadcrumb: [
        { id: 'home', label: 'Visão Geral', level: 0, context: {} },
        { id: `filial-${filial}`, label: `Filial ${filial}`, level: 1, context: { filial } },
      ],
    }))
  }

  const handleSelectMetric = (metric: any) => {
    setContext(prev => ({ ...prev, metric }))
  }

  const handleToggleViewMode = (widgetId: string) => {
    setContext(prev => ({
      ...prev,
      viewModes: {
        ...prev.viewModes,
        [widgetId]: prev.viewModes[widgetId] === 'table' ? 'chart' : 'table',
      },
    }))
  }

  // ── Drill-Down Handlers ──
  const handleDrilldownBranch = (filial: string) => {
    handleSelectFilial(filial)
  }

  const handleDrilldownSeller = (seller: TopSellerItem) => {
    setContext(prev => {
      const newBreadcrumb: BreadcrumbLevel[] = [
        ...prev.breadcrumb.filter(b => b.level < 2),
        {
          id: `seller-${seller.id}`,
          label: seller.name,
          level: 2,
          context: { vendedor: { id: seller.id, name: seller.name, type: 'vendedor', value: seller.value } },
        },
      ]
      return {
        ...prev,
        vendedor: { id: seller.id, name: seller.name, type: 'vendedor', value: seller.value },
        activeFilters: [
          ...prev.activeFilters.filter(f => f.dimension !== 'vendedor'),
          { id: `vendedor-${seller.id}`, label: `Vendedor: ${seller.name}`, dimension: 'vendedor', value: seller.id },
        ],
        breadcrumb: newBreadcrumb,
      }
    })
  }

  const handleDrilldownProduct = (product: TopProductItem) => {
    setContext(prev => {
      const currentLevel = prev.breadcrumb.length
      const newBreadcrumb: BreadcrumbLevel[] = [
        ...prev.breadcrumb,
        {
          id: `product-${product.id}`,
          label: product.name,
          level: currentLevel,
          context: { produto: { id: product.id, name: product.name, type: 'produto', value: product.value } },
        },
      ]
      return {
        ...prev,
        produto: { id: product.id, name: product.name, type: 'produto', value: product.value },
        activeFilters: [
          ...prev.activeFilters.filter(f => f.dimension !== 'produto'),
          { id: `produto-${product.id}`, label: `Produto: ${product.name}`, dimension: 'produto', value: product.id },
        ],
        breadcrumb: newBreadcrumb,
      }
    })
  }

  const handleDrilldownClient = (client: TopClientItem) => {
    setContext(prev => {
      const currentLevel = prev.breadcrumb.length
      const newBreadcrumb: BreadcrumbLevel[] = [
        ...prev.breadcrumb,
        {
          id: `client-${client.id}`,
          label: client.name,
          level: currentLevel,
          context: { cliente: { id: client.id, name: client.name, type: 'cliente', value: client.value } },
        },
      ]
      return {
        ...prev,
        cliente: { id: client.id, name: client.name, type: 'cliente', value: client.value },
        activeFilters: [
          ...prev.activeFilters.filter(f => f.dimension !== 'cliente'),
          { id: `cliente-${client.id}`, label: `Cliente: ${client.name}`, dimension: 'cliente', value: client.id },
        ],
        breadcrumb: newBreadcrumb,
      }
    })
  }

  const handleSelectInsight = (insight: GovernedInsight) => {
    if (insight.entity_type === 'filial' && insight.entity_id) {
      handleDrilldownBranch(insight.entity_id)
    }
  }

  const handleOpenFocusMode = (title: string, dimension: string, data: any) => {
    setContext(prev => ({
      ...prev,
      focusedWidget: {
        widgetId: dimension,
        title,
        dimension,
        metric: prev.metric,
        data,
      },
    }))
  }

  const handleKpiFocusMode = (kpiState: FocusWidgetState) => {
    let focusData: any[] = []
    let focusTitle = kpiState.title
    let focusDimension = kpiState.dimension

    if (kpiState.widgetId === 'kpi-faturamento') {
      focusData = dashboardData.evolution.map(e => ({ name: e.label, value: e.value, formatted: e.formatted }))
      focusTitle = 'Detalhamento do Faturamento Total'
      focusDimension = 'Mês'
    } else if (kpiState.widgetId === 'kpi-quantidade') {
      focusData = dashboardData.evolution.map(e => ({ name: e.label, value: e.volume, formatted: e.formatted_volume }))
      focusTitle = 'Detalhamento do Volume de Itens'
      focusDimension = 'Mês'
    } else if (kpiState.widgetId === 'kpi-ticket') {
      focusData = dashboardData.branch_performance.map(b => ({
        name: b.name,
        value: (b.value / (b.invoices_count || 1)),
        formatted: `R$ ${(b.value / (b.invoices_count || 1)).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / nota`,
      }))
      focusTitle = 'Detalhamento do Ticket Médio por Filial'
      focusDimension = 'Filial'
    } else if (kpiState.widgetId === 'kpi-notas') {
      focusData = dashboardData.evolution.map(e => ({ name: e.label, value: e.invoices, formatted: `${e.invoices} NF-e` }))
      focusTitle = 'Detalhamento de Notas Fiscais e Pedidos'
      focusDimension = 'Mês'
    } else if (kpiState.widgetId === 'kpi-vendedores') {
      focusData = dashboardData.top_sellers
      focusTitle = 'Detalhamento da Equipe Comercial'
      focusDimension = 'Vendedor'
    } else if (kpiState.widgetId === 'kpi-clientes') {
      focusData = dashboardData.top_clients
      focusTitle = 'Detalhamento da Carteira de Clientes'
      focusDimension = 'Cliente'
    } else if (kpiState.widgetId === 'kpi-produtos') {
      focusData = dashboardData.top_products
      focusTitle = 'Detalhamento do Mix de Produtos'
      focusDimension = 'Produto'
    } else if (kpiState.widgetId === 'kpi-filiais') {
      focusData = dashboardData.branch_performance
      focusTitle = 'Detalhamento das Unidades Ativas'
      focusDimension = 'Filial'
    }

    setContext(prev => ({
      ...prev,
      focusedWidget: {
        widgetId: kpiState.widgetId,
        title: focusTitle,
        dimension: focusDimension,
        metric: kpiState.metric || 'faturamento',
        data: focusData,
      },
    }))
  }

  const handleNavigateBreadcrumb = (targetLevel: number) => {
    if (targetLevel === 0) {
      setContext(prev => ({
        ...prev,
        filial: null,
        vendedor: null,
        produto: null,
        cliente: null,
        breadcrumb: [{ id: 'home', label: 'Visão Geral', level: 0, context: {} }],
        activeFilters: prev.activeFilters.filter(f => f.dimension === 'period'),
      }))
      return
    }

    setContext(prev => {
      const nextBreadcrumb = prev.breadcrumb.slice(0, targetLevel + 1)
      const target = nextBreadcrumb[nextBreadcrumb.length - 1]
      // Clean all entity filters first, then apply target context
      const cleanEntityContext = {
        filial: null,
        vendedor: null,
        produto: null,
        cliente: null,
      }
      return {
        ...prev,
        ...cleanEntityContext,
        ...(target.context || {}),
        breadcrumb: nextBreadcrumb,
      }
    })
  }

  const handleRemoveFilter = (filterId: string) => {
    setContext(prev => {
      const nextFilters = prev.activeFilters.filter(f => f.id !== filterId)
      const removed = prev.activeFilters.find(f => f.id === filterId)
      const patch: Partial<AnalyticalContext> = {}

      if (removed?.dimension === 'filial') patch.filial = null
      if (removed?.dimension === 'vendedor') patch.vendedor = null
      if (removed?.dimension === 'produto') patch.produto = null
      if (removed?.dimension === 'cliente') patch.cliente = null

      return {
        ...prev,
        ...patch,
        activeFilters: nextFilters,
        breadcrumb: prev.breadcrumb.filter(b => {
          if (removed?.dimension === 'filial' && b.context?.filial) return false
          if (removed?.dimension === 'vendedor' && b.context?.vendedor) return false
          if (removed?.dimension === 'produto' && b.context?.produto) return false
          if (removed?.dimension === 'cliente' && b.context?.cliente) return false
          return true
        }),
      }
    })
  }

  const handleClearAllFilters = () => {
    setContext(prev => ({
      ...prev,
      filial: null,
      vendedor: null,
      produto: null,
      cliente: null,
      metric: 'faturamento',
      startDate: '2026-01-01',
      endDate: '2026-08-18',
      periodPreset: 'Este Ano (2026)',
      breadcrumb: [{ id: 'home', label: 'Visão Geral', level: 0, context: {} }],
      activeFilters: [{ id: 'period-default', label: 'Este Ano (2026)', dimension: 'period', value: '2026-01-01:2026-08-18' }],
    }))
  }

  // ── AI Side Chat Query Handler ──
  const handleSideChatQuery = async (
    question: string,
    currentContext: AnalyticalContext
  ): Promise<{ answer: string; action?: DashboardChatAction }> => {
    const norm = question.toLowerCase()

    // 1. Natural Language Filter/Action Detection
    if (norm.includes('mostre filial') || norm.includes('só filial') || norm.includes('apenas filial') || norm.includes('filial 1') || norm.includes('filial 2') || norm.includes('filial 3') || norm.includes('filial 4') || norm.includes('filial 5')) {
      const match = norm.match(/filial\s*([1-5])/)
      const branchId = match ? match[1] : '1'
      const bObj = dashboardData.branch_performance.find(b => b.filial === branchId)
      return {
        answer: `Aplicando filtro para a Filial ${branchId}. O faturamento acumulado desta unidade no período é de ${bObj?.formatted || 'R$ 0,00'} (${bObj?.percentage || 0}% do total) com ${bObj?.sellers_count || 0} vendedores ativos.`,
        action: { action_type: 'APPLY_FILTER', payload: { dimension: 'filial', value: branchId } },
      }
    }

    if (norm.includes('janeiro') || norm.includes('agora janeiro')) {
      return {
        answer: 'Período atualizado para Janeiro de 2026. Atualizando visualizações com os dados reais do período.',
        action: { action_type: 'SET_DATE_RANGE', payload: { startDate: '2026-01-01', endDate: '2026-01-31' } },
      }
    }

    if (norm.includes('fevereiro') || norm.includes('agora fevereiro')) {
      return {
        answer: 'Período atualizado para Fevereiro de 2026. Atualizando visualizações com os dados reais do período.',
        action: { action_type: 'SET_DATE_RANGE', payload: { startDate: '2026-02-01', endDate: '2026-02-28' } },
      }
    }

    if (norm.includes('transforme em tabela') || norm.includes('em tabela') || norm.includes('ver como tabela')) {
      return {
        answer: 'Alternando visualização da evolução temporal para o formato de tabela.',
        action: { action_type: 'TOGGLE_VISUALIZATION', payload: { widget_id: 'evolution', view_mode: 'table' } },
      }
    }

    if (norm.includes('transforme em gráfico') || norm.includes('em grafico') || norm.includes('em gráfico')) {
      return {
        answer: 'Alternando visualização da evolução temporal para gráfico.',
        action: { action_type: 'TOGGLE_VISUALIZATION', payload: { widget_id: 'evolution', view_mode: 'chart' } },
      }
    }

    if (norm.includes('quem vendeu mais') || norm.includes('melhor vendedor') || norm.includes('destaque comercial') || norm.includes('quem mais vendeu')) {
      const topS = dashboardData.top_sellers[0]
      if (topS) {
        return {
          answer: `O vendedor líder no período é ${topS.name}, com ${topS.formatted} faturados em ${topS.sales_count} notas fiscais na Filial ${topS.filial}.`,
          action: {
            action_type: 'DRILLDOWN',
            payload: { entity: { id: topS.id, name: topS.name, type: 'vendedor', value: topS.value } },
          },
        }
      }
    }

    if (norm.includes('top 5 produtos') || norm.includes('produtos mais vendidos')) {
      const pList = dashboardData.top_products.slice(0, 5).map((p, i) => `${i + 1}. ${p.name} (${p.formatted})`).join('\n')
      return {
        answer: `Os 5 produtos com maior faturamento no período são:\n${pList}`,
      }
    }

    if (norm.includes('compara') || norm.includes('comparativo') || norm.includes('compare')) {
      const b1 = dashboardData.branch_performance.find(b => b.filial === '1')
      const b2 = dashboardData.branch_performance.find(b => b.filial === '2')
      if (b1 && b2) {
        return {
          answer: `Comparativo: ${b1.name} (${b1.formatted}, ${b1.percentage}%) vs ${b2.name} (${b2.formatted}, ${b2.percentage}%). A Filial 1 lidera a receita no período.`,
        }
      }
    }

    if (norm.includes('volta') || norm.includes('voltar') || norm.includes('nível anterior')) {
      return {
        answer: 'Voltando um nível na navegação analítica.',
        action: { action_type: 'GO_BACK' },
      }
    }

    if (norm.includes('limpar') || norm.includes('reset') || norm.includes('limpar filtros')) {
      return {
        answer: 'Limpando todos os filtros e retornando à Visão Geral Executiva.',
        action: { action_type: 'RESET_FILTERS' },
      }
    }

    // Contextual Synthesis
    const branchContext = currentContext.filial ? `para a Filial ${currentContext.filial}` : 'para todas as filiais'
    return {
      answer: `Analisando métricas ${branchContext} no período ${currentContext.periodPreset}:\nO faturamento total é de ${dashboardData.kpis.faturamento_formatted} com ${dashboardData.kpis.quantidade_formatted} comercializadas em ${dashboardData.kpis.notas_formatted} notas fiscais.`,
    }
  }

  const handleExecuteAction = (action: DashboardChatAction) => {
    if (action.action_type === 'APPLY_FILTER' && action.payload) {
      if (action.payload.dimension === 'filial' && action.payload.value) {
        handleSelectFilial(action.payload.value)
      }
    }
    if (action.action_type === 'SET_DATE_RANGE' && action.payload) {
      if (action.payload.startDate && action.payload.endDate) {
        handleSelectDateRange(action.payload.startDate, action.payload.endDate, `De ${action.payload.startDate} até ${action.payload.endDate}`)
      }
    }
    if (action.action_type === 'DRILLDOWN' && action.payload?.entity) {
      if (action.payload.entity.type === 'vendedor') {
        handleDrilldownSeller(action.payload.entity as unknown as TopSellerItem)
      }
      if (action.payload.entity.type === 'produto') {
        handleDrilldownProduct(action.payload.entity as unknown as TopProductItem)
      }
    }
    if (action.action_type === 'TOGGLE_VISUALIZATION' && action.payload?.widget_id) {
      handleToggleViewMode(action.payload.widget_id)
    }
    if (action.action_type === 'GO_BACK') {
      if (context.breadcrumb.length > 1) {
        handleNavigateBreadcrumb(context.breadcrumb.length - 2)
      }
    }
    if (action.action_type === 'RESET_FILTERS') {
      handleClearAllFilters()
    }
  }

  return (
    <div
      data-testid="interactive-executive-workspace"
      className="flex h-full w-full overflow-hidden bg-zinc-950 dark:bg-black text-[rgb(var(--text-primary))] relative"
    >
      {/* Ambient Radial Mesh Background with Subtle AI Glow Drift */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_15%,_rgba(6,182,212,0.08)_0%,_transparent_45%),radial-gradient(circle_at_85%_25%,_rgba(99,102,241,0.07)_0%,_transparent_50%),radial-gradient(circle_at_50%_80%,_rgba(245,158,11,0.05)_0%,_transparent_55%)] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:4rem_4rem] pointer-events-none opacity-40" />

      {/* ── Main Left Analytics Grid (Adapts when Side Chat opens) ── */}
      <main className="flex-1 overflow-y-auto p-3.5 sm:p-5 space-y-4 transition-all duration-300 relative z-10">
        {/* 1. Executive Header */}
        <ExecutiveHeader
          startDate={context.startDate}
          endDate={context.endDate}
          periodPreset={context.periodPreset}
          minAvailableDate={dashboardData.metadata?.min_available_date}
          maxAvailableDate={dashboardData.metadata?.max_available_date}
          selectedFilial={context.filial}
          availableBranches={dashboardData.metadata?.available_branches || ['1', '2', '3', '4', '5']}
          freshness={dashboardData.metadata?.freshness || 'Hoje'}
          sideChatOpen={sideChatOpen}
          loading={loading}
          onSelectDateRange={handleSelectDateRange}
          onSelectFilial={handleSelectFilial}
          onToggleSideChat={() => setSideChatOpen(!sideChatOpen)}
          onRefresh={() => fetchMetrics(context)}
        />

        {/* 2. Breadcrumb & Active Filter Badges */}
        <ActiveFiltersAndBreadcrumb
          breadcrumb={context.breadcrumb}
          activeFilters={context.activeFilters}
          onNavigateBreadcrumb={handleNavigateBreadcrumb}
          onRemoveFilter={handleRemoveFilter}
          onClearAllFilters={handleClearAllFilters}
        />

        {/* 3. Interactive KPI Grid (8 real KPIs) */}
        <InteractiveKpiGrid
          data={dashboardData.kpis}
          loading={loading}
          selectedMetric={context.metric}
          onSelectMetric={handleSelectMetric}
          onOpenFocusMode={handleKpiFocusMode}
        />

        {/* 4. Charts, Tables & Lateral Rankings */}
        <InteractiveChartsGrid
          evolution={dashboardData.evolution}
          branchPerformance={dashboardData.branch_performance}
          topProducts={dashboardData.top_products}
          topSellers={dashboardData.top_sellers}
          topClients={dashboardData.top_clients}
          insights={dashboardData.insights}
          loading={loading}
          selectedFilial={context.filial}
          selectedVendedor={context.vendedor}
          selectedProduto={context.produto}
          selectedCliente={context.cliente}
          viewModes={context.viewModes}
          onToggleViewMode={handleToggleViewMode}
          onDrilldownBranch={handleDrilldownBranch}
          onDrilldownSeller={handleDrilldownSeller}
          onDrilldownProduct={handleDrilldownProduct}
          onDrilldownClient={handleDrilldownClient}
          onSelectInsight={handleSelectInsight}
          onOpenFocusMode={handleOpenFocusMode}
        />

        {/* 5. Isolated Pinned User Widgets & Custom Insights */}
        <PinnedWidgetsSection />
      </main>

      {/* ── Contextual AI Side Chat (Docked on Right) ── */}
      <div
        className={cn(
          'transition-all duration-300 overflow-hidden shrink-0 flex',
          sideChatOpen ? 'w-[320px] lg:w-[350px] 2xl:w-[380px]' : 'w-0'
        )}
      >
        <ContextualSideChat
          open={sideChatOpen}
          context={context}
          loading={loading}
          onClose={() => setSideChatOpen(false)}
          onSendQuery={handleSideChatQuery}
          onExecuteAction={handleExecuteAction}
        />
      </div>

      {/* ── Analytical Focus Mode Modal (Fullscreen deep dive) ── */}
      <AnalyticalFocusMode
        focusedWidget={context.focusedWidget}
        onClose={() => setContext(prev => ({ ...prev, focusedWidget: null }))}
        onDrilldownEntity={entity => {
          if (entity.type === 'vendedor') handleDrilldownSeller(entity as any)
          if (entity.type === 'produto') handleDrilldownProduct(entity as any)
          if (entity.type === 'filial') handleDrilldownBranch(entity.id)
          setContext(prev => ({ ...prev, focusedWidget: null }))
        }}
      />
    </div>
  )
}
