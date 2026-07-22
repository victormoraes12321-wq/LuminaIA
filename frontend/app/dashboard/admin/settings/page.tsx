'use client'

/**
 * LuminaAI — Painel Administrativo de Configurações SaaS
 * -----------------------------------------------------
 * Página para gerenciamento de configurações do Tenant. Organizada em 3 abas
 * interativas com animações fluidas do Framer Motion:
 * 1. Visual: Nome da empresa, URL da logo e cores primárias/secundárias.
 * 2. IA: Modelo OpenAI de NLP, temperatura de amostragem e instruções personalizadas.
 * 3. Banco de Dados: Host, porta, usuário, SID/Service Name do Oracle Database,
 *    incluindo teste de conexão em tempo real (Thin Mode).
 * 
 * Regra de Segurança (RBAC):
 * - Acesso restrito a usuários com papel 'ADMIN'.
 * - Caso um usuário sem permissão acesse, exibe uma tela elegante de Acesso Negado.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Palette,
  Bot,
  Database,
  ShieldAlert,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  XCircle,
  Save,
  Play,
  Plus,
  Trash2,
  Key,
  History,
  RefreshCw
} from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '@/context/AuthContext'
import { GlassCard } from '@/components/ui/GlassCard'
import { cn, getApiBase } from '@/lib/utils'
import { TooltipHelp } from '@/components/ui/TooltipHelp'
import { Sidebar } from '@/components/Sidebar'

// Tipo para as abas de configurações
type TabID = 'visual' | 'ia' | 'db' | 'sync' | 'audit'

// Interface para os modelos de IA cadastrados
interface RegisteredAIModel {
  id: string
  name: string
  model_base: string
  api_key: string
}

interface AuditLogItem {
  id: string
  pergunta: string
  ia_confianca?: number | null
  tempo_resposta_ms?: number | null
  criado_em: string
  usuario: {
    nome: string
    email: string
  }
  view: {
    nome_view_oracle?: string | null
  }
}

interface SyncProgressState {
  active: boolean
  status: 'idle' | 'running' | 'completed' | 'failed' | string
  phase: string
  percent: number
  current_view?: string | null
  current_view_index?: number
  total_views?: number
  current_view_rows?: number
  current_view_estimated_rows?: number | null
  processed_views?: number
  processed_rows?: number
  total_rows?: number
  message?: string
  updated_at?: string | null
  started_at?: string | null
  finished_at?: string | null
  error?: string | null
}

export default function AdminSettingsPage() {
  const { user, token } = useAuth()
  
  // Controle de Abas
  const [activeTab, setActiveTab] = useState<TabID>('visual')
  
  // Estados de Carregamento e Notificações
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testingConnection, setTestingConnection] = useState(false)
  const [globalError, setGlobalError] = useState<string | null>(null)
  const [globalSuccess, setGlobalSuccess] = useState<string | null>(null)
  
  // Estado específico para o teste de conexão Oracle
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  // ── ESTADO DAS CONFIGURAÇÕES ──
  
  // Aba 1: Visual
  const [tenantName, setTenantName] = useState('')
  const [logoUrl, setLogoUrl] = useState('')
  const [primaryColor, setPrimaryColor] = useState('#6C63FF')
  const [secondaryColor, setSecondaryColor] = useState('#00D2D3')
  const [borderRadius, setBorderRadius] = useState('14px')
  
  // Aba 2: IA
  const [iaTemperature, setIaTemperature] = useState(0.0)
  const [iaInstructions, setIaInstructions] = useState('')
  
  // Modelos de IA Registrados
  const [registeredModels, setRegisteredModels] = useState<RegisteredAIModel[]>([])
  const [activeModelId, setActiveModelId] = useState<string>('')
  
  // Form para nova IA
  const [newModelName, setNewModelName] = useState('')
  const [newModelBase, setNewModelBase] = useState('gpt-4o-mini')
  const [newModelApiKey, setNewModelApiKey] = useState('')

  // Estados de teste de conexão de IA
  const [testingAiId, setTestingAiId] = useState<string | null>(null)
  const [testingNewAi, setTestingNewAi] = useState(false)
  const [aiTestResult, setAiTestResult] = useState<{ id: string; success: boolean; message: string } | null>(null)


  // Estados dos logs de auditoria
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([])
  const [loadingAudit, setLoadingAudit] = useState(false)
  
  // Aba 3: Banco de Dados Oracle
  const [dbHost, setDbHost] = useState('')
  const [dbPort, setDbPort] = useState(1521)
  const [dbUser, setDbUser] = useState('')
  const [dbPassword, setDbPassword] = useState('••••••••')
  const [dbSid, setDbSid] = useState('')
  const [dbServiceName, setDbServiceName] = useState('')

  // Aba 3.5: PostgreSQL Clone
  const [cloneHost, setCloneHost] = useState('')
  const [clonePort, setClonePort] = useState(5432)
  const [cloneUser, setCloneUser] = useState('')
  const [clonePassword, setClonePassword] = useState('••••••••')
  const [cloneDatabase, setCloneDatabase] = useState('')
  
  // Sincronização
  const [syncEnabled, setSyncEnabled] = useState(false)
  const [syncTimes, setSyncTimes] = useState<string[]>([])
  const [newSyncTime, setNewSyncTime] = useState('')
  
  // Status da Sincronização
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null)
  const [lastSyncStatus, setLastSyncStatus] = useState<string | null>(null)
  const [lastSyncMessage, setLastSyncMessage] = useState<string | null>(null)
  
  // Estados de conexão e sync
  const [testingClone, setTestingClone] = useState(false)
  const [testCloneResult, setTestCloneResult] = useState<{ success: boolean; message: string } | null>(null)
  const [syncingNow, setSyncingNow] = useState(false)
  const [syncNowResult, setSyncNowResult] = useState<{ success: boolean; message: string } | null>(null)
  const [syncProgress, setSyncProgress] = useState<SyncProgressState | null>(null)
  const [syncProgressPolling, setSyncProgressPolling] = useState(false)
  const syncProgressRef = useRef<SyncProgressState | null>(null)

  const API_BASE = getApiBase()
  const isAdmin = user?.role === 'ADMIN'

  // Busca as configurações atuais do tenant (dados mascarados pelo backend)
  const fetchSettings = useCallback(async () => {
    if (!token || !isAdmin) return
    try {
      setLoading(true)
      setGlobalError(null)
      const res = await fetch(`${API_BASE}/api/v1/tenant/settings`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao buscar configurações do tenant.')
      }
      
      const data = await res.json()
      
      // Carrega dados da Aba 1 (Visual)
      setTenantName(data.nome || '')
      setLogoUrl(data.logo_url || '')
      setPrimaryColor(data.tema_config?.primary_color || '#6C63FF')
      setSecondaryColor(data.tema_config?.secondary_color || '#00D2D3')
      setBorderRadius(data.tema_config?.border_radius || '14px')
      
      // Carrega dados da Aba 2 (IA)
      setIaTemperature(data.ia_config?.temperature ?? 0.0)
      setIaInstructions(data.ia_config?.custom_instructions || '')
      
      // Carrega modelos registrados e ativo
      const regModels = (data.ia_config?.registered_models || []).map((model: RegisteredAIModel) => ({
        ...model,
        model_base: 'gpt-4o-mini',
      }))
      const actModelId = data.ia_config?.active_model_id || ''
      
      // Migração de chaves legadas se houver chave salva mas nenhuma lista
      if (regModels.length === 0 && data.ia_config?.api_key) {
        const legacyModel = {
          id: 'legacy-default',
          name: 'OpenAI Principal (Legado)',
          model_base: 'gpt-4o-mini',
          api_key: data.ia_config?.api_key
        }
        setRegisteredModels([legacyModel])
        setActiveModelId('legacy-default')
      } else {
        setRegisteredModels(regModels)
        setActiveModelId(actModelId)
      }
      
      // Carrega dados da Aba 3 (Oracle)
      setDbHost(data.oracle_conn?.host || '')
      setDbPort(Number(data.oracle_conn?.port) || 1521)
      setDbUser(data.oracle_conn?.user || '')
      setDbPassword(data.oracle_conn?.password || '••••••••')
      setDbSid(data.oracle_conn?.sid || '')
      setDbServiceName(data.oracle_conn?.service_name || '')

      // Carrega dados do Clone Postgres
      setCloneHost(data.clone_db_conn?.host || '')
      setClonePort(Number(data.clone_db_conn?.port) || 5432)
      setCloneUser(data.clone_db_conn?.user || '')
      setClonePassword(data.clone_db_conn?.password || '••••••••')
      setCloneDatabase(data.clone_db_conn?.database || '')
      
      // Carrega dados de sincronização
      setSyncEnabled(data.sync_config?.enabled || false)
      setSyncTimes(data.sync_config?.times || [])
      setLastSyncTime(data.sync_config?.last_sync || null)
      setLastSyncStatus(data.sync_config?.last_sync_status || null)
      setLastSyncMessage(data.sync_config?.last_sync_message || null)
      
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'Erro ao recuperar configurações.')
    } finally {
      setLoading(false)
    }
  }, [API_BASE, isAdmin, token])

  useEffect(() => {
    if (user && !isAdmin) {
      queueMicrotask(() => setLoading(false))
    } else if (token && isAdmin) {
      void Promise.resolve().then(fetchSettings)
    }
  }, [fetchSettings, isAdmin, token, user])

  // Limpa mensagens após 5 segundos
  useEffect(() => {
    if (globalSuccess) {
      const timer = setTimeout(() => setGlobalSuccess(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [globalSuccess])

  useEffect(() => {
    syncProgressRef.current = syncProgress
  }, [syncProgress])

  // Busca logs de auditoria do Tenant
  const fetchAuditLogs = useCallback(async () => {
    if (!token) return
    try {
      setLoadingAudit(true)
      const res = await fetch(`${API_BASE}/api/v1/tenant/audit-logs`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (res.ok) {
        const data = await res.json()
        setAuditLogs(data)
      }
    } catch (err) {
      console.error('Erro ao buscar logs de auditoria:', err)
    } finally {
      setLoadingAudit(false)
    }
  }, [API_BASE, token])

  // Carrega logs ao ativar a aba de auditoria
  useEffect(() => {
    if (activeTab === 'audit') {
      void Promise.resolve().then(fetchAuditLogs)
    }
  }, [activeTab, fetchAuditLogs, token])

  // Lógica local para adicionar modelo de IA no estado
  const handleAddRegisteredModel = () => {
    if (!newModelName.trim()) {
      alert('Por favor, informe o nome descritivo do modelo.')
      return
    }
    if (!newModelApiKey.trim()) {
      alert('Por favor, insira a chave de API.')
      return
    }
    const newModel: RegisteredAIModel = {
      id: `model-${Date.now()}`,
      name: newModelName.trim(),
      model_base: newModelBase,
      api_key: newModelApiKey.trim()
    }
    setRegisteredModels(prev => [...prev, newModel])
    
    // Ativa automaticamente se for o primeiro modelo cadastrado
    if (registeredModels.length === 0) {
      setActiveModelId(newModel.id)
    }
    setNewModelName('')
    setNewModelApiKey('')
  }

  const handleTestAiConnection = async (modelId: string, modelBase: string, apiKey: string) => {
    setTestingAiId(modelId)
    setAiTestResult(null)
    try {
      const res = await fetch(`${API_BASE}/api/v1/tenant/test-ai`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          id: modelId,
          model: modelBase,
          api_key: apiKey
        })
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error?.message ?? 'Erro na validação da chave de IA.')
      }
      setAiTestResult({
        id: modelId,
        success: true,
        message: data.message ?? 'IA conectada com sucesso!'
      })
    } catch (err) {
      setAiTestResult({
        id: modelId,
        success: false,
        message: err instanceof Error ? err.message : 'Falha na conexão com a OpenAI.'
      })
    } finally {
      setTestingAiId(null)
    }
  }

  const handleTestNewAiConnection = async () => {
    if (!newModelApiKey.trim()) {
      alert('Por favor, informe a chave de API para testar.')
      return
    }
    setTestingNewAi(true)
    setAiTestResult(null)
    try {
      const res = await fetch(`${API_BASE}/api/v1/tenant/test-ai`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          model: newModelBase,
          api_key: newModelApiKey.trim()
        })
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error?.message ?? 'Erro na validação da chave de IA.')
      }
      setAiTestResult({
        id: 'new-model',
        success: true,
        message: data.message ?? 'IA conectada com sucesso!'
      })
    } catch (err) {
      setAiTestResult({
        id: 'new-model',
        success: false,
        message: err instanceof Error ? err.message : 'Falha na conexão com a OpenAI.'
      })
    } finally {
      setTestingNewAi(false)
    }
  }

  // Lógica local para remover modelo de IA do estado
  const handleRemoveRegisteredModel = (id: string) => {
    setRegisteredModels(prev => prev.filter(m => m.id !== id))
    if (activeModelId === id) {
      setActiveModelId('')
    }
  }

  // Salva as configurações editadas no banco PostgreSQL
  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSaving(true)
      setGlobalError(null)
      setGlobalSuccess(null)

      const activeModel = registeredModels.find(m => m.id === activeModelId)

      const payload = {
        nome: tenantName.trim(),
        logo_url: logoUrl.trim() || null,
        tema_config: {
          primary_color: primaryColor,
          secondary_color: secondaryColor,
          border_radius: borderRadius
        },
        ia_config: {
          active_model_id: activeModelId,
          temperature: Number(iaTemperature),
          custom_instructions: iaInstructions.trim(),
          registered_models: registeredModels,
          // Fallback legado para compatibilidade do backend antigo
          model: activeModel ? activeModel.model_base : 'gpt-4o-mini',
          api_key: activeModel ? activeModel.api_key : ''
        },
        oracle_conn: {
          host: dbHost.trim(),
          port: Number(dbPort),
          user: dbUser.trim(),
          password: dbPassword,
          sid: dbSid.trim() || null,
          service_name: dbServiceName.trim() || null
        },
        clone_db_conn: {
          host: cloneHost.trim(),
          port: Number(clonePort),
          user: cloneUser.trim(),
          password: clonePassword,
          database: cloneDatabase.trim()
        },
        sync_config: {
          enabled: syncEnabled,
          times: syncTimes
        }
      }

      const res = await fetch(`${API_BASE}/api/v1/tenant/settings`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao salvar configurações.')
      }

      setGlobalSuccess('Todas as configurações do Tenant foram salvas com sucesso!')
      
      // Força a recarga para atualizar as máscaras corretas vindas do backend
      await fetchSettings()
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'Falha ao salvar as configurações.')
    } finally {
      setSaving(false)
    }
  }

  // Executa teste de conexão em tempo real contra o banco de dados Oracle do cliente
  const handleTestOracleConnection = async () => {
    setTestingConnection(true)
    setTestResult(null)
    setGlobalError(null)
    
    try {
      // Monta os parâmetros necessários para o Thin mode
      const connParams = {
        host: dbHost.trim(),
        port: Number(dbPort),
        user: dbUser.trim(),
        password: dbPassword,
        sid: dbSid.trim() || null,
        service_name: dbServiceName.trim() || null
      }

      const res = await fetch(`${API_BASE}/api/v1/tenant/test-oracle`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(connParams)
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error?.message ?? data.detail ?? 'Falha de comunicação ou parâmetros incorretos.')
      }

      setTestResult({
        success: true,
        message: data.message ?? 'Conectividade estabelecida com sucesso!'
      })
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof Error ? err.message : 'Não foi possível conectar ao banco Oracle.'
      })
    } finally {
      setTestingConnection(false)
    }
  }

  // Testar conexão Postgres Clone
  const handleTestPostgresCloneConnection = async () => {
    setTestingClone(true)
    setTestCloneResult(null)
    setGlobalError(null)
    try {
      const connParams = {
        host: cloneHost.trim(),
        port: Number(clonePort),
        user: cloneUser.trim(),
        password: clonePassword,
        database: cloneDatabase.trim()
      }
      const res = await fetch(`${API_BASE}/api/v1/tenant/test-postgres-clone`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(connParams)
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error?.message ?? 'Falha de comunicação ou parâmetros incorretos.')
      }
      setTestCloneResult({
        success: true,
        message: data.message ?? 'Conectividade estabelecida com sucesso!'
      })
    } catch (err) {
      setTestCloneResult({
        success: false,
        message: err instanceof Error ? err.message : 'Não foi possível conectar ao banco PostgreSQL clonado.'
      })
    } finally {
      setTestingClone(false)
    }
  }

  const refreshLastSyncStatus = useCallback(async () => {
    if (!token) return null
    const checkRes = await fetch(`${API_BASE}/api/v1/tenant/settings`, {
      credentials: 'include',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    if (!checkRes.ok) return null
    const checkData = await checkRes.json()
    setLastSyncTime(checkData.sync_config?.last_sync || null)
    setLastSyncStatus(checkData.sync_config?.last_sync_status || null)
    setLastSyncMessage(checkData.sync_config?.last_sync_message || null)
    return checkData.sync_config ?? null
  }, [API_BASE, token])

  const fetchSyncProgress = useCallback(async () => {
    if (!token) return null

    const fallbackProgress = (message: string): SyncProgressState => {
      const current = syncProgressRef.current
      const fallback: SyncProgressState = {
        active: true,
        status: 'running',
        phase: 'progress_unavailable',
        percent: Math.min(99, Math.max(0, Number(current?.percent ?? 0))),
        current_view: current?.current_view ?? null,
        current_view_index: current?.current_view_index ?? 0,
        total_views: current?.total_views ?? 0,
        current_view_rows: current?.current_view_rows ?? 0,
        current_view_estimated_rows: current?.current_view_estimated_rows ?? null,
        processed_views: current?.processed_views ?? 0,
        processed_rows: current?.processed_rows ?? 0,
        total_rows: current?.total_rows ?? 0,
        message,
        updated_at: new Date().toISOString(),
        started_at: current?.started_at ?? new Date().toISOString(),
        finished_at: null,
        error: null
      }
      syncProgressRef.current = fallback
      setSyncProgress(fallback)
      return fallback
    }

    try {
      const res = await fetch(`${API_BASE}/api/v1/tenant/sync-progress`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        const detail = data.error?.message ?? data.detail
        return fallbackProgress(
          detail || `Sincronizacao iniciada. Aguardando backend de progresso responder (${res.status}).`
        )
      }
      const data = await res.json() as SyncProgressState
      const safePercent = Number.isFinite(Number(data.percent))
        ? Math.min(100, Math.max(0, Number(data.percent)))
        : 0
      const normalized = { ...data, percent: safePercent }
      syncProgressRef.current = normalized
      setSyncProgress(normalized)
      return normalized
    } catch {
      return fallbackProgress('Sincronizacao iniciada. Aguardando backend de progresso responder.')
    }
  }, [API_BASE, token])

  useEffect(() => {
    if (!syncProgressPolling || !token) return

    let alive = true
    const startedAt = Date.now()

    const tick = async () => {
      try {
        const progress = await fetchSyncProgress()
        if (!alive || !progress) return

        const finished = progress.status === 'completed' || progress.status === 'failed'
        const timedOut = Date.now() - startedAt > 10 * 60 * 1000

        if (progress.phase === 'progress_unavailable') {
          const syncConfig = await refreshLastSyncStatus()
          const finalStatus = syncConfig?.last_sync_status
          if (finalStatus === 'success' || finalStatus === 'failed') {
            const finalProgress: SyncProgressState = {
              ...progress,
              active: false,
              status: finalStatus === 'success' ? 'completed' : 'failed',
              phase: finalStatus === 'success' ? 'completed' : 'failed',
              percent: finalStatus === 'success' ? 100 : progress.percent,
              message: syncConfig?.last_sync_message || (
                finalStatus === 'success'
                  ? 'Sincronizacao concluida com sucesso.'
                  : 'A sincronizacao falhou.'
              ),
              finished_at: syncConfig?.last_sync || new Date().toISOString(),
              error: finalStatus === 'failed' ? syncConfig?.last_sync_message || 'Falha na sincronizacao.' : null
            }
            syncProgressRef.current = finalProgress
            setSyncProgress(finalProgress)
            setSyncProgressPolling(false)
            setSyncingNow(false)
            setSyncNowResult({
              success: finalStatus === 'success',
              message: finalProgress.message || 'Sincronizacao finalizada.'
            })
          }
          if (timedOut) {
            setSyncProgressPolling(false)
            setSyncingNow(false)
            setSyncNowResult({
              success: true,
              message: 'A sincronizacao continua em segundo plano, mas o acompanhamento em tempo real expirou. Atualize o status em alguns instantes.'
            })
          }
          return
        }

        if (finished || timedOut) {
          setSyncProgressPolling(false)
          setSyncingNow(false)
          await refreshLastSyncStatus()
          setSyncNowResult({
            success: progress.status === 'completed',
            message: timedOut
              ? 'A sincronizacao continua em segundo plano, mas o acompanhamento em tempo real expirou. Atualize o status em alguns instantes.'
              : progress.message || (progress.status === 'completed'
                ? 'Sincronizacao concluida com sucesso.'
                : 'A sincronizacao falhou.')
          })
        }
      } catch {
        const syncConfig = await refreshLastSyncStatus()
        if (syncConfig?.last_sync_status === 'success' || syncConfig?.last_sync_status === 'failed') {
          setSyncProgressPolling(false)
          setSyncingNow(false)
        }
      }
    }

    void tick()
    const intervalId = window.setInterval(() => void tick(), 1200)
    return () => {
      alive = false
      window.clearInterval(intervalId)
    }
  }, [fetchSyncProgress, refreshLastSyncStatus, syncProgressPolling, token])

  // Sincronizar agora
  const handleSyncNow = async () => {
    setSyncingNow(true)
    setSyncNowResult(null)
    setGlobalError(null)
    setSyncProgress({
      active: true,
      status: 'running',
      phase: 'starting',
      percent: 0,
      current_view: null,
      current_view_index: 0,
      total_views: 0,
      current_view_rows: 0,
      current_view_estimated_rows: null,
      processed_views: 0,
      processed_rows: 0,
      total_rows: 0,
      message: 'Solicitando inicio da sincronizacao...',
      updated_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      finished_at: null,
      error: null
    })
    try {
      const res = await fetch(`${API_BASE}/api/v1/tenant/sync-now`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error?.message ?? 'Falha ao sincronizar o banco de dados.')
      }
      setSyncNowResult({
        success: true,
        message: data.message ?? 'Sincronização manual iniciada em segundo plano!'
      })
      setSyncProgressPolling(true)
    } catch (err) {
      setSyncNowResult({
        success: false,
        message: err instanceof Error ? err.message : 'Falha ao sincronizar.'
      })
      setSyncingNow(false)
      setSyncProgress(prev => prev ? {
        ...prev,
        active: false,
        status: 'failed',
        phase: 'failed',
        message: err instanceof Error ? err.message : 'Falha ao sincronizar.',
        error: err instanceof Error ? err.message : 'Falha ao sincronizar.',
        finished_at: new Date().toISOString()
      } : null)
    }
  }

  // Lógica de horários do scheduler
  const handleAddSyncTime = () => {
    if (!newSyncTime) return
    const regex = /^([01]\d|2[0-3]):([0-5]\d)$/
    if (!regex.test(newSyncTime)) {
      alert('Por favor, informe o horário no formato de 24 horas (HH:MM), ex: 03:00')
      return
    }
    if (syncTimes.includes(newSyncTime)) {
      alert('Este horário já está cadastrado.')
      return
    }
    setSyncTimes(prev => [...prev, newSyncTime].sort())
    setNewSyncTime('')
  }

  const handleRemoveSyncTime = (time: string) => {
    setSyncTimes(prev => prev.filter(t => t !== time))
  }

  // ── Proteção RBAC / Acesso Negado ──────────────────────────────
  if (!loading && user?.role !== 'ADMIN') {
    return (
      <div className="flex h-dvh w-screen items-center justify-center p-6" style={{ background: 'rgb(var(--bg-base))' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md w-full text-center"
        >
          <GlassCard padding="lg" className="flex flex-col items-center gap-6 border-red-500/25">
            <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center text-red-500">
              <ShieldAlert size={36} />
            </div>
            <div>
              <h2 className="text-xl font-bold mb-2" style={{ color: 'rgb(var(--text-primary))' }}>
                Acesso Restrito
              </h2>
              <p className="text-sm leading-relaxed" style={{ color: 'rgb(var(--text-secondary))' }}>
                Desculpe, as configurações gerais de infraestrutura SaaS e banco de dados são restritas a administradores.
              </p>
            </div>
            <Link href="/dashboard" className="w-full">
              <button
                className="w-full flex items-center justify-center gap-2 text-xs font-semibold py-3 px-4 rounded-xl transition-all interactive hover:bg-zinc-800"
                style={{
                  background: 'rgb(var(--bg-elevated))',
                  border: '1px solid rgb(var(--border) / 0.6)',
                  color: 'rgb(var(--text-secondary))',
                }}
              >
                <ArrowLeft size={14} />
                <span>Voltar ao Dashboard</span>
              </button>
            </Link>
          </GlassCard>
        </motion.div>
      </div>
    )
  }

  // Lista de Abas para Renderização
  const tabList = [
    { id: 'visual', label: 'Tema & Marca', icon: Palette },
    { id: 'ia', label: 'Configurações de IA', icon: Bot },
    { id: 'db', label: 'Banco Original', icon: Database },
    { id: 'sync', label: 'Sincronização & Clone', icon: RefreshCw },
    { id: 'audit', label: 'Auditoria de Logs', icon: History }
  ] as const
  const visibleSyncProgress = Boolean(syncProgress && (
    syncingNow ||
    syncProgress.active ||
    syncProgress.status === 'completed' ||
    syncProgress.status === 'failed'
  ))
  const syncPercent = Math.min(100, Math.max(0, Number(syncProgress?.percent ?? 0)))
  const formatSyncCount = (value?: number | null) => Number(value ?? 0).toLocaleString('pt-BR')
  const syncProgressTone = syncProgress?.status === 'failed'
    ? 'red'
    : syncProgress?.status === 'completed'
      ? 'emerald'
      : 'lumina'

  return (
    <div className="flex h-dvh overflow-hidden" style={{ background: 'rgb(var(--bg-base))' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0 dashboard-main-content">
        
        {/* Top Header */}
        <header
          className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 px-8 py-6 flex-shrink-0"
          style={{ borderBottom: '1px solid rgb(var(--border) / 0.5)' }}
        >
          <div>
            <h1 className="text-xl font-bold text-gradient">
              Configurações do SaaS
            </h1>
            <p className="text-xs mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
              Gerencie a identidade visual, parametrize os modelos LLM e configure as chaves criptografadas de banco.
            </p>
          </div>
        </header>

        {/* Corpo Principal da Tela */}
        <main className="flex-1 overflow-y-auto px-8 py-6 space-y-6 max-w-4xl w-full">
          
          {/* Sucesso Global */}
          {globalSuccess && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 flex items-start gap-3"
            >
              <CheckCircle2 className="text-emerald-400 mt-0.5 flex-shrink-0" size={16} />
              <div>
                <p className="text-xs font-semibold text-emerald-400">Sucesso!</p>
                <p className="text-xs leading-normal mt-0.5" style={{ color: 'rgb(var(--text-secondary))' }}>
                  {globalSuccess}
                </p>
              </div>
            </motion.div>
          )}

          {/* Erro Global */}
          {globalError && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-xl border border-red-500/20 bg-red-500/10 flex items-start gap-3"
            >
              <XCircle className="text-red-400 mt-0.5 flex-shrink-0" size={16} />
              <div>
                <p className="text-xs font-semibold text-red-400">Falha ao atualizar parâmetros</p>
                <p className="text-xs leading-normal mt-0.5" style={{ color: 'rgb(var(--text-secondary))' }}>
                  {globalError}
                </p>
              </div>
            </motion.div>
          )}

          {loading ? (
            <div className="flex items-center justify-center h-64 gap-3">
              <Loader2 className="text-lumina-400 animate-spin" size={24} />
              <span className="text-xs" style={{ color: 'rgb(var(--text-muted))' }}>Carregando dados da empresa...</span>
            </div>
          ) : (
            <form onSubmit={handleSaveSettings} className="space-y-6">
              
              {/* Barra de Abas Estilo Bento */}
              <div className="flex p-1 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-250 dark:border-zinc-800/80 max-w-xl">
                {tabList.map(tab => {
                  const Icon = tab.icon
                  const isActive = activeTab === tab.id
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setActiveTab(tab.id)}
                      className={cn(
                        'flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-bold transition-all relative select-none cursor-pointer',
                        isActive ? 'text-zinc-900 dark:text-white' : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-250'
                      )}
                    >
                      {isActive && (
                        <motion.div
                          layoutId="active-settings-tab"
                          className="absolute inset-0 rounded-lg bg-white dark:bg-zinc-800 shadow-sm dark:shadow-md"
                          style={{ zIndex: 0 }}
                          transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                        />
                      )}
                      <Icon size={13} className="relative z-10" />
                      <span className="relative z-10 hidden sm:inline">{tab.label}</span>
                    </button>
                  )
                })}
              </div>

              {/* Área do Conteúdo da Aba Ativa */}
              <div className="min-h-[400px]">
                
                {/* â”€â”€ TAB: VISUAL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
                {activeTab === 'visual' && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="space-y-6"
                  >
                    <GlassCard className="border-zinc-300 dark:border-zinc-800/50 space-y-5">
                      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-3">
                        <h3 className="text-sm font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                          <Palette size={15} className="text-lumina-400" />
                          Customização da Marca
                        </h3>
                        <p className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                          Personalize como a sua empresa visualiza a plataforma LuminaAI.
                        </p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Nome da Empresa */}
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Nome da Organização
                            <TooltipHelp content="O nome oficial da sua empresa, exibido no cabeçalho e nos e-mails de notificação." />
                          </label>
                          <input
                            type="text"
                            required
                            value={tenantName}
                            onChange={e => setTenantName(e.target.value)}
                            placeholder="Ex: Acme Corporation Ltda"
                            className="py-2.5 px-3.5 text-xs lumina-input"
                          />
                        </div>

                        {/* URL da Logo */}
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            URL do Logotipo (PNG/SVG)
                            <TooltipHelp content="Endereço web do logotipo da empresa. Deve ser um link direto para uma imagem PNG, JPG ou SVG para customizar o canto superior esquerdo do painel." />
                          </label>
                          <input
                            type="url"
                            value={logoUrl}
                            onChange={e => setLogoUrl(e.target.value)}
                            placeholder="Ex: https://cdn.empresa.com/logo.svg"
                            className="py-2.5 px-3.5 text-xs lumina-input"
                          />
                        </div>

                        {/* Cor Primária */}
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Cor Principal Accent (Hex)
                            <TooltipHelp content="A cor primária da marca (em formato hexadecimal, ex: #6C63FF). Será usada em botões principais, gradientes, seleções ativas e detalhes visuais importantes." />
                          </label>
                          <div className="flex gap-2">
                            <input
                              type="color"
                              value={primaryColor}
                              onChange={e => setPrimaryColor(e.target.value)}
                              className="w-10 h-10 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 p-1 cursor-pointer"
                            />
                            <input
                              type="text"
                              required
                              value={primaryColor}
                              onChange={e => setPrimaryColor(e.target.value)}
                              className="flex-1 py-2 px-3 text-xs lumina-input font-mono uppercase"
                            />
                          </div>
                        </div>

                        {/* Cor Secundária */}
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Cor de Destaque Secundária (Hex)
                            <TooltipHelp content="A cor secundária ou de destaque (ex: #00D2D3). Será usada em badges de status secundários, linhas de tendência e elementos gráficos de suporte." />
                          </label>
                          <div className="flex gap-2">
                            <input
                              type="color"
                              value={secondaryColor}
                              onChange={e => setSecondaryColor(e.target.value)}
                              className="w-10 h-10 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 p-1 cursor-pointer"
                            />
                            <input
                              type="text"
                              required
                              value={secondaryColor}
                              onChange={e => setSecondaryColor(e.target.value)}
                              className="flex-1 py-2 px-3 text-xs lumina-input font-mono uppercase"
                            />
                          </div>
                        </div>

                        {/* Border Radius */}
                        <div className="flex flex-col gap-1.5 md:col-span-2">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Arredondamento de Bordas (Border Radius)
                            <TooltipHelp content="Define a curvatura dos cantos de botões, caixas de entrada de texto e cards. O modo moderno de 14px é o padrão recomendado do LuminaAI." />
                          </label>
                          <select
                            value={borderRadius}
                            onChange={e => setBorderRadius(e.target.value)}
                            className="py-2.5 px-3.5 text-xs lumina-input"
                          >
                            <option value="6px">Reto / Corporativo (6px)</option>
                            <option value="10px">Suave (10px)</option>
                            <option value="14px">Moderno (14px - Padrão Lumina)</option>
                            <option value="20px">Orgânico / Arredondado (20px)</option>
                          </select>
                        </div>

                      </div>
                    </GlassCard>
                  </motion.div>
                )}

                {/* â”€â”€ TAB: IA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
                {activeTab === 'ia' && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="space-y-6"
                  >
                    <GlassCard className="border-zinc-300 dark:border-zinc-800/50 space-y-5">
                      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-3">
                        <h3 className="text-sm font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                          <Bot size={15} className="text-lumina-400" />
                          Configurações Globais de IA
                        </h3>
                        <p className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                          Configure e ative seus modelos de inteligência artificial de forma personalizada.
                        </p>
                      </div>

                      <div className="space-y-4">
                        {/* Modelo de IA Ativo e Temperatura */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                              Modelo de IA Ativo
                              <TooltipHelp content="Selecione qual das chaves e modelos de IA cadastrados abaixo será usado para traduzir as perguntas em parâmetros de views. Só aparecerá após você cadastrar uma IA com chave na seção abaixo." />
                            </label>
                            <select
                              value={activeModelId}
                              disabled={registeredModels.length === 0}
                              onChange={e => setActiveModelId(e.target.value)}
                              className="py-2.5 px-3.5 text-xs lumina-input disabled:opacity-50"
                            >
                              {registeredModels.length === 0 ? (
                                <option value="">Nenhum modelo cadastrado. Cadastre um abaixo primeiro.</option>
                              ) : (
                                <>
                                  <option value="">Selecione um modelo ativo...</option>
                                  {registeredModels.map(m => (
                                    <option key={m.id} value={m.id}>
                                      {m.name} ({m.model_base})
                                    </option>
                                  ))}
                                </>
                              )}
                            </select>
                          </div>

                          <div className="flex flex-col gap-1.5">
                            <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                              Temperatura (Criatividade): {iaTemperature}
                              <TooltipHelp content="Controla a aleatoriedade das respostas. Valores baixos (ex: 0.0) geram respostas consistentes e exatas para queries. Valores altos dão maior variação." />
                            </label>
                            <input
                              type="range"
                              min="0"
                              max="1.0"
                              step="0.1"
                              value={iaTemperature}
                              onChange={e => setIaTemperature(Number(e.target.value))}
                              className="w-full h-1.5 bg-zinc-200 dark:bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-violet-500 mt-3"
                            />
                            <div className="flex justify-between text-[9px] text-zinc-600 font-bold leading-none">
                              <span>ESTRITO (0.0)</span>
                              <span>CRIATIVO (1.0)</span>
                            </div>
                          </div>
                        </div>

                        {/* Custom Instructions */}
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Diretrizes de Prompt (Custom Instructions)
                            <TooltipHelp content="Instruções de comportamento fornecidas à inteligência artificial em todas as consultas. Ex: 'Seja sempre formal nas análises financeiras. Traduza badges de status para português...'" />
                          </label>
                          <textarea
                            rows={4}
                            value={iaInstructions}
                            onChange={e => setIaInstructions(e.target.value)}
                            placeholder="Instruções personalizadas repassadas para o sistema de linguagem. Ex: 'Seja sempre formal nas análises financeiras. Traduza badges de status para português...'"
                            className="py-2.5 px-3.5 text-xs lumina-input leading-relaxed resize-none"
                          />
                        </div>
                      </div>
                    </GlassCard>

                    {/* Novo Bloco: Registro de IAs */}
                    <GlassCard className="border-zinc-200 dark:border-zinc-800/50 space-y-5">
                      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-3">
                        <h3 className="text-sm font-bold text-zinc-800 dark:text-white flex items-center gap-2">
                          <Key size={15} className="text-lumina-400" />
                          Cadastro de Modelos de IA & API Keys
                        </h3>
                        <p className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                          Configure chaves de API OpenAI dedicadas e o identificador de IA para o sistema.
                        </p>
                      </div>

                      {/* Lista de Modelos Cadastrados */}
                      <div className="space-y-3">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
                          Modelos Cadastrados ({registeredModels.length})
                        </span>
                        {registeredModels.length === 0 ? (
                          <div className="p-4 rounded-xl border border-dashed border-zinc-300 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950/40 text-center">
                            <p className="text-xs text-zinc-500">Nenhum provedor de IA cadastrado para esta organização. Use o formulário abaixo para registrar.</p>
                          </div>
                        ) : (
                          <div className="overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800/60 bg-zinc-50 dark:bg-zinc-900/30">
                            <table className="w-full text-left border-collapse text-xs">
                              <thead>
                                <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-950/40 text-zinc-600 dark:text-zinc-400 font-semibold">
                                  <th className="p-3">Nome do Modelo</th>
                                  <th className="p-3">Modelo Base</th>
                                  <th className="p-3">Chave de API</th>
                                  <th className="p-3 text-right">Ação</th>
                                </tr>
                              </thead>
                              <tbody>
                                {registeredModels.map(m => (
                                  <tr key={m.id} className="border-b border-zinc-200 dark:border-zinc-800/40 hover:bg-zinc-100 dark:hover:bg-zinc-800/20 text-zinc-700 dark:text-zinc-300">
                                    <td className="p-3 font-semibold">{m.name}</td>
                                    <td className="p-3 font-mono text-zinc-650 dark:text-zinc-400">{m.model_base}</td>
                                    <td className="p-3 font-mono text-zinc-650 dark:text-zinc-400 select-all">{m.api_key}</td>
                                    <td className="p-3 text-right">
                                      <button
                                        type="button"
                                        disabled={testingAiId !== null}
                                        onClick={() => handleTestAiConnection(m.id, m.model_base, m.api_key)}
                                        className="text-zinc-500 hover:text-emerald-500 dark:hover:text-emerald-400 p-1.5 rounded transition-colors mr-1 cursor-pointer disabled:opacity-50 bg-transparent border-0"
                                        title="Testar conexão"
                                      >
                                        {testingAiId === m.id ? (
                                          <Loader2 size={13} className="animate-spin text-emerald-500 dark:text-emerald-400" />
                                        ) : (
                                          <Play size={13} />
                                        )}
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => handleRemoveRegisteredModel(m.id)}
                                        className="text-zinc-500 hover:text-red-500 dark:hover:text-red-400 p-1.5 rounded transition-colors cursor-pointer bg-transparent border-0"
                                        title="Remover modelo"
                                      >
                                        <Trash2 size={13} />
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>

                      {/* Form de Cadastro */}
                      <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/20 space-y-4">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                          Registrar Nova Conexão de IA
                        </span>
                        
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-bold text-zinc-500 flex items-center">
                              Nome Personalizado
                              <TooltipHelp content="Um apelido legível para você saber qual API/Ambiente é este (Ex: 'OpenAI Finanças')." />
                            </label>
                            <input
                              type="text"
                              value={newModelName}
                              onChange={e => setNewModelName(e.target.value)}
                              placeholder="Ex: OpenAI Produção"
                              className="py-2 px-3 text-xs lumina-input"
                            />
                          </div>

                          <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-bold text-zinc-500 flex items-center">
                              Modelo Base
                              <TooltipHelp content="O modelo oficial da OpenAI a ser utilizado para as tarefas de processamento de linguagem natural." />
                            </label>
                            <select
                              value={newModelBase}
                              onChange={e => setNewModelBase(e.target.value)}
                              className="py-2 px-3 text-xs lumina-input"
                            >
                              <option value="gpt-4o-mini">gpt-4o-mini (Recomendado)</option>
                            </select>
                          </div>

                          <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-bold text-zinc-500 flex items-center">
                              Chave de API OpenAI
                              <TooltipHelp content="Insira a API Key (sk-...) gerada na sua conta de desenvolvedor OpenAI." />
                            </label>
                            <input
                              type="password"
                              value={newModelApiKey}
                              onChange={e => setNewModelApiKey(e.target.value)}
                              placeholder="sk-..."
                              className="py-2 px-3 text-xs lumina-input font-mono"
                            />
                          </div>
                        </div>

                        <div className="flex justify-between items-center pt-1 w-full">
                          <div>
                            {aiTestResult && (aiTestResult.id === 'new-model' || registeredModels.some(m => m.id === aiTestResult.id)) && (
                              <span className={cn("text-[10px] font-semibold leading-none", aiTestResult.success ? "text-emerald-500 dark:text-emerald-400" : "text-red-500 dark:text-red-400")}>
                                {aiTestResult.message}
                              </span>
                            )}
                          </div>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              disabled={testingNewAi}
                              onClick={handleTestNewAiConnection}
                              className="flex items-center gap-1.5 text-xs font-bold py-2 px-4 rounded-xl border border-zinc-300 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-800 dark:hover:text-zinc-200 transition-all cursor-pointer disabled:opacity-50"
                            >
                              {testingNewAi ? (
                                <Loader2 size={12} className="animate-spin" />
                              ) : (
                                <Play size={12} />
                              )}
                              <span>Testar Conexão</span>
                            </button>
                            <button
                              type="button"
                              onClick={handleAddRegisteredModel}
                              className="flex items-center gap-1.5 text-xs font-bold py-2 px-4 rounded-xl border border-zinc-300 dark:border-zinc-700 bg-zinc-100 dark:bg-zinc-800 text-lumina-500 dark:text-lumina-400 hover:bg-zinc-200 dark:hover:bg-zinc-750 transition-all cursor-pointer"
                            >
                              <Plus size={12} />
                              <span>Adicionar IA</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    </GlassCard>
                  </motion.div>
                )}

                {/* â”€â”€ TAB: DATABASE (ORACLE) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
                {activeTab === 'db' && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="space-y-6"
                  >
                    <GlassCard className="border-zinc-200 dark:border-zinc-800/50 space-y-5">
                      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-3">
                        <h3 className="text-sm font-bold text-zinc-800 dark:text-white flex items-center gap-2">
                          <Database size={15} className="text-lumina-400" />
                          Conexão com Banco Oracle (Thin Mode)
                        </h3>
                        <p className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                          Configure a string de conexão física de produção onde as views mapeadas estão localizadas.
                        </p>
                      </div>

                      {/* Parâmetros Host e Porta */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="md:col-span-2 flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Host (Endereço IP ou Domínio)
                            <TooltipHelp content="O IP físico ou nome de domínio DNS para alcançar o servidor do banco de dados Oracle da sua corporação." />
                          </label>
                          <input
                            type="text"
                            required
                            value={dbHost}
                            onChange={e => setDbHost(e.target.value)}
                            placeholder="oracle.suaempresa.com.br"
                            className="py-2.5 px-3.5 text-xs lumina-input font-mono"
                          />
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Porta Oracle
                            <TooltipHelp content="A porta de escuta do Oracle Listener (geralmente a porta padrão 1521)." />
                          </label>
                          <input
                            type="number"
                            required
                            value={dbPort}
                            onChange={e => setDbPort(Number(e.target.value))}
                            placeholder="1521"
                            className="py-2.5 px-3.5 text-xs lumina-input font-mono"
                          />
                        </div>
                      </div>

                      {/* Usuário e Senha */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Usuário do Banco (User)
                            <TooltipHelp content="O nome do usuário/schema de banco de dados configurado para leitura das views (ex: LUMINA_READER)." />
                          </label>
                          <input
                            type="text"
                            required
                            value={dbUser}
                            onChange={e => setDbUser(e.target.value)}
                            placeholder="LUMINA_READER"
                            className="py-2.5 px-3.5 text-xs lumina-input uppercase font-mono"
                          />
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Senha (Password)
                            <TooltipHelp content="Senha de acesso do usuário do banco Oracle. Salva de forma criptografada por chaves simétricas seguras." />
                          </label>
                          <input
                            type="password"
                            required
                            value={dbPassword}
                            onChange={e => setDbPassword(e.target.value)}
                            placeholder="SuaSenhaSegura"
                            className="py-2.5 px-3.5 text-xs lumina-input font-mono"
                          />
                        </div>
                      </div>

                      {/* Identificadores SID e Service Name */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Oracle System ID (SID) — Opcional
                            <TooltipHelp content="Identificador exclusivo da instância do banco de dados Oracle (ex: XE, ORCL). Informe se não estiver usando Service Name." />
                          </label>
                          <input
                            type="text"
                            value={dbSid}
                            onChange={e => setDbSid(e.target.value.toUpperCase())}
                            placeholder="XE"
                            className="py-2.5 px-3.5 text-xs lumina-input font-mono uppercase"
                          />
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Service Name (Alternativa ao SID) — Opcional
                            <TooltipHelp content="O nome de serviço do banco Oracle registrado no Listener. Recomendado para ambientes RAC ou nuvem." />
                          </label>
                          <input
                            type="text"
                            value={dbServiceName}
                            onChange={e => setDbServiceName(e.target.value.toLowerCase())}
                            placeholder="orcl.suaempresa.com"
                            className="py-2.5 px-3.5 text-xs lumina-input font-mono"
                          />
                        </div>
                      </div>

                      {/* Area do Testador de Conexão */}
                      <div className="border-t border-zinc-200 dark:border-zinc-850 pt-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="min-w-0 max-w-md">
                          <p className="text-xs font-bold text-zinc-800 dark:text-white">Validação Real-Time</p>
                          <p className="text-[10px] text-zinc-550 dark:text-zinc-400 mt-0.5 leading-relaxed">
                            Antes de salvar as credenciais no Postgres, rode um teste em modo Thin para assegurar que o host/porta e usuários estão configurados corretamente.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={handleTestOracleConnection}
                          disabled={testingConnection || !dbHost || !dbUser}
                          className="flex items-center justify-center gap-2 text-xs font-bold px-4 py-2.5 rounded-xl border border-zinc-300 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-lumina-500 dark:text-lumina-400 transition-all select-none disabled:opacity-50 interactive"
                        >
                          {testingConnection ? (
                            <Loader2 className="animate-spin" size={14} />
                          ) : (
                            <Play size={12} className="fill-lumina-400/20" />
                          )}
                          <span>Testar Conexão</span>
                        </button>
                      </div>

                      {/* Notificação do Resultado do Teste */}
                      {testResult && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.98 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className={cn(
                            'p-3.5 rounded-xl border flex items-start gap-2.5',
                            testResult.success 
                              ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-500 dark:text-emerald-400'
                              : 'border-red-500/20 bg-red-500/5 text-red-500 dark:text-red-400'
                          )}
                        >
                          {testResult.success ? (
                            <CheckCircle2 size={16} className="mt-0.5 flex-shrink-0" />
                          ) : (
                            <XCircle size={16} className="mt-0.5 flex-shrink-0" />
                          )}
                          <span className="text-[11px] leading-relaxed">{testResult.message}</span>
                        </motion.div>
                      )}

                    </GlassCard>
                  </motion.div>
                )}

                {/* â”€â”€ TAB: SYNC & CLONE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
                {activeTab === 'sync' && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="space-y-6"
                  >
                    {/* Credenciais do PostgreSQL do Clone */}
                    <GlassCard className="border-zinc-250 dark:border-zinc-800/50 space-y-5">
                      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-3">
                        <h3 className="text-sm font-bold text-zinc-800 dark:text-white flex items-center gap-2">
                          <Database size={15} className="text-lumina-400" />
                          Banco de Dados Clonado (PostgreSQL)
                        </h3>
                        <p className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                          Configure a conexão do banco de dados PostgreSQL local que hospedará os clones/cópias das tabelas do Oracle.
                        </p>
                      </div>

                      {/* Host e Porta */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="md:col-span-2 flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Host do Postgres Clone
                            <TooltipHelp content="Endereço de rede local (geralmente localhost ou 127.0.0.1 se estiver no mesmo servidor)." />
                          </label>
                          <input
                            type="text"
                            value={cloneHost}
                            onChange={e => setCloneHost(e.target.value)}
                            placeholder="127.0.0.1"
                            className="py-2.5 px-3.5 text-xs lumina-input font-mono"
                          />
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Porta Postgres
                            <TooltipHelp content="Porta de escuta do PostgreSQL (geralmente a padrão 5432)." />
                          </label>
                          <input
                            type="number"
                            value={clonePort}
                            onChange={e => setClonePort(Number(e.target.value))}
                            placeholder="5432"
                            className="py-2.5 px-3.5 text-xs lumina-input font-mono"
                          />
                        </div>
                      </div>

                      {/* Usuário, Senha e Banco de Dados */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Usuário (User)
                          </label>
                          <input
                            type="text"
                            value={cloneUser}
                            onChange={e => setCloneUser(e.target.value)}
                            placeholder="postgres"
                            className="py-2.5 px-3.5 text-xs lumina-input font-mono"
                          />
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Senha (Password)
                          </label>
                          <input
                            type="password"
                            value={clonePassword}
                            onChange={e => setClonePassword(e.target.value)}
                            placeholder="••••••••"
                            className="py-2.5 px-3.5 text-xs lumina-input font-mono"
                          />
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Banco de Dados (Database)
                            <TooltipHelp content="Nome do banco de dados que conterá as cópias das tabelas (ex: luminaai_clone)." />
                          </label>
                          <input
                            type="text"
                            value={cloneDatabase}
                            onChange={e => setCloneDatabase(e.target.value)}
                            placeholder="luminaai_clone"
                            className="py-2.5 px-3.5 text-xs lumina-input font-mono"
                          />
                        </div>
                      </div>

                      {/* Validador Real-Time Clone */}
                      <div className="border-t border-zinc-200 dark:border-zinc-855 pt-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="min-w-0 max-w-md">
                          <p className="text-xs font-bold text-zinc-800 dark:text-white">Validar Conexão do Clone</p>
                          <p className="text-[10px] text-zinc-550 dark:text-zinc-400 mt-0.5 leading-relaxed">
                            Teste a conexão com o banco do clone local antes de aplicar a configuração.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={handleTestPostgresCloneConnection}
                          disabled={testingClone || !cloneHost || !cloneUser || !cloneDatabase}
                          className="flex items-center justify-center gap-2 text-xs font-bold px-4 py-2.5 rounded-xl border border-zinc-300 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-lumina-500 dark:text-lumina-400 transition-all select-none disabled:opacity-50 interactive cursor-pointer"
                        >
                          {testingClone ? (
                            <Loader2 className="animate-spin" size={14} />
                          ) : (
                            <Play size={12} className="fill-lumina-400/20" />
                          )}
                          <span>Testar Conexão Clone</span>
                        </button>
                      </div>

                      {testCloneResult && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.98 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className={cn(
                            'p-3.5 rounded-xl border flex items-start gap-2.5',
                            testCloneResult.success 
                              ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-500 dark:text-emerald-400'
                              : 'border-red-500/20 bg-red-500/5 text-red-500 dark:text-red-400'
                          )}
                        >
                          {testCloneResult.success ? (
                            <CheckCircle2 size={16} className="mt-0.5 flex-shrink-0" />
                          ) : (
                            <XCircle size={16} className="mt-0.5 flex-shrink-0" />
                          )}
                          <span className="text-[11px] leading-relaxed">{testCloneResult.message}</span>
                        </motion.div>
                      )}
                    </GlassCard>

                    {/* Agendador de Sincronização */}
                    <GlassCard className="border-zinc-250 dark:border-zinc-800/50 space-y-5">
                      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-3">
                        <h3 className="text-sm font-bold text-zinc-800 dark:text-white flex items-center gap-2">
                          <RefreshCw size={15} className="text-lumina-400" />
                          Agendador de Sincronização Automática
                        </h3>
                        <p className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                          Defina as regras e horários que o robô do sistema utilizará para copiar os dados do Oracle original para a base PostgreSQL local.
                        </p>
                      </div>

                      {/* Habilitar / Desabilitar Switch */}
                      <div className="flex items-center justify-between p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-850">
                        <div className="max-w-md min-w-0">
                          <p className="text-xs font-bold text-zinc-800 dark:text-white">Status da Sincronização Automática</p>
                          <p className="text-[10px] text-zinc-550 dark:text-zinc-400 mt-0.5 leading-relaxed">
                            Se ativado, o robô irá sincronizar no horário configurado. Caso contrário, a base clone só será atualizada ao acionar o botão de sincronização manual.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setSyncEnabled(prev => !prev)}
                          className={cn(
                            "w-12 h-6 rounded-full p-1 transition-colors duration-250 cursor-pointer flex-shrink-0 relative",
                            syncEnabled ? "bg-lumina-500" : "bg-zinc-300 dark:bg-zinc-700"
                          )}
                        >
                          <motion.div
                            layout
                            className="w-4 h-4 rounded-full bg-white shadow-sm"
                            animate={{ x: syncEnabled ? 24 : 0 }}
                            transition={{ type: "spring", stiffness: 500, damping: 30 }}
                          />
                        </button>
                      </div>

                      {/* Horários cadastrados */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-3">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Definir Novo Horário de Execução
                          </label>
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={newSyncTime}
                              onChange={e => setNewSyncTime(e.target.value)}
                              placeholder="ex: 03:00 ou 12:00"
                              className="py-2 px-3 text-xs lumina-input font-mono flex-1"
                            />
                            <button
                              type="button"
                              onClick={handleAddSyncTime}
                              className="flex items-center gap-1 text-xs font-bold py-2 px-4 rounded-xl bg-zinc-100 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-200 dark:hover:bg-zinc-750 transition-all cursor-pointer"
                            >
                              <Plus size={12} />
                              <span>Adicionar</span>
                            </button>
                          </div>
                          <p className="text-[9px] text-zinc-500 leading-normal">
                            * Use o formato de 24 horas (HH:MM). Exemplo: 03:00, 12:00, 15:30. Você pode adicionar quantos horários quiser.
                          </p>
                        </div>

                        <div className="space-y-3">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 flex items-center">
                            Horários Configurados ({syncTimes.length})
                          </label>
                          {syncTimes.length === 0 ? (
                            <div className="p-4 rounded-xl border border-dashed border-zinc-250 dark:border-zinc-800 text-center">
                              <p className="text-[10px] text-zinc-500">Nenhum horário cadastrado. A sincronização automática não executará.</p>
                            </div>
                          ) : (
                            <div className="flex flex-wrap gap-2 max-h-[120px] overflow-y-auto thin-scroll p-1">
                              {syncTimes.map(time => (
                                <div
                                  key={time}
                                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-250 dark:border-zinc-800 text-xs font-bold text-zinc-750 dark:text-zinc-300"
                                >
                                  <span className="font-mono">{time}</span>
                                  <button
                                    type="button"
                                    onClick={() => handleRemoveSyncTime(time)}
                                    className="text-red-400 hover:text-red-500 transition-colors cursor-pointer"
                                  >
                                    <Trash2 size={11} />
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Logs e Estatísticas de Sincronização */}
                      <div className="border-t border-zinc-200 dark:border-zinc-850 pt-4 space-y-4">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-bold text-zinc-800 dark:text-white">Última Sincronização</p>
                            <div className="flex items-center gap-2 mt-1 flex-wrap">
                              {lastSyncStatus ? (
                                <span className={cn(
                                  "text-[10px] font-semibold px-2 py-0.5 rounded-full border",
                                  lastSyncStatus === 'success'
                                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500"
                                    : "bg-red-500/10 border-red-500/20 text-red-500"
                                )}>
                                  {lastSyncStatus === 'success' ? 'Sucesso' : 'Falhou'}
                                </span>
                              ) : (
                                <span className="text-[10px] text-zinc-500 italic">Nunca sincronizado</span>
                              )}
                              {lastSyncTime && (
                                <span className="text-[10px] text-zinc-550">
                                  Executado em: {new Date(lastSyncTime).toLocaleString('pt-BR')}
                                </span>
                              )}
                            </div>
                            {lastSyncMessage && (
                              <p className="text-[10px] text-zinc-650 dark:text-zinc-400 mt-1.5 leading-normal bg-zinc-50 dark:bg-zinc-900/40 p-2.5 rounded-lg border border-zinc-200 dark:border-zinc-850 font-mono">
                                {lastSyncMessage}
                              </p>
                            )}
                          </div>

                          <button
                            type="button"
                            onClick={handleSyncNow}
                            disabled={syncingNow || !cloneHost || !cloneUser || !cloneDatabase}
                            className="flex items-center justify-center gap-2 text-xs font-bold px-4 py-2.5 rounded-xl border border-zinc-300 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-lumina-500 dark:text-lumina-400 transition-all select-none disabled:opacity-50 interactive cursor-pointer flex-shrink-0"
                          >
                            {syncingNow ? (
                              <Loader2 className="animate-spin" size={14} />
                            ) : (
                              <RefreshCw size={12} />
                            )}
                            <span>Sincronizar Agora</span>
                          </button>
                        </div>

                        {visibleSyncProgress && syncProgress && (
                          <motion.div
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={cn(
                              'rounded-2xl border p-4 space-y-3 bg-white dark:bg-zinc-950/60',
                              syncProgressTone === 'red'
                                ? 'border-red-500/25'
                                : syncProgressTone === 'emerald'
                                  ? 'border-emerald-500/25'
                                  : 'border-lumina-500/25'
                            )}
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                              <div>
                                <p className="text-xs font-bold text-zinc-950 dark:text-white">
                                  Progresso da sincronizacao
                                </p>
                                <p className="text-[10px] text-zinc-700 dark:text-zinc-300 mt-0.5">
                                  {syncProgress.message || 'Acompanhando atualizacao do banco analitico.'}
                                </p>
                              </div>
                              <div className={cn(
                                'text-xs font-black tabular-nums',
                                syncProgressTone === 'red'
                                  ? 'text-red-500'
                                  : syncProgressTone === 'emerald'
                                    ? 'text-emerald-500'
                                    : 'text-lumina-500 dark:text-lumina-300'
                              )}>
                                {syncPercent.toFixed(syncPercent % 1 === 0 ? 0 : 1)}%
                              </div>
                            </div>

                            <div
                              className="h-2.5 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
                              role="progressbar"
                              aria-valuemin={0}
                              aria-valuemax={100}
                              aria-valuenow={syncPercent}
                            >
                              <div
                                className={cn(
                                  'h-full rounded-full transition-all duration-500',
                                  syncProgressTone === 'red'
                                    ? 'bg-red-500'
                                    : syncProgressTone === 'emerald'
                                      ? 'bg-emerald-500'
                                      : 'bg-gradient-to-r from-lumina-500 to-cyan-400'
                                )}
                                style={{ width: `${syncPercent}%` }}
                              />
                            </div>

                            <div className="grid gap-2 sm:grid-cols-3 text-[10px] text-zinc-700 dark:text-zinc-300">
                              <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 px-3 py-2">
                                <span className="block uppercase tracking-wider text-zinc-600 dark:text-zinc-400">View atual</span>
                                <strong className="block mt-1 text-zinc-950 dark:text-zinc-100 break-all">
                                  {syncProgress.current_view || 'Preparando...'}
                                </strong>
                              </div>
                              <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 px-3 py-2">
                                <span className="block uppercase tracking-wider text-zinc-600 dark:text-zinc-400">Views</span>
                                <strong className="block mt-1 text-zinc-950 dark:text-zinc-100">
                                  {formatSyncCount(syncProgress.processed_views)} de {formatSyncCount(syncProgress.total_views)}
                                </strong>
                              </div>
                              <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 px-3 py-2">
                                <span className="block uppercase tracking-wider text-zinc-600 dark:text-zinc-400">Linhas da view</span>
                                <strong className="block mt-1 text-zinc-950 dark:text-zinc-100">
                                  {formatSyncCount(syncProgress.current_view_rows)}
                                  {syncProgress.current_view_estimated_rows != null
                                    ? ` / ${formatSyncCount(syncProgress.current_view_estimated_rows)}`
                                    : ''}
                                </strong>
                              </div>
                            </div>
                          </motion.div>
                        )}

                        {syncNowResult && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.98 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className={cn(
                              'p-3.5 rounded-xl border flex items-start gap-2.5',
                              syncNowResult.success 
                                ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-500 dark:text-emerald-400'
                                : 'border-red-500/20 bg-red-500/5 text-red-500 dark:text-red-400'
                            )}
                          >
                            {syncNowResult.success ? (
                              <CheckCircle2 size={16} className="mt-0.5 flex-shrink-0" />
                            ) : (
                              <XCircle size={16} className="mt-0.5 flex-shrink-0" />
                            )}
                            <span className="text-[11px] leading-relaxed">{syncNowResult.message}</span>
                          </motion.div>
                        )}
                      </div>
                    </GlassCard>
                  </motion.div>
                )}

                {/* â”€â”€ TAB: AUDITORIA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
                {activeTab === 'audit' && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="space-y-6"
                  >
                    <GlassCard className="border-zinc-200 dark:border-zinc-800/50 space-y-6">
                      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-3 flex justify-between items-center">
                        <div>
                          <h3 className="text-sm font-bold text-zinc-800 dark:text-white flex items-center gap-2">
                            <History size={15} className="text-lumina-400" />
                            Painel de Auditoria & Logs de IA
                          </h3>
                          <p className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                            Monitore o desempenho do motor de NLP e as queries realizadas pelos usuários em tempo real.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={fetchAuditLogs}
                          disabled={loadingAudit}
                          className="text-[10px] font-bold py-1.5 px-3 rounded bg-zinc-100 dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 text-lumina-500 dark:text-lumina-400 hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
                        >
                          {loadingAudit ? 'Atualizando...' : 'Atualizar Logs'}
                        </button>
                      </div>

                      {/* Métricas Rápidas */}
                      {auditLogs.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-850">
                            <span className="text-[10px] font-bold uppercase text-zinc-500">Total de Consultas</span>
                            <h4 className="text-lg font-bold text-zinc-800 dark:text-white mt-1">{auditLogs.length}</h4>
                          </div>
                          
                          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-850">
                            <span className="text-[10px] font-bold uppercase text-zinc-500">Confiança Média</span>
                            <h4 className="text-lg font-bold text-emerald-500 dark:text-emerald-400 mt-1">
                              {(auditLogs.reduce((acc, log) => acc + (log.ia_confianca || 0), 0) / auditLogs.length * 100).toFixed(0)}%
                            </h4>
                          </div>

                          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-850">
                            <span className="text-[10px] font-bold uppercase text-zinc-500">Latência Média</span>
                            <h4 className="text-lg font-bold text-violet-500 dark:text-violet-400 mt-1">
                              {(auditLogs.reduce((acc, log) => acc + (log.tempo_resposta_ms || 0), 0) / auditLogs.length).toFixed(0)}ms
                            </h4>
                          </div>
                        </div>
                      )}

                      {/* Tabela de logs */}
                      {loadingAudit ? (
                        <div className="flex items-center justify-center py-12 gap-3">
                          <Loader2 className="text-lumina-400 animate-spin" size={20} />
                          <span className="text-xs text-zinc-500">Buscando logs de auditoria...</span>
                        </div>
                      ) : auditLogs.length === 0 ? (
                        <div className="p-12 border border-dashed border-zinc-300 dark:border-zinc-800 rounded-xl text-center">
                          <p className="text-xs text-zinc-500">Nenhum registro de consulta no histórico do Tenant.</p>
                        </div>
                      ) : (
                        <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/20 max-h-[500px] overflow-y-auto thin-scroll">
                          <table className="w-full text-left border-collapse text-xs">
                            <thead className="sticky top-0 z-10 bg-zinc-100/90 dark:bg-zinc-950/90 backdrop-blur border-b border-zinc-200 dark:border-zinc-850">
                              <tr className="text-zinc-650 dark:text-zinc-400 font-semibold">
                                <th className="p-3">Usuário</th>
                                <th className="p-3">Pergunta</th>
                                <th className="p-3">View Mapeada</th>
                                <th className="p-3">Confiança</th>
                                <th className="p-3">Latência</th>
                                <th className="p-3 text-right">Data/Hora</th>
                              </tr>
                            </thead>
                            <tbody>
                              {auditLogs.map(log => {
                                const lat = log.tempo_resposta_ms || 0
                                const latColor = lat < 500 ? 'text-emerald-500 dark:text-emerald-400' : lat < 1500 ? 'text-yellow-500 dark:text-yellow-400' : 'text-red-500 dark:text-red-400'
                                const conf = (log.ia_confianca || 0) * 100
                                const confColor = conf >= 70 ? 'text-emerald-500 dark:text-emerald-400' : conf >= 40 ? 'text-yellow-500 dark:text-yellow-400' : 'text-zinc-500 dark:text-zinc-400'
                                
                                return (
                                  <tr key={log.id} className="border-b border-zinc-200 dark:border-zinc-800/40 hover:bg-zinc-100 dark:hover:bg-zinc-800/10 text-zinc-700 dark:text-zinc-300">
                                    <td className="p-3 min-w-[120px]">
                                      <p className="font-semibold truncate max-w-[150px]">{log.usuario.nome}</p>
                                      <p className="text-[10px] text-zinc-500 truncate max-w-[150px]">{log.usuario.email}</p>
                                    </td>
                                    <td className="p-3 max-w-[200px] truncate font-medium" title={log.pergunta}>
                                      {log.pergunta}
                                    </td>
                                    <td className="p-3 font-mono text-[10px] text-zinc-650 dark:text-zinc-400">
                                      {log.view.nome_view_oracle ? (
                                        <span className="px-2 py-0.5 rounded bg-zinc-200 dark:bg-zinc-850 border border-zinc-300 dark:border-zinc-800 text-zinc-700 dark:text-zinc-200">
                                          {log.view.nome_view_oracle}
                                        </span>
                                      ) : (
                                        <span className="text-zinc-500 dark:text-zinc-650 italic">Nenhum match</span>
                                      )}
                                    </td>
                                    <td className="p-3">
                                      <span className={cn('font-semibold', confColor)}>
                                        {conf > 0 ? `${conf.toFixed(0)}%` : '0%'}
                                      </span>
                                    </td>
                                    <td className="p-3 font-mono">
                                      <span className={latColor}>{lat}ms</span>
                                    </td>
                                    <td className="p-3 text-right text-zinc-500 text-[10px]">
                                      {new Date(log.criado_em).toLocaleString('pt-BR')}
                                    </td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </GlassCard>
                  </motion.div>
                )}

              </div>

              {/* Botão Fixo de Salvar no Rodapé */}
              <div className="flex justify-end pt-4 border-t border-zinc-200 dark:border-zinc-900">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center justify-center gap-2 text-xs font-bold py-3 px-6 rounded-xl bg-lumina-gradient text-white shadow-lumina-lg transition-all hover:scale-102 interactive"
                >
                  {saving ? (
                    <Loader2 className="animate-spin" size={14} />
                  ) : (
                    <Save size={14} />
                  )}
                  <span>Salvar Todas as Configurações</span>
                </button>
              </div>

            </form>
          )}

        </main>
      </div>
    </div>
  )
}
