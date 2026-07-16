'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ComponentType, DragEvent } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart3,
  Copy,
  Download,
  Eye,
  EyeOff,
  Gauge,
  Grid3X3,
  Layers,
  LayoutDashboard,
  Moon,
  MousePointer2,
  PanelTop,
  RotateCcw,
  Save,
  Sparkles,
  Star,
  Sun,
  Table2,
  Upload,
} from 'lucide-react'
import { Sidebar } from '@/components/Sidebar'
import { useAuth } from '@/context/AuthContext'
import { getApiBase } from '@/lib/utils'

type StudioGridItem = {
  id: string
  x: number
  y: number
  w: number
  h: number
  hidden?: boolean
}

type StudioComponent = {
  id: string
  type: string
  title: string
  hidden?: boolean
  source_id?: string
  visual_config?: Record<string, unknown>
}

type DashboardTemplate = {
  id: string
  name: string
  description?: string | null
  category: string
  version: number
  grid: { columns?: number; items?: StudioGridItem[] }
  components: StudioComponent[]
  theme: Record<string, unknown>
  atualizado_em: string
}

type DashboardInstance = {
  id: string
  template_id: string
  name: string
  version: number
  is_favorite: boolean
  layout_override: { grid?: { columns?: number; items?: StudioGridItem[] } }
  panel_positions: Record<string, StudioGridItem>
  preferences: Record<string, unknown>
  atualizado_em: string
}

type ComponentPreset = {
  type: string
  title: string
  icon: ComponentType<{ size?: number; className?: string }>
  w: number
  h: number
}

const COMPONENT_PRESETS: ComponentPreset[] = [
  { type: 'KPI', title: 'KPI visual', icon: Gauge, w: 3, h: 2 },
  { type: 'CARD', title: 'Card executivo', icon: PanelTop, w: 3, h: 2 },
  { type: 'BAR', title: 'Grafico de barras', icon: BarChart3, w: 6, h: 4 },
  { type: 'LINE', title: 'Evolucao temporal', icon: BarChart3, w: 6, h: 4 },
  { type: 'TABLE', title: 'Tabela visual', icon: Table2, w: 12, h: 4 },
  { type: 'SUMMARY', title: 'Resumo executivo', icon: Sparkles, w: 6, h: 3 },
]

const DEFAULT_COMPONENTS: StudioComponent[] = [
  { id: 'kpi-revenue', type: 'KPI', title: 'Receita' },
  { id: 'kpi-margin', type: 'KPI', title: 'Margem' },
  { id: 'chart-main', type: 'BAR', title: 'Grafico principal' },
  { id: 'table-detail', type: 'TABLE', title: 'Detalhamento' },
]

const DEFAULT_GRID: StudioGridItem[] = [
  { id: 'kpi-revenue', x: 0, y: 0, w: 3, h: 2 },
  { id: 'kpi-margin', x: 3, y: 0, w: 3, h: 2 },
  { id: 'chart-main', x: 0, y: 2, w: 8, h: 4 },
  { id: 'table-detail', x: 0, y: 6, w: 12, h: 4 },
]

