'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { generateId, truncate, getApiBase } from '@/lib/utils'
import { repairObjectText, repairTextEncoding } from '@/lib/textEncoding'
import { useAuth } from '@/context/AuthContext'
import type {
  ChatMessage,
  FavoriteItem,
  HistoryItem,
  QueryMode,
  QueryResponse,
  ChartType,
} from '@/types/lumina'
import { ExecutionStatus, VisualizationType } from '@/types/dashboard-runtime'
import type {
  ConversationGraph,
  ConversationNode,
  DashboardState,
  ExecutionResult,
} from '@/types/dashboard-runtime'

// â”€â”€ Constants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface HistoryApiItem {
  id: string
  pergunta: string
  view_name: string | null
  chart_type: ChartType | null
  timestamp: string
}

interface FavoriteApiItem {
  id: string
  titulo: string
  view_name: string
  chart_type: ChartType
  parametros: Record<string, string>
  query_id: string
}

function createConversationSessionId() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return `lumina-${globalThis.crypto.randomUUID()}`
  }
  return `lumina-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

// â”€â”€ Return Type â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export interface UseLuminaQueryReturn {
  /** Whether a query is in flight */
  loading: boolean
  /** Error message from last failed query */
  error: string | null
  /** Full conversation history (user + assistant bubbles) */
  messages: ChatMessage[]
  /** Compact history items for sidebar */
  history: HistoryItem[]
  /** Favorites saved in this session */
  favorites: FavoriteItem[]
  /** Last successful API response (used to render the Bento Grid) */
  lastResponse: QueryResponse | null
  /** Send a natural language query to LuminaAI */
  sendQuery: (pergunta: string) => Promise<void>
  /** Clear the current error state */
  clearError: () => void
  /** Inject a question string back into the chat input */
  setInjectedQuery: React.Dispatch<React.SetStateAction<string>>
  /** The currently injected query string (consumed by ChatInterface) */
  injectedQuery: string
  /** Save / unsave a query as favorite */
  toggleFavorite: (response: QueryResponse, titulo?: string) => void
  /** Check if a query_id is already favorited */
  isFavorite: (queryId: string) => boolean
  /** Carrega o histórico recente do PostgreSQL */
  fetchHistory: () => Promise<void>
  /** Carrega a lista de favoritos do PostgreSQL */
  fetchFavorites: () => Promise<void>
  /** Active response depth mode */
  mode: QueryMode
  /** Change active response depth mode and persist choice */
  changeMode: (mode: QueryMode) => void
  /** The active conversation graph */
  conversationGraph: ConversationGraph
  /** Stable backend conversation session id for the current chat */
  sessionId: string
  /** Reset the visible chat and start a new backend conversation session */
  resetConversation: () => void
  /** Intercept visual commands locally */
  classify_and_handle_ui_command: (pergunta: string) => boolean
  /** Backtrack to a previous conversation node */
  backtrackToNode: (nodeId: string) => void
}

// â”€â”€ Hook â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export function useLuminaQuery(): UseLuminaQueryReturn {
  const { token, user, logout } = useAuth()
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState<string | null>(null)
  const [messages, setMessages]         = useState<ChatMessage[]>([])
  const [history, setHistory]           = useState<HistoryItem[]>([])
  const [favorites, setFavorites]       = useState<FavoriteItem[]>([])
  const [lastResponse, setLastResponse] = useState<QueryResponse | null>(null)
  const [conversationGraph, setConversationGraph] = useState<ConversationGraph>({
    nodes: {},
    current_node_id: null,
  })
  const [sessionId, setSessionId] = useState(createConversationSessionId)
  const [injectedQuery, setInjectedQuery] = useState('')
  const [mode, setMode] = useState<QueryMode>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('lumina_query_mode')
      if (saved === 'operational' || saved === 'analytical' || saved === 'executive') {
        return saved
      }
    }
    return 'analytical'
  })

  const changeMode = useCallback((newMode: QueryMode) => {
    setMode(newMode)
    if (typeof window !== 'undefined') {
      localStorage.setItem('lumina_query_mode', newMode)
    }
  }, [])

  // Keep a ref to abort ongoing requests if unmounted
  const abortRef = useRef<AbortController | null>(null)

  const resetConversation = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
    setError(null)
    setMessages([])
    setLastResponse(null)
    setConversationGraph({
      nodes: {},
      current_node_id: null,
    })
    setInjectedQuery('')
    setSessionId(createConversationSessionId())
  }, [])

  // â”€â”€ Hydration Methods â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  // Busca histórico de pesquisas salvo no PostgreSQL
  const fetchHistory = useCallback(async () => {
    if (!token) return
    try {
      const res = await fetch(`${getApiBase()}/api/v1/query/history`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (res.status === 401) {
        void logout()
        return
      }
      if (res.ok) {
        const data = repairObjectText(await res.json()) as HistoryApiItem[]
        const formatted: HistoryItem[] = data.map((item) => ({
          id: item.id,
          pergunta: item.pergunta,
          viewName: item.view_name,
          chartType: item.chart_type,
          timestamp: new Date(item.timestamp),
        }))
        setHistory(formatted)
      }
    } catch (err) {
      console.error('Erro ao hidratar histórico:', err)
    }
  }, [token, logout])

  // Busca favoritos salvos no PostgreSQL
  const fetchFavorites = useCallback(async () => {
    if (!token) return
    try {
      const res = await fetch(`${getApiBase()}/api/v1/query/favorites`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (res.status === 401) {
        void logout()
        return
      }
      if (res.ok) {
        const data = repairObjectText(await res.json()) as FavoriteApiItem[]
        const formatted: FavoriteItem[] = data.map((item) => ({
          id: item.id,
          titulo: item.titulo,
          viewName: item.view_name,
          chartType: item.chart_type,
          parametros: item.parametros,
          queryId: item.query_id,
        }))
        setFavorites(formatted)
      }
    } catch (err) {
      console.error('Erro ao hidratar favoritos:', err)
    }
  }, [token, logout])

  // Executa a hidratação na montagem e sempre que o token mudar
  useEffect(() => {
    if (token) {
      void Promise.resolve().then(() => {
        void fetchHistory()
        void fetchFavorites()
      })
    } else {
      queueMicrotask(() => {
        setHistory([])
        setFavorites([])
      })
    }
  }, [token, fetchHistory, fetchFavorites])

  // ─── Command Interceptor ──────────────────

  const classify_and_handle_ui_command = useCallback((pergunta: string): boolean => {
    const text = pergunta.toLowerCase().trim()
    if (!lastResponse) return false

    // Identificar nó ativo
    let activeNodeId = conversationGraph.current_node_id
    let activeNode = activeNodeId ? conversationGraph.nodes[activeNodeId] : null

    // Fallback: inicializa o grafo com o nó raiz correspondente ao lastResponse
    if (!activeNode) {
      activeNodeId = lastResponse.query_id
      const executionResult: ExecutionResult = {
        status: lastResponse.view_name ? ExecutionStatus.READY : ExecutionStatus.INVALID,
        dataset: (lastResponse.chart_data && 'rows' in lastResponse.chart_data) ? (lastResponse.chart_data.rows as Record<string, unknown>[]) : [],
        metadata: { view_name: lastResponse.view_name, query_id: lastResponse.query_id },
        warnings: [],
        execution_time_ms: lastResponse.telemetry?.timings?.total_pipeline ?? 0,
        row_count: (lastResponse.chart_data && 'rows' in lastResponse.chart_data) ? (lastResponse.chart_data.rows as unknown[]).length : 0,
        cache_hit: false
      }
      const dashboardState: DashboardState = {
        chart_type: (lastResponse.chart_type as any) || 'TABLE',
        selected_chart_id: lastResponse.query_id,
        drilldown_stack: [],
        hidden_columns: [],
        visible_metrics: [],
        selected_filters: {},
        pagination_page: 1
      }
      activeNode = {
        node_id: activeNodeId,
        parent_id: null,
        children_ids: [],
        user_query: lastResponse.pergunta_original || 'Query original',
        execution_result: executionResult,
        dashboard_state: dashboardState
      }

      setConversationGraph(prev => ({
        ...prev,
        nodes: { ...prev.nodes, [activeNodeId!]: activeNode! },
        current_node_id: activeNodeId
      }))
    }

    // 1. Alteração de Tipo de Gráfico
    let targetChartType: VisualizationType | null = null
    if (text.includes('barras') || text.includes('barra')) {
      targetChartType = VisualizationType.BAR
    } else if (text.includes('linhas') || text.includes('linha')) {
      targetChartType = VisualizationType.LINE
    } else if (text.includes('pizza') || text.includes('pie')) {
      targetChartType = VisualizationType.PIE
    } else if (text.includes('tabela') || text.includes('grade') || text.includes('dados')) {
      targetChartType = VisualizationType.TABLE
    } else if (text.includes('kpi') || text.includes('cards') || text.includes('card')) {
      targetChartType = VisualizationType.KPI_CARD
    } else if (text.includes('donut') || text.includes('rosca')) {
      targetChartType = VisualizationType.DONUT
    } else if (text.includes('scatter') || text.includes('dispersao')) {
      targetChartType = VisualizationType.SCATTER
    } else if (text.includes('heatmap') || text.includes('calor')) {
      targetChartType = VisualizationType.HEATMAP
    }

    const isChangeChart = (text.includes('mudar') || text.includes('alterar') || text.includes('exibir') || text.includes('mostrar') || text.includes('tipo') || text.includes('como') || text.includes('renderizar')) && targetChartType !== null

    if (isChangeChart && targetChartType) {
      // Atualiza lastResponse
      setLastResponse(prev => prev ? { ...prev, chart_type: targetChartType as any } : null)

      // Atualiza DashboardState no Grafo
      setConversationGraph(prev => {
        const nodeId = prev.current_node_id || activeNodeId!
        const node = prev.nodes[nodeId] || activeNode!
        const updatedState: DashboardState = {
          ...node.dashboard_state,
          chart_type: targetChartType!
        }
        return {
          ...prev,
          nodes: {
            ...prev.nodes,
            [nodeId]: { ...node, dashboard_state: updatedState }
          }
        }
      })

      // Injeta mensagem do assistente confirmando alteração instantânea
      const assistantMsg: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: `Entendido! Alterei a visualização ativa para o gráfico de **${targetChartType}** instantaneamente em memória (zero Network Requests efetuados).`,
        timestamp: new Date(),
        queryResponse: lastResponse ? { ...lastResponse, chart_type: targetChartType as any } : undefined
      }
      setMessages(prev => [...prev, assistantMsg])
      return true
    }

    // 2. Ordenação de Colunas
    const sortMatch = text.match(/(?:ordenar|ordene|organizar|organize)\s+(?:por\s+)?([a-z0-9_áéíóúâêîôûãõç\s]+)/i)
    if (sortMatch) {
      const field = sortMatch[1].trim().toLowerCase()
      let matchedKey = ''
      
      setLastResponse(prev => {
        if (!prev || !prev.chart_data || !('rows' in prev.chart_data)) return prev
        const rows = [...(prev.chart_data.rows as Record<string, any>[])]
        if (rows.length === 0) return prev

        const firstRow = rows[0]
        matchedKey = Object.keys(firstRow).find(k => k.toLowerCase() === field || (prev.chart_data && 'columns' in prev.chart_data && (prev.chart_data.columns as any[]).some(col => col.key === k && col.label.toLowerCase() === field))) || field

        rows.sort((a, b) => {
          const valA = a[matchedKey]
          const valB = b[matchedKey]
          if (typeof valA === 'number' && typeof valB === 'number') {
            return valB - valA;
          }
          return String(valA).localeCompare(String(valB))
        })

        return {
          ...prev,
          chart_data: {
            ...prev.chart_data,
            rows: rows
          }
        }
      })

      if (matchedKey) {
        // Atualiza grafo
        setConversationGraph(prev => {
          const nodeId = prev.current_node_id || activeNodeId!
          const node = prev.nodes[nodeId] || activeNode!
          const updatedState: DashboardState = {
            ...node.dashboard_state,
            visible_metrics: [...new Set([...node.dashboard_state.visible_metrics, matchedKey])]
          }
          return {
            ...prev,
            nodes: {
              ...prev.nodes,
              [nodeId]: { ...node, dashboard_state: updatedState }
            }
          }
        })

        const assistantMsg: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: `Entendido! Ordenei a tabela local pelo campo **${field}** instantaneamente em memória (zero Network Requests efetuados).`,
          timestamp: new Date(),
          queryResponse: lastResponse || undefined
        }
        setMessages(prev => [...prev, assistantMsg])
        return true
      }
    }

    // 3. Filtragem Local
    const filterMatch = text.match(/(?:filtrar|filtre|filtro)\s+(?:por\s+)?([a-z0-9_áéíóúâêîôûãõç]+)\s+(?:como|=)\s+(.+)/i)
    if (filterMatch) {
      const field = filterMatch[1].trim().toLowerCase()
      const val = filterMatch[2].trim().toLowerCase()
      let filteredCount = 0

      setLastResponse(prev => {
        if (!prev || !prev.chart_data || !('rows' in prev.chart_data)) return prev
        
        const originalRows = (activeNode && activeNode.execution_result && activeNode.execution_result.dataset.length > 0)
          ? (activeNode.execution_result.dataset as Record<string, any>[])
          : (prev.chart_data.rows as Record<string, any>[])
        
        const firstRow = originalRows[0] || {}
        const matchedKey = Object.keys(firstRow).find(k => k.toLowerCase() === field) || field

        const filtered = originalRows.filter(row => String(row[matchedKey] ?? '').toLowerCase().includes(val))
        filteredCount = filtered.length

        return {
          ...prev,
          chart_data: {
            ...prev.chart_data,
            rows: filtered
          }
        }
      })

      // Atualiza grafo
      setConversationGraph(prev => {
        const nodeId = prev.current_node_id || activeNodeId!
        const node = prev.nodes[nodeId] || activeNode!
        const updatedState: DashboardState = {
          ...node.dashboard_state,
          selected_filters: { ...node.dashboard_state.selected_filters, [field]: val }
        }
        return {
          ...prev,
          nodes: {
            ...prev.nodes,
            [nodeId]: { ...node, dashboard_state: updatedState }
          }
        }
      })

      const assistantMsg: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: `Entendido! Filtrei os registros locais por **${field} = "${val}"** (encontrado ${filteredCount} item(ns)). Processamento instantâneo em memória concluído sem Network Requests.`,
        timestamp: new Date(),
        queryResponse: lastResponse || undefined
      }
      setMessages(prev => [...prev, assistantMsg])
      return true
    }

    // 4. Paginação
    if (text.includes('pagina') || text.includes('paginação') || text.includes('avançar') || text.includes('voltar')) {
      const pageMatch = text.match(/(?:pagina|página)\s*(\d+)/i)
      let targetPage = 1
      if (pageMatch) {
        targetPage = parseInt(pageMatch[1], 10)
      } else if (text.includes('proxima') || text.includes('avançar')) {
        targetPage = (activeNode?.dashboard_state.pagination_page || 1) + 1
      } else if (text.includes('anterior') || text.includes('voltar')) {
        targetPage = Math.max(1, (activeNode?.dashboard_state.pagination_page || 1) - 1)
      }

      setConversationGraph(prev => {
        const nodeId = prev.current_node_id || activeNodeId!
        const node = prev.nodes[nodeId] || activeNode!
        const updatedState: DashboardState = {
          ...node.dashboard_state,
          pagination_page: targetPage
        }
        return {
          ...prev,
          nodes: {
            ...prev.nodes,
            [nodeId]: { ...node, dashboard_state: updatedState }
          }
        }
      })

      const assistantMsg: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: `Entendido! Alterei a página de exibição local para **Página ${targetPage}** instantaneamente em memória.`,
        timestamp: new Date(),
        queryResponse: lastResponse || undefined
      }
      setMessages(prev => [...prev, assistantMsg])
      return true
    }

    return false
  }, [lastResponse, conversationGraph])

  // ─── Send Query ───────────────────────────

  const sendQuery = useCallback(async (pergunta: string) => {
    const trimmed = pergunta.trim()
    if (!trimmed || loading) return

    // Abort previous in-flight request if any
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    setError(null)

    // Append user message immediately
    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])

    // Intercept UI commands locally to avoid network requests
    const wasUiCommand = classify_and_handle_ui_command(trimmed)
    if (wasUiCommand) {
      setLoading(false)
      return
    }

    try {
      if (!token || !user) {
        throw new Error('Você não está autenticado no sistema.')
      }

      // Mapeia o histórico recente do chat (limita a 10 mensagens)
      const chatHistory = messages
        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
        .slice(-10)
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }))

      const res = await fetch(`${getApiBase()}/api/v1/query/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          pergunta: trimmed,
          tenant_id: user.tenant_id,
          session_id: sessionId,
          history: chatHistory,
          mode: mode,
          parent_id: conversationGraph.current_node_id,
        }),
        signal: controller.signal,
      })

      if (res.status === 401) {
        void logout()
        throw new Error('Sessão expirada. Por favor, faça login novamente.')
      }

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({
          error: { message: `Erro HTTP ${res.status}` },
        }))
        throw new Error(
          repairTextEncoding(
            (errBody as { error?: { message?: string } }).error?.message ??
              `HTTP ${res.status}`,
          ),
        )
      }

      const data = repairObjectText(await res.json()) as QueryResponse
      setLastResponse(data)

      // Registra o novo nó no grafo analítico da conversa
      const nodeId = data.query_id
      const executionResult: ExecutionResult = {
        status: data.view_name ? ExecutionStatus.READY : ExecutionStatus.INVALID,
        dataset: (data.chart_data && 'rows' in data.chart_data) ? (data.chart_data.rows as Record<string, unknown>[]) : [],
        metadata: { view_name: data.view_name, query_id: data.query_id },
        warnings: [],
        execution_time_ms: data.telemetry?.timings?.total_pipeline ?? 0,
        row_count: (data.chart_data && 'rows' in data.chart_data) ? (data.chart_data.rows as unknown[]).length : 0,
        cache_hit: false
      }
      const dashboardState: DashboardState = {
        chart_type: (data.chart_type as any) || 'TABLE',
        selected_chart_id: data.query_id,
        drilldown_stack: [],
        hidden_columns: [],
        visible_metrics: [],
        selected_filters: {},
        pagination_page: 1
      }
      const newNode: ConversationNode = {
        node_id: nodeId,
        parent_id: conversationGraph.current_node_id,
        children_ids: [],
        user_query: trimmed,
        execution_result: executionResult,
        dashboard_state: dashboardState
      }

      setConversationGraph(prev => {
        const nodes = { ...prev.nodes, [nodeId]: newNode }
        if (prev.current_node_id && nodes[prev.current_node_id]) {
          nodes[prev.current_node_id] = {
            ...nodes[prev.current_node_id],
            children_ids: [...nodes[prev.current_node_id].children_ids, nodeId]
          }
        }
        return {
          ...prev,
          nodes,
          current_node_id: nodeId
        }
      })

      // â”€â”€ Build assistant narrative â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
      const formatViewName = (name?: string | null) => {
        if (!name) return 'Análise de Vendas'
        let clean = name.replace(/^VW_/i, '')
        clean = clean.replace(/_/g, ' ')
        return clean.toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
      }

      let assistantText = ''

      if (data.view_name) {
        // Prefer business explanations returned by the backend; only fall back to a generic report message.
        const fallbackReportText = `Aqui está o relatório detalhado para a ${formatViewName(data.view_name)}. Você pode visualizar os dados consolidados na tabela e no gráfico interativo abaixo.`
        assistantText = repairTextEncoding(data.mensagem ?? data.resposta_direta ?? data.ia_analise ?? fallbackReportText)
      } else {
        assistantText = repairTextEncoding(
          data.mensagem ??
          data.resposta_direta ??
          'Não encontrei uma análise correspondente à sua pergunta. ' +
            'Tente reformular com mais detalhes ou use termos como "vendas", "clientes", "KPIs".',
        )
      }

      const assistantMsg: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: assistantText,
        timestamp: new Date(),
        queryResponse: data,
      }
      setMessages(prev => [...prev, assistantMsg])

      // â”€â”€ Update sidebar history â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
      if (data.view_name) {
        const histItem: HistoryItem = {
          id: data.query_id,
          pergunta: truncate(trimmed, 48),
          viewName: data.view_name,
          chartType: data.chart_type,
          timestamp: new Date(),
        }
        setHistory(prev => [histItem, ...prev].slice(0, 20))
      }
    } catch (err) {
      // AbortError is expected when component unmounts
      if (err instanceof DOMException && err.name === 'AbortError') return

      const message =
        err instanceof Error
          ? err.message
          : 'Erro inesperado ao conectar com o servidor.'

      setError(message)

      const errMsg: ChatMessage = {
        id: generateId(),
        role: 'error',
        content: message,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
      }
      setLoading(false)
    }
  }, [classify_and_handle_ui_command, conversationGraph, loading, logout, messages, mode, sessionId, token, user])

  // â”€â”€ Favorites â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  const toggleFavorite = useCallback(
    (response: QueryResponse, titulo?: string) => {
      if (!response.view_name || !response.chart_type) return

      setFavorites(prev => {
        const exists = prev.some(f => f.queryId === response.query_id)
        if (exists) {
          return prev.filter(f => f.queryId !== response.query_id)
        }
        const newFav: FavoriteItem = {
          id: generateId(),
          queryId: response.query_id,
          titulo: titulo ?? truncate(response.pergunta_original, 36),
          viewName: response.view_name!,
          chartType: response.chart_type!,
          parametros: response.parametros_extraidos,
        }
        return [newFav, ...prev].slice(0, 20)
      })
    },
    [],
  )

  const isFavorite = useCallback(
    (queryId: string) => favorites.some(f => f.queryId === queryId),
    [favorites],
  )

  const clearError = useCallback(() => setError(null), [])

  const backtrackToNode = useCallback((nodeId: string) => {
    const node = conversationGraph.nodes[nodeId]
    if (!node || !node.execution_result || !node.dashboard_state) return

    const response: QueryResponse = {
      query_id: node.node_id,
      view_name: (node.execution_result.metadata?.view_name as string) || null,
      view_catalog_id: null,
      chart_type: node.dashboard_state.chart_type as any,
      chart_data: {
        rows: node.execution_result.dataset,
        columns: node.execution_result.dataset.length > 0
          ? Object.keys(node.execution_result.dataset[0]).map(k => ({ key: k, label: k.replace(/_/g, ' ').toUpperCase(), type: 'string' }))
          : [],
        total_rows: node.execution_result.dataset.length,
        resumo: {}
      },
      visualizations: null,
      parametros_extraidos: {},
      ia_confianca: 1.0,
      ia_justificativa: null,
      pergunta_original: node.user_query,
      pode_favoritar: true,
      mensagem: null
    }

    setLastResponse(response)
    setConversationGraph(prev => ({
      ...prev,
      current_node_id: nodeId
    }))

    const infoMsg: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: `Viagem no tempo realizada! Restaurado o estado de análise para a pergunta: **"${node.user_query}"** (dados carregados instantaneamente do cache local).`,
      timestamp: new Date(),
      queryResponse: response
    }
    setMessages(prev => [...prev, infoMsg])
  }, [conversationGraph])

  return {
    loading,
    error,
    messages,
    history,
    favorites,
    lastResponse,
    sendQuery,
    clearError,
    setInjectedQuery,
    injectedQuery,
    toggleFavorite,
    isFavorite,
    fetchHistory,
    fetchFavorites,
    mode,
    changeMode,
    conversationGraph,
    sessionId,
    resetConversation,
    classify_and_handle_ui_command,
    backtrackToNode,
  }
}