const paletteByTheme: Record<string, { primary: string; accent: string; surface: string }> = {
  corporate: { primary: '#14b8a6', accent: '#f59e0b', surface: '#0f172a' },
  dark: { primary: '#60a5fa', accent: '#22c55e', surface: '#020617' },
  light: { primary: '#0f766e', accent: '#ea580c', surface: '#f8fafc' },
  custom: { primary: '#6C63FF', accent: '#00D2D3', surface: '#111827' },
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

function overlaps(a: StudioGridItem, b: StudioGridItem) {
  return !(
    a.x + a.w <= b.x ||
    b.x + b.w <= a.x ||
    a.y + a.h <= b.y ||
    b.y + b.h <= a.y
  )
}

function normalizeGrid(items: StudioGridItem[], columns = 12) {
  const placed: StudioGridItem[] = []
  return items
    .map(item => ({
      ...item,
      x: clamp(Math.round(item.x), 0, columns - 1),
      y: Math.max(0, Math.round(item.y)),
      w: clamp(Math.round(item.w), 1, columns),
      h: clamp(Math.round(item.h), 1, 24),
    }))
    .map(item => ({ ...item, x: clamp(item.x, 0, columns - item.w) }))
    .sort((a, b) => a.y - b.y || a.x - b.x)
    .map(item => {
      const next = { ...item }
      while (placed.some(existing => overlaps(next, existing))) {
        next.y += 1
      }
      placed.push(next)
      return next
    })
}

function panelPositionsFromGrid(items: StudioGridItem[]) {
  return items.reduce<Record<string, StudioGridItem>>((acc, item) => {
    acc[item.id] = item
    return acc
  }, {})
}

function componentIcon(type: string) {
  const preset = COMPONENT_PRESETS.find(item => item.type === type)
  return preset?.icon ?? LayoutDashboard
}

function formatDate(value?: string) {
  if (!value) return 'agora'
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export default function DashboardStudioPage() {
  const { token, loading: authLoading } = useAuth()
  const canvasRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const nextComponentIdRef = useRef(0)
  const templatesRef = useRef<DashboardTemplate[]>([])
  const [templates, setTemplates] = useState<DashboardTemplate[]>([])
  const [instances, setInstances] = useState<DashboardInstance[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<DashboardTemplate | null>(null)
  const [selectedInstance, setSelectedInstance] = useState<DashboardInstance | null>(null)
  const [components, setComponents] = useState<StudioComponent[]>(DEFAULT_COMPONENTS)
  const [gridItems, setGridItems] = useState<StudioGridItem[]>(DEFAULT_GRID)
  const [templateName, setTemplateName] = useState('Executive Sales Studio')
  const [themeMode, setThemeMode] = useState<'corporate' | 'dark' | 'light' | 'custom'>('corporate')
  const [activePanel, setActivePanel] = useState<'template' | 'instance'>('template')
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const palette = paletteByTheme[themeMode]

  const request = useCallback(async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
    if (!token) {
      throw new Error('Sessao expirada. Faca login novamente.')
    }
    const response = await fetch(`${getApiBase()}/api/v1${path}`, {
      ...init,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(init.headers || {}),
      },
    })
    if (!response.ok) {
      const payload = await response.json().catch(() => null) as { error?: { message?: string } } | null
      throw new Error(payload?.error?.message || `Falha na API (${response.status})`)
    }
    return response.json() as Promise<T>
  }, [token])

  const hydrateTemplate = useCallback((template: DashboardTemplate) => {
    setSelectedTemplate(template)
    setSelectedInstance(null)
    setTemplateName(template.name)
    const items = template.grid?.items?.length ? template.grid.items : DEFAULT_GRID
    setGridItems(normalizeGrid(items))
    setComponents(template.components?.length ? template.components : DEFAULT_COMPONENTS)
    const mode = String((template.theme as { mode?: string })?.mode || 'corporate')
    setThemeMode(['corporate', 'dark', 'light', 'custom'].includes(mode) ? mode as typeof themeMode : 'corporate')
    setActivePanel('template')
  }, [])

  const hydrateInstance = useCallback((instance: DashboardInstance, template?: DashboardTemplate) => {
    const baseTemplate = template || templatesRef.current.find(item => item.id === instance.template_id) || null
    setSelectedTemplate(baseTemplate)
    setSelectedInstance(instance)
    setTemplateName(baseTemplate?.name || 'Dashboard Studio')
    const overrideItems = instance.layout_override?.grid?.items
    const baseItems = baseTemplate?.grid?.items
    setGridItems(normalizeGrid(overrideItems?.length ? overrideItems : baseItems?.length ? baseItems : DEFAULT_GRID))
    setComponents(baseTemplate?.components?.length ? baseTemplate.components : DEFAULT_COMPONENTS)
    const prefs = instance.preferences as { theme_mode?: string }
    const mode = prefs.theme_mode || String((baseTemplate?.theme as { mode?: string } | undefined)?.mode || 'corporate')
    setThemeMode(['corporate', 'dark', 'light', 'custom'].includes(mode) ? mode as typeof themeMode : 'corporate')
    setActivePanel('instance')
  }, [])

  const loadStudio = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const [templateRows, instanceRows] = await Promise.all([
        request<DashboardTemplate[]>('/dashboard-studio/templates'),
        request<DashboardInstance[]>('/dashboard-studio/instances'),
      ])
      templatesRef.current = templateRows
      setTemplates(templateRows)
      setInstances(instanceRows)
      if (instanceRows[0]) {
        const ownerTemplate = templateRows.find(item => item.id === instanceRows[0].template_id)
        hydrateInstance(instanceRows[0], ownerTemplate)
      } else if (templateRows[0]) {
        hydrateTemplate(templateRows[0])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar Studio.')
    } finally {
      setLoading(false)
    }
  }, [hydrateInstance, hydrateTemplate, request, token])

  useEffect(() => {
    void Promise.resolve().then(loadStudio)
  }, [loadStudio])

  const visibleItems = useMemo(() => {
    const hiddenIds = new Set(components.filter(component => component.hidden).map(component => component.id))
    return normalizeGrid(gridItems.filter(item => !item.hidden && !hiddenIds.has(item.id)))
  }, [components, gridItems])

  const hiddenCount = components.filter(component => component.hidden).length + gridItems.filter(item => item.hidden).length

  const updateGridItem = (id: string, updater: (item: StudioGridItem) => StudioGridItem) => {
    setGridItems(current => normalizeGrid(current.map(item => item.id === id ? updater(item) : item)))
  }

  const resizeItem = (id: string, dw: number, dh: number) => {
    updateGridItem(id, item => ({ ...item, w: clamp(item.w + dw, 1, 12), h: clamp(item.h + dh, 1, 12) }))
  }

  const toggleComponent = (id: string) => {
    setComponents(current => current.map(item => item.id === id ? { ...item, hidden: !item.hidden } : item))
    setGridItems(current => current.map(item => item.id === id ? { ...item, hidden: !item.hidden } : item))
  }

  const addComponent = (preset: ComponentPreset) => {
    nextComponentIdRef.current += 1
    const suffix = nextComponentIdRef.current.toString(36)
    const id = `${preset.type.toLowerCase()}-${suffix}`
    const y = gridItems.reduce((max, item) => Math.max(max, item.y + item.h), 0)
    setComponents(current => [...current, { id, type: preset.type, title: preset.title }])
    setGridItems(current => normalizeGrid([...current, { id, x: 0, y, w: preset.w, h: preset.h }]))
  }

  const handleDragStart = (id: string) => {
    setDraggingId(id)
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    if (!draggingId || !canvasRef.current) return
    const rect = canvasRef.current.getBoundingClientRect()
    const x = clamp(Math.floor(((event.clientX - rect.left) / rect.width) * 12), 0, 11)
    const y = Math.max(0, Math.floor((event.clientY - rect.top) / 72))
    updateGridItem(draggingId, item => ({ ...item, x, y }))
    setDraggingId(null)
  }

  const currentGridPayload = {
    columns: 12,
    gap: 16,
    row_height: 88,
    snap: true,
    auto_spacing: true,
    auto_balance: true,
    responsive: true,
    items: normalizeGrid(gridItems),
  }

  const saveTemplate = async (): Promise<DashboardTemplate | null> => {
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const payload = {
        name: templateName,
        description: 'Visual-only Dashboard Studio template',
        category: 'STUDIO',
        grid: currentGridPayload,
        components,
        component_order: gridItems.map(item => item.id),
        theme: {
          mode: themeMode,
          palette,
          typography: { heading: 'Manrope', body: 'Source Sans 3' },
          spacing: 'balanced',
          radius: 'xl',
          shadows: 'soft',
        },
        responsive: {
          desktop: { columns: 12 },
          notebook: { columns: 10 },
          tablet: { columns: 6 },
          mobile: { columns: 1, stack: true },
        },
        permissions: {
          can_move: true,
          can_resize: true,
          can_hide: true,
          can_change_analytics: false,
        },
      }
      const saved = selectedTemplate
        ? await request<DashboardTemplate>(`/dashboard-studio/templates/${selectedTemplate.id}`, {
            method: 'PATCH',
            body: JSON.stringify({ ...payload, description_change: 'Saved from Dashboard Studio' }),
          })
        : await request<DashboardTemplate>('/dashboard-studio/templates', {
            method: 'POST',
            body: JSON.stringify(payload),
          })
      setSelectedTemplate(saved)
      setTemplates(current => {
        const next = [saved, ...current.filter(item => item.id !== saved.id)]
        templatesRef.current = next
        return next
      })
      setNotice('Template visual salvo com versionamento.')
      return saved
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao salvar template.')
      return null
    } finally {
      setSaving(false)
    }
  }

  const saveInstance = async () => {
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      let template = selectedTemplate
      if (!template) {
        template = await saveTemplate()
      }
      if (!template) {
        throw new Error('Salve um Template antes de criar a Instance.')
      }
      const payload = {
        name: selectedInstance?.name || `${template.name} - Minha instancia`,
        panel_positions: panelPositionsFromGrid(gridItems),
        layout_override: { grid: currentGridPayload },
        preferences: {
          theme_mode: themeMode,
          studio_saved_at: new Date().toISOString(),
        },
      }
      const saved = selectedInstance
        ? await request<DashboardInstance>(`/dashboard-studio/instances/${selectedInstance.id}`, {
            method: 'PATCH',
            body: JSON.stringify({ ...payload, description_change: 'Saved user layout from Dashboard Studio' }),
          })
        : await request<DashboardInstance>('/dashboard-studio/instances', {
            method: 'POST',
            body: JSON.stringify({ ...payload, template_id: template.id }),
          })
      setSelectedInstance(saved)
      setInstances(current => [saved, ...current.filter(item => item.id !== saved.id)])
      setNotice('Instance do usuario salva sem alterar o Template original.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao salvar instance.')
    } finally {
      setSaving(false)
    }
  }

  const createNewDraft = () => {
    setSelectedTemplate(null)
    setSelectedInstance(null)
    setTemplateName('Enterprise Studio Layout')
    setComponents(DEFAULT_COMPONENTS)
    setGridItems(DEFAULT_GRID)
    setThemeMode('corporate')
    setActivePanel('template')
    setNotice('Novo rascunho visual criado localmente.')
  }

  const duplicateInstance = async () => {
    if (!selectedInstance) return
    setSaving(true)
    try {
      const copy = await request<DashboardInstance>(`/dashboard-studio/instances/${selectedInstance.id}/duplicate`, {
        method: 'POST',
        body: JSON.stringify({ name: `${selectedInstance.name} - Copy` }),
      })
      setInstances(current => [copy, ...current])
      hydrateInstance(copy)
      setNotice('Instance duplicada com estado visual independente.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao duplicar instance.')
    } finally {
      setSaving(false)
    }
  }

  const toggleFavorite = async () => {
    if (!selectedInstance) return
    try {
      const saved = await request<DashboardInstance>(`/dashboard-studio/instances/${selectedInstance.id}/favorite`, {
        method: 'POST',
        body: JSON.stringify({ is_favorite: !selectedInstance.is_favorite }),
      })
      setSelectedInstance(saved)
      setInstances(current => current.map(item => item.id === saved.id ? saved : item))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao favoritar instance.')
    }
  }

  const exportLayout = async () => {
    const target = selectedInstance
      ? `/dashboard-studio/instances/${selectedInstance.id}/export`
      : selectedTemplate
        ? `/dashboard-studio/templates/${selectedTemplate.id}/export`
        : null
    if (!target) return
    try {
      const exported = await request<Record<string, unknown>>(target)
      const blob = new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `lumina-dashboard-studio-${Date.now()}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao exportar layout.')
    }
  }

  const importLayout = async (file: File) => {
    try {
      const text = await file.text()
      const parsed = JSON.parse(text) as { target_type?: string; payload?: Record<string, unknown> }
      const imported = await request<DashboardTemplate | DashboardInstance>('/dashboard-studio/import', {
        method: 'POST',
        body: JSON.stringify({
          target_type: parsed.target_type || 'TEMPLATE',
          payload: parsed.payload || parsed,
          name_override: 'Imported Studio Layout',
        }),
      })
      if ('template_id' in imported) {
        setInstances(current => [imported, ...current])
      } else {
        setTemplates(current => {
          const next = [imported, ...current]
          templatesRef.current = next
          return next
        })
        hydrateTemplate(imported)
      }
      setNotice('Layout importado com sucesso.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao importar layout.')
    }
  }

  if (authLoading || loading) {
    return (
      <div className="flex h-dvh items-center justify-center" style={{ background: 'rgb(var(--bg-base))' }}>
        <div className="lumina-card p-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-lumina-400 border-t-transparent animate-spin" />
          <span className="text-sm" style={{ color: 'rgb(var(--text-secondary))' }}>Carregando Dashboard Studio...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-dvh overflow-hidden" style={{ background: 'rgb(var(--bg-base))' }}>
      <Sidebar />
      <main className="flex-1 min-w-0 overflow-hidden" style={{ marginLeft: 'var(--sidebar-w)' }}>
        <div className="h-full overflow-y-auto">
          <section className="relative min-h-full overflow-hidden p-4 md:p-6">
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background:
                  `radial-gradient(circle at 12% 12%, ${palette.primary}22, transparent 28%), ` +
                  `radial-gradient(circle at 82% 0%, ${palette.accent}18, transparent 30%), ` +
                  'linear-gradient(135deg, rgb(var(--bg-base)), rgb(var(--bg-surface)))',
              }}
            />
            <div className="relative z-10 flex flex-col gap-5">
              <header className="flex flex-col xl:flex-row xl:items-end xl:justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-[0.24em] bg-lumina-500/10 text-lumina-400 border border-lumina-500/20">
                      Dashboard Studio
                    </span>
                    <span className="px-3 py-1 rounded-full text-[11px] font-semibold border" style={{ borderColor: 'rgb(var(--border))', color: 'rgb(var(--text-muted))' }}>
                      Visual-only
                    </span>
                  </div>
                  <h1 className="text-3xl md:text-5xl font-black tracking-tight text-gradient">
                    Studio Enterprise
                  </h1>
                  <p className="max-w-2xl mt-3 text-sm md:text-base leading-relaxed" style={{ color: 'rgb(var(--text-secondary))' }}>
                    Personalize layout, grid, tema e estado visual sem alterar Blueprint, Business Layer, KPIs, formulas ou dados.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button onClick={createNewDraft} className="px-4 py-2.5 rounded-xl text-xs font-bold border hover:bg-[rgb(var(--bg-elevated))]" style={{ borderColor: 'rgb(var(--border))' }}>
                    Novo layout
                  </button>
                  <button onClick={saveTemplate} disabled={saving} className="px-4 py-2.5 rounded-xl text-xs font-bold bg-lumina-gradient text-white shadow-lumina flex items-center gap-2 disabled:opacity-60">
                    <Save size={14} /> Salvar Template
                  </button>
                  <button onClick={saveInstance} disabled={saving || !selectedTemplate} className="px-4 py-2.5 rounded-xl text-xs font-bold text-white flex items-center gap-2 disabled:opacity-50" style={{ background: palette.primary }}>
                    <MousePointer2 size={14} /> Salvar Instance
                  </button>
                </div>
              </header>

              {/* Guia Rápido de Uso - UI Explicativa */}
              <div className="rounded-[1.5rem] border p-5 flex flex-col md:flex-row gap-5 items-start md:items-center justify-between transition-all" style={{ background: `linear-gradient(145deg, rgb(var(--bg-surface) / 0.8), ${palette.primary}08)`, borderColor: 'rgb(var(--border))' }}>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm font-black" style={{ color: palette.primary }}>
                    <Sparkles size={16} />
                    <span>Guia Rápido do Studio</span>
                  </div>
                  <p className="text-xs" style={{ color: 'rgb(var(--text-secondary))' }}>
                    Siga o passo a passo para customizar o painel e salvar suas preferências sem código.
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 w-full md:w-auto md:max-w-4xl text-[11px] leading-relaxed">
                  <div className="p-3 rounded-2xl border bg-white/5" style={{ borderColor: 'rgb(var(--border) / 0.5)' }}>
                    <strong style={{ color: palette.primary }}>1. Adicione</strong>
                    <p style={{ color: 'rgb(var(--text-muted))' }}>Clique nos botões da barra lateral para inserir novos tipos de widgets.</p>
                  </div>
                  <div className="p-3 rounded-2xl border bg-white/5" style={{ borderColor: 'rgb(var(--border) / 0.5)' }}>
                    <strong style={{ color: palette.primary }}>2. Arraste</strong>
                    <p style={{ color: 'rgb(var(--text-muted))' }}>Clique e segure o widget para movê-lo pela grade pontilhada central.</p>
                  </div>
                  <div className="p-3 rounded-2xl border bg-white/5" style={{ borderColor: 'rgb(var(--border) / 0.5)' }}>
                    <strong style={{ color: palette.primary }}>3. Redimensione</strong>
                    <p style={{ color: 'rgb(var(--text-muted))' }}>Use Largura e Altura (+/-) para ajustar as colunas ocupadas pelo widget.</p>
                  </div>
                  <div className="p-3 rounded-2xl border bg-white/5" style={{ borderColor: 'rgb(var(--border) / 0.5)' }}>
                    <strong style={{ color: palette.primary }}>4. Salve</strong>
                    <p style={{ color: 'rgb(var(--text-muted))' }}>Clique em Salvar Template para todos, ou Salvar Instance para você.</p>
                  </div>
                </div>
              </div>

              {(error || notice) && (
                <div className="lumina-card p-3 text-sm" style={{ color: error ? '#f87171' : 'rgb(var(--text-secondary))' }}>
                  {error || notice}
                </div>
              )}

              <div className="grid grid-cols-1 2xl:grid-cols-[320px_minmax(0,1fr)_330px] gap-4">
                <aside className="space-y-4">
                  <div className="lumina-card p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h2 className="text-sm font-bold" style={{ color: 'rgb(var(--text-primary))' }}>Templates</h2>
                      <Layers size={15} className="text-lumina-400" />
                    </div>
                    <div className="space-y-2 max-h-60 overflow-y-auto thin-scroll">
                      {templates.length === 0 && (
                        <p className="text-xs leading-relaxed" style={{ color: 'rgb(var(--text-muted))' }}>
                          Nenhum template ainda. Salve o rascunho atual para criar o primeiro.
                        </p>
                      )}
                      {templates.map(template => (
                        <button
                          key={template.id}
                          onClick={() => hydrateTemplate(template)}
                          className="w-full text-left rounded-2xl p-3 border transition-all hover:bg-[rgb(var(--bg-elevated))]"
                          style={{
                            borderColor: selectedTemplate?.id === template.id && !selectedInstance ? palette.primary : 'rgb(var(--border) / 0.6)',
                          }}
                        >
                          <p className="text-xs font-bold truncate" style={{ color: 'rgb(var(--text-primary))' }}>{template.name}</p>
                          <p className="text-[11px] mt-1" style={{ color: 'rgb(var(--text-muted))' }}>v{template.version} - {formatDate(template.atualizado_em)}</p>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="lumina-card p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h2 className="text-sm font-bold" style={{ color: 'rgb(var(--text-primary))' }}>Instances</h2>
                      <Star size={15} className="text-yellow-400" />
                    </div>
                    <div className="space-y-2 max-h-60 overflow-y-auto thin-scroll">
                      {instances.length === 0 && (
                        <p className="text-xs leading-relaxed" style={{ color: 'rgb(var(--text-muted))' }}>
                          Salve uma Instance para preservar preferencias do usuario.
                        </p>
                      )}
                      {instances.map(instance => (
                        <button
                          key={instance.id}
                          onClick={() => hydrateInstance(instance)}
                          className="w-full text-left rounded-2xl p-3 border transition-all hover:bg-[rgb(var(--bg-elevated))]"
                          style={{
                            borderColor: selectedInstance?.id === instance.id ? palette.accent : 'rgb(var(--border) / 0.6)',
                          }}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-xs font-bold truncate" style={{ color: 'rgb(var(--text-primary))' }}>{instance.name}</p>
                            {instance.is_favorite && <Star size={12} className="fill-yellow-400 text-yellow-400" />}
                          </div>
                          <p className="text-[11px] mt-1" style={{ color: 'rgb(var(--text-muted))' }}>v{instance.version} - {formatDate(instance.atualizado_em)}</p>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="lumina-card p-4">
                    <h2 className="text-sm font-bold mb-3" style={{ color: 'rgb(var(--text-primary))' }}>Adicionar</h2>
                    <div className="grid grid-cols-2 gap-2">
                      {COMPONENT_PRESETS.map(preset => {
                        const Icon = preset.icon
                        return (
                          <button
                            key={preset.type}
                            onClick={() => addComponent(preset)}
                            className="p-3 rounded-2xl border text-left hover:bg-[rgb(var(--bg-elevated))] transition-colors"
                            style={{ borderColor: 'rgb(var(--border) / 0.7)' }}
                          >
                            <Icon size={15} className="mb-2 text-lumina-400" />
                            <p className="text-[11px] font-bold" style={{ color: 'rgb(var(--text-primary))' }}>{preset.type}</p>
                            <p className="text-[10px] mt-1" style={{ color: 'rgb(var(--text-muted))' }}>{preset.title}</p>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                </aside>

                <section className="lumina-card p-4 md:p-5 min-h-[720px]">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
                    <div>
                      <input
                        value={templateName}
                        onChange={event => setTemplateName(event.target.value)}
                        className="bg-transparent text-xl md:text-2xl font-black outline-none w-full border-b border-dashed border-white/20 pb-1"
                        style={{ color: 'rgb(var(--text-primary))' }}
                      />
                      <p className="text-xs mt-2" style={{ color: 'rgb(var(--text-muted))' }}>
                        {activePanel === 'instance' ? 'Editando preferencias da Instance' : 'Editando Template visual permanente'} - {visibleItems.length} visiveis, {hiddenCount} ocultos
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => setGridItems(current => normalizeGrid(current))} className="px-3 py-2 rounded-xl text-xs font-bold border flex items-center gap-2 hover:bg-white/5" style={{ borderColor: 'rgb(var(--border))' }}>
                        <Grid3X3 size={14} /> Auto balance
                      </button>
                      <button onClick={() => setGridItems(DEFAULT_GRID)} className="px-3 py-2 rounded-xl text-xs font-bold border flex items-center gap-2 hover:bg-white/5" style={{ borderColor: 'rgb(var(--border))' }}>
                        <RotateCcw size={14} /> Restaurar
                      </button>
                    </div>
                  </div>

                  <div
                    ref={canvasRef}
                    onDragOver={event => event.preventDefault()}
                    onDrop={handleDrop}
                    className="relative rounded-[2rem] border p-3 md:p-4 min-h-[620px] overflow-hidden"
                    style={{
                      borderColor: `${palette.primary}55`,
                      background:
                        `linear-gradient(90deg, rgb(var(--border) / 0.28) 1px, transparent 1px), ` +
                        `linear-gradient(rgb(var(--border) / 0.28) 1px, transparent 1px), ` +
                        `linear-gradient(145deg, ${palette.surface}cc, rgb(var(--bg-surface)))`,
                      backgroundSize: 'calc(100% / 12) 72px, calc(100% / 12) 72px, auto',
                    }}
                  >
                    <div
                      className="grid gap-3"
                      style={{
                        gridTemplateColumns: 'repeat(12, minmax(0, 1fr))',
                        gridAutoRows: '64px',
                      }}
                    >
                      {visibleItems.map((item, index) => {
                        const component = components.find(entry => entry.id === item.id)
                        const Icon = componentIcon(component?.type || 'CARD')
                        return (
                          <motion.article
                            key={item.id}
                            draggable
                            onDragStart={() => handleDragStart(item.id)}
                            initial={{ opacity: 0, y: 16, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            transition={{ delay: index * 0.03 }}
                            className="group rounded-3xl border p-4 flex flex-col justify-between cursor-grab active:cursor-grabbing overflow-hidden"
                            style={{
                              gridColumn: `${item.x + 1} / span ${item.w}`,
                              gridRow: `${item.y + 1} / span ${item.h}`,
                              borderColor: 'rgb(var(--border) / 0.75)',
                              background: `linear-gradient(145deg, rgb(var(--bg-surface) / 0.94), ${palette.primary}10)`,
                              boxShadow: `0 18px 60px ${palette.primary}12`,
                            }}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="w-8 h-8 rounded-2xl flex items-center justify-center" style={{ background: `${palette.primary}22`, color: palette.primary }}>
                                    <Icon size={15} />
                                  </span>
                                  <span className="text-[10px] font-black uppercase tracking-[0.18em]" style={{ color: palette.primary }}>
                                    {component?.type || 'CARD'}
                                  </span>
                                </div>
                                <h3 className="text-sm md:text-base font-black truncate" style={{ color: 'rgb(var(--text-primary))' }}>
                                  {component?.title || item.id}
                                </h3>
                                <p className="text-[10px] mt-1" style={{ color: 'rgb(var(--text-muted))' }}>
                                  Coluna {item.x + 1} | Linha {item.y + 1} | Tamanho: {item.w}x{item.h}
                                </p>
                              </div>
                              <button onClick={() => toggleComponent(item.id)} className="opacity-0 group-hover:opacity-100 transition-opacity">
                                <EyeOff size={15} />
                              </button>
                            </div>
                            <div className="flex items-center gap-1.5 pt-4">
                              <button onClick={() => resizeItem(item.id, 1, 0)} className="px-2.5 py-1 rounded-xl text-[10px] font-bold bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">Largura +</button>
                              <button onClick={() => resizeItem(item.id, -1, 0)} className="px-2.5 py-1 rounded-xl text-[10px] font-bold bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">Largura -</button>
                              <button onClick={() => resizeItem(item.id, 0, 1)} className="px-2.5 py-1 rounded-xl text-[10px] font-bold bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">Altura +</button>
                              <button onClick={() => resizeItem(item.id, 0, -1)} className="px-2.5 py-1 rounded-xl text-[10px] font-bold bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">Altura -</button>
                            </div>
                          </motion.article>
                        )
                      })}
                    </div>
                  </div>
                </section>

                <aside className="space-y-4">
                  <div className="lumina-card p-4">
                    <h2 className="text-sm font-bold mb-3" style={{ color: 'rgb(var(--text-primary))' }}>Modo de edicao</h2>
                    <div className="grid grid-cols-2 gap-2">
                      {(['template', 'instance'] as const).map(mode => (
                        <button
                          key={mode}
                          onClick={() => setActivePanel(mode)}
                          className="p-3 rounded-2xl border text-xs font-bold capitalize"
                          style={{
                            borderColor: activePanel === mode ? palette.primary : 'rgb(var(--border))',
                            color: activePanel === mode ? palette.primary : 'rgb(var(--text-secondary))',
                          }}
                        >
                          {mode}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="lumina-card p-4">
                    <h2 className="text-sm font-bold mb-3" style={{ color: 'rgb(var(--text-primary))' }}>Temas</h2>
                    <div className="grid grid-cols-2 gap-2">
                      {(['corporate', 'dark', 'light', 'custom'] as const).map(mode => (
                        <button
                          key={mode}
                          onClick={() => setThemeMode(mode)}
                          className="p-3 rounded-2xl border text-left"
                          style={{
                            borderColor: themeMode === mode ? paletteByTheme[mode].primary : 'rgb(var(--border))',
                            background: `${paletteByTheme[mode].primary}10`,
                          }}
                        >
                          <div className="flex items-center gap-2">
                            {mode === 'light' ? <Sun size={14} /> : <Moon size={14} />}
                            <span className="text-xs font-bold capitalize" style={{ color: 'rgb(var(--text-primary))' }}>{mode}</span>
                          </div>
                          <div className="flex gap-1 mt-3">
                            {Object.values(paletteByTheme[mode]).map(color => (
                              <span key={color} className="w-5 h-2 rounded-full" style={{ background: color }} />
                            ))}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="lumina-card p-4">
                    <h2 className="text-sm font-bold mb-3" style={{ color: 'rgb(var(--text-primary))' }}>Componentes</h2>
                    <div className="space-y-2 max-h-80 overflow-y-auto thin-scroll">
                      {components.map(component => {
                        const Icon = component.hidden ? EyeOff : Eye
                        return (
                          <div key={component.id} className="flex items-center justify-between gap-2 p-2 rounded-2xl border" style={{ borderColor: 'rgb(var(--border) / 0.65)' }}>
                            <div className="min-w-0">
                              <p className="text-xs font-bold truncate" style={{ color: 'rgb(var(--text-primary))' }}>{component.title}</p>
                              <p className="text-[10px]" style={{ color: 'rgb(var(--text-muted))' }}>{component.type}</p>
                            </div>
                            <button onClick={() => toggleComponent(component.id)} className="w-8 h-8 rounded-xl flex items-center justify-center hover:bg-[rgb(var(--bg-elevated))]">
                              <Icon size={14} />
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  <div className="lumina-card p-4">
                    <h2 className="text-sm font-bold mb-3" style={{ color: 'rgb(var(--text-primary))' }}>Governanca</h2>
                    <div className="space-y-2 text-xs" style={{ color: 'rgb(var(--text-secondary))' }}>
                      <p>Blueprint: somente referencia, nunca alterado.</p>
                      <p>KPIs/Formulas: bloqueados pela API.</p>
                      <p>Grid: snap, auto-spacing e anti-overlap.</p>
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-4">
                      <button onClick={duplicateInstance} disabled={!selectedInstance} className="px-3 py-2 rounded-xl text-xs font-bold border flex items-center justify-center gap-2 disabled:opacity-40" style={{ borderColor: 'rgb(var(--border))' }}>
                        <Copy size={13} /> Duplicar
                      </button>
                      <button onClick={toggleFavorite} disabled={!selectedInstance} className="px-3 py-2 rounded-xl text-xs font-bold border flex items-center justify-center gap-2 disabled:opacity-40" style={{ borderColor: 'rgb(var(--border))' }}>
                        <Star size={13} /> Favorito
                      </button>
                      <button onClick={exportLayout} disabled={!selectedTemplate && !selectedInstance} className="px-3 py-2 rounded-xl text-xs font-bold border flex items-center justify-center gap-2 disabled:opacity-40" style={{ borderColor: 'rgb(var(--border))' }}>
                        <Download size={13} /> Exportar
                      </button>
                      <button onClick={() => fileInputRef.current?.click()} className="px-3 py-2 rounded-xl text-xs font-bold border flex items-center justify-center gap-2" style={{ borderColor: 'rgb(var(--border))' }}>
                        <Upload size={13} /> Importar
                      </button>
                    </div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="application/json"
                      className="hidden"
                      onChange={event => {
                        const file = event.target.files?.[0]
                        if (file) void importLayout(file)
                        event.currentTarget.value = ''
                      }}
                    />
                  </div>
                </aside>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}
