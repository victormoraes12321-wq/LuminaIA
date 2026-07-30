'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Accessibility,
  AlertCircle,
  Check,
  Download,
  EyeOff,
  FileClock,
  Loader2,
  MonitorCog,
  RefreshCw,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  UserRoundCog,
  X,
} from 'lucide-react'
import { Sidebar } from '@/components/Sidebar'
import { useAuth } from '@/context/AuthContext'
import { cn, formatDate, getApiBase } from '@/lib/utils'
import type {
  ProfileApiError,
  ProfileCapabilities,
  UserAnalyticalProfile,
  UserPreference,
} from '@/types/userAnalyticalProfile'

const API_PATH = '/api/v2/me'
const buttonClass = 'inline-flex min-h-9 items-center justify-center gap-2 rounded-md border border-zinc-700/60 px-3 py-2 text-xs font-semibold text-zinc-300 transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50'
const inputClass = 'h-9 w-full rounded-md border border-zinc-700/60 bg-zinc-950/40 px-3 text-sm text-zinc-100 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20'

function errorMessage(payload: ProfileApiError, fallback: string): string {
  return payload.error?.message ?? payload.detail ?? fallback
}

function preferenceByType(
  profile: UserAnalyticalProfile | null,
  type: UserPreference['preference_type'],
): UserPreference | undefined {
  return profile?.preferences.find(item => item.preference_type === type)
}

export default function UserAnalyticalProfilePage() {
  const { token, loading: authLoading } = useAuth()
  const apiBase = getApiBase()
  const [capabilities, setCapabilities] = useState<ProfileCapabilities | null>(null)
  const [profile, setProfile] = useState<UserAnalyticalProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteReason, setDeleteReason] = useState('')
  const [locale, setLocale] = useState('pt-BR')
  const [timezone, setTimezone] = useState('America/Sao_Paulo')
  const [currency, setCurrency] = useState('BRL')
  const [dateFormat, setDateFormat] = useState('DD/MM/YYYY')
  const [numberFormat, setNumberFormat] = useState('pt-BR')
  const [visualization, setVisualization] = useState('AUTO')
  const [density, setDensity] = useState('COMFORTABLE')
  const [pageSize, setPageSize] = useState(25)
  const [decimalPlaces, setDecimalPlaces] = useState(2)
  const [theme, setTheme] = useState('SYSTEM')
  const [reducedMotion, setReducedMotion] = useState(false)
  const [highContrast, setHighContrast] = useState(false)
  const [largerText, setLargerText] = useState(false)

  const request = useCallback(async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const response = await fetch(`${apiBase}${API_PATH}${path}`, {
      ...init,
      credentials: 'include',
      headers: {
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    })
    const payload = await response.json() as T & ProfileApiError
    if (!response.ok) throw new Error(errorMessage(payload, 'Não foi possível concluir a operação.'))
    return payload
  }, [apiBase, token])

  const hydrateForm = useCallback((value: UserAnalyticalProfile) => {
    const localePreference = preferenceByType(value, 'LOCALE')
    const presentationPreference = preferenceByType(value, 'PRESENTATION')
    const accessibilityPreference = preferenceByType(value, 'ACCESSIBILITY')
    if (localePreference) {
      setLocale(String(localePreference.content.locale ?? 'pt-BR'))
      setTimezone(String(localePreference.content.timezone ?? 'America/Sao_Paulo'))
      setCurrency(String(localePreference.content.currency_display ?? 'BRL'))
      setDateFormat(String(localePreference.content.date_format ?? 'DD/MM/YYYY'))
      setNumberFormat(String(localePreference.content.number_format ?? 'pt-BR'))
    }
    if (presentationPreference) {
      setVisualization(String(presentationPreference.content.preferred_visualization ?? 'AUTO'))
      setDensity(String(presentationPreference.content.table_density ?? 'COMFORTABLE'))
      setPageSize(Number(presentationPreference.content.page_size ?? 25))
      setDecimalPlaces(Number(presentationPreference.content.decimal_places ?? 2))
      setTheme(String(presentationPreference.content.theme ?? 'SYSTEM'))
    }
    if (accessibilityPreference) {
      setReducedMotion(Boolean(accessibilityPreference.content.reduced_motion))
      setHighContrast(Boolean(accessibilityPreference.content.high_contrast))
      setLargerText(Boolean(accessibilityPreference.content.larger_text))
    }
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const available = await request<ProfileCapabilities>('/analytical-profile/capabilities')
      setCapabilities(available)
      if (available.mode === 'LEGACY_ONLY' || !available.frontend_enabled) return
      const value = await request<UserAnalyticalProfile>('/analytical-profile')
      setProfile(value)
      hydrateForm(value)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao carregar o perfil.')
    } finally {
      setLoading(false)
    }
  }, [hydrateForm, request])

  useEffect(() => {
    if (authLoading) return
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [authLoading, load])

  const savePreference = useCallback(async (
    type: UserPreference['preference_type'],
    key: string,
    content: Record<string, string | number | boolean>,
  ) => {
    const existing = preferenceByType(profile, type)
    if (existing) {
      return request<UserPreference>(`/preferences/${existing.preference_id}`, {
        method: 'PUT',
        body: JSON.stringify({
          expected_lock_version: existing.lock_version,
          content,
          effective_from: null,
          effective_to: null,
          expires_at: null,
        }),
      })
    }
    return request<UserPreference>('/preferences', {
      method: 'POST',
      body: JSON.stringify({
        preference_key: key,
        content,
        origin: 'USER_EXPLICIT',
      }),
    })
  }, [profile, request])

  const saveAll = async () => {
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      await savePreference('LOCALE', 'display.locale', {
        kind: 'LOCALE',
        locale,
        timezone,
        currency_display: currency,
        date_format: dateFormat,
        number_format: numberFormat,
      })
      await savePreference('PRESENTATION', 'display.presentation', {
        kind: 'PRESENTATION',
        preferred_visualization: visualization,
        table_first: true,
        table_density: density,
        page_size: pageSize,
        decimal_places: decimalPlaces,
        ordering: 'DEFAULT',
        chart_granularity: 'AUTO',
        theme,
      })
      await savePreference('ACCESSIBILITY', 'display.accessibility', {
        kind: 'ACCESSIBILITY',
        reduced_motion: reducedMotion,
        high_contrast: highContrast,
        larger_text: largerText,
        accessible_labels: true,
      })
      setNotice('Preferências atualizadas.')
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao salvar preferências.')
    } finally {
      setSaving(false)
    }
  }

  const setPreferenceStatus = async (item: UserPreference) => {
    setSaving(true)
    setError(null)
    try {
      const action = item.status === 'ACTIVE' ? 'disable' : 'reactivate'
      await request(`/preferences/${item.preference_id}/${action}`, {
        method: 'POST',
        body: JSON.stringify({ expected_lock_version: item.lock_version }),
      })
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao alterar preferência.')
    } finally {
      setSaving(false)
    }
  }

  const toggleConsent = async (item: UserPreference) => {
    setSaving(true)
    setError(null)
    try {
      if (item.consent?.status === 'GRANTED') {
        await request(`/preferences/${item.preference_id}/consent`, {
          method: 'DELETE',
          body: JSON.stringify({ expected_lock_version: item.consent.lock_version }),
        })
      } else {
        await request(`/preferences/${item.preference_id}/consent`, {
          method: 'POST',
          body: JSON.stringify({
            expected_preference_lock_version: item.lock_version,
            purpose: 'Aplicar este padrão analítico quando o pedido e o contexto não definirem o campo.',
            scope: item.preference_key,
            policy_version: 'user-profile-consent/1.0',
          }),
        })
      }
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao alterar consentimento.')
    } finally {
      setSaving(false)
    }
  }

  const toggleProfile = async () => {
    if (!profile) return
    setSaving(true)
    setError(null)
    try {
      const action = profile.status === 'ACTIVE' ? 'disable' : 'reactivate'
      await request(`/analytical-profile/${action}`, {
        method: 'POST',
        body: JSON.stringify({ expected_lock_version: profile.lock_version }),
      })
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao alterar o perfil.')
    } finally {
      setSaving(false)
    }
  }

  const exportProfile = async () => {
    setSaving(true)
    setError(null)
    try {
      const exported = await request<Record<string, unknown>>('/profile/export')
      const blob = new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'lumina-perfil-analitico.json'
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao exportar o perfil.')
    } finally {
      setSaving(false)
    }
  }

  const requestDeletion = async () => {
    setSaving(true)
    setError(null)
    try {
      await request('/analytical-profile/deletion-requests', {
        method: 'POST',
        headers: { 'Idempotency-Key': crypto.randomUUID() },
        body: JSON.stringify({ reason: deleteReason || null }),
      })
      setDeleteOpen(false)
      setNotice('Solicitação de exclusão registrada.')
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Falha ao solicitar exclusão.')
    } finally {
      setSaving(false)
    }
  }

  const analyticalItems = useMemo(
    () => profile?.preferences.filter(item => !['LOCALE', 'PRESENTATION', 'ACCESSIBILITY'].includes(item.preference_type)) ?? [],
    [profile],
  )

  if (loading || authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-300">
        <Loader2 className="animate-spin" aria-label="Carregando perfil" />
      </div>
    )
  }

  const unavailable = capabilities?.mode === 'LEGACY_ONLY' || !capabilities?.frontend_enabled

  return (
    <div className="flex min-h-screen bg-[rgb(var(--bg-primary))] text-[rgb(var(--text-primary))]">
      <Sidebar />
      <main className="dashboard-main-content min-w-0 flex-1 overflow-y-auto">
        <header className="border-b border-zinc-800/70 px-5 py-4 sm:px-8">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
            <div>
              <h1 className="flex items-center gap-2 text-lg font-semibold">
                <UserRoundCog size={18} className="text-cyan-400" />
                Meu perfil analítico
              </h1>
              <p className="mt-1 text-xs text-zinc-400">Preferências pessoais explícitas e controladas por você.</p>
            </div>
            {!unavailable && (
              <button type="button" onClick={() => void load()} className={buttonClass} title="Recarregar perfil">
                <RefreshCw size={14} />
                Atualizar
              </button>
            )}
          </div>
        </header>

        <div className="mx-auto max-w-6xl space-y-8 px-5 py-6 sm:px-8">
          {error && (
            <div role="alert" className="flex items-start gap-2 rounded-md border border-red-500/30 bg-red-950/20 p-3 text-sm text-red-300">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              {error}
            </div>
          )}
          {notice && (
            <div role="status" className="flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-950/20 p-3 text-sm text-emerald-300">
              <Check size={16} />
              {notice}
            </div>
          )}

          {unavailable ? (
            <section className="border-y border-zinc-800 py-8" data-testid="profile-disabled-state">
              <h2 className="text-base font-semibold">Perfil V2 ainda não ativado</h2>
              <p className="mt-2 max-w-2xl text-sm text-zinc-400">
                O comportamento atual continua preservado. Nenhuma preferência nova está sendo aplicada.
              </p>
            </section>
          ) : profile ? (
            <>
              <section className="grid gap-4 border-b border-zinc-800 pb-6 sm:grid-cols-3">
                <div>
                  <p className="text-xs text-zinc-500">Status</p>
                  <p className="mt-1 text-sm font-semibold">{profile.status === 'ACTIVE' ? 'Ativo' : 'Desativado'}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500">Preferências</p>
                  <p className="mt-1 text-sm font-semibold">{profile.preferences.length}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500">Última atualização</p>
                  <p className="mt-1 text-sm font-semibold">{formatDate(profile.updated_at)}</p>
                </div>
              </section>

              <section aria-labelledby="locale-title" className="space-y-4 border-b border-zinc-800 pb-8">
                <div>
                  <h2 id="locale-title" className="flex items-center gap-2 text-sm font-semibold">
                    <MonitorCog size={16} className="text-cyan-400" />
                    Idioma e formatação
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500">Essas opções mudam apenas a apresentação.</p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                  <label className="space-y-1 text-xs text-zinc-400">Idioma
                    <select value={locale} onChange={event => setLocale(event.target.value)} className={inputClass}>
                      <option value="pt-BR">Português (Brasil)</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-xs text-zinc-400">Fuso horário
                    <select value={timezone} onChange={event => setTimezone(event.target.value)} className={inputClass}>
                      <option value="America/Sao_Paulo">São Paulo</option>
                      <option value="America/Fortaleza">Fortaleza</option>
                      <option value="UTC">UTC</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-xs text-zinc-400">Moeda
                    <select value={currency} onChange={event => setCurrency(event.target.value)} className={inputClass}>
                      <option value="BRL">Real (BRL)</option>
                      <option value="USD">Dólar (USD)</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-xs text-zinc-400">Data
                    <select value={dateFormat} onChange={event => setDateFormat(event.target.value)} className={inputClass}>
                      <option value="DD/MM/YYYY">DD/MM/AAAA</option>
                      <option value="YYYY-MM-DD">AAAA-MM-DD</option>
                      <option value="DD MMM YYYY">DD MMM AAAA</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-xs text-zinc-400">Números
                    <select value={numberFormat} onChange={event => setNumberFormat(event.target.value)} className={inputClass}>
                      <option value="pt-BR">1.234,56</option>
                      <option value="en-US">1,234.56</option>
                    </select>
                  </label>
                </div>
              </section>

              <section aria-labelledby="presentation-title" className="space-y-4 border-b border-zinc-800 pb-8">
                <div>
                  <h2 id="presentation-title" className="flex items-center gap-2 text-sm font-semibold">
                    <SlidersHorizontal size={16} className="text-cyan-400" />
                    Apresentação
                  </h2>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                  <label className="space-y-1 text-xs text-zinc-400">Visualização
                    <select value={visualization} onChange={event => setVisualization(event.target.value)} className={inputClass}>
                      <option value="AUTO">Automática</option>
                      <option value="TABLE">Tabela</option>
                      <option value="BAR_CHART">Barras</option>
                      <option value="LINE_CHART">Linha</option>
                      <option value="PIE_CHART">Pizza</option>
                      <option value="KPI_CARD">Indicador</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-xs text-zinc-400">Densidade
                    <select value={density} onChange={event => setDensity(event.target.value)} className={inputClass}>
                      <option value="COMPACT">Compacta</option>
                      <option value="COMFORTABLE">Confortável</option>
                      <option value="SPACIOUS">Espaçosa</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-xs text-zinc-400">Itens por página
                    <input type="number" min={5} max={200} value={pageSize} onChange={event => setPageSize(Number(event.target.value))} className={inputClass} />
                  </label>
                  <label className="space-y-1 text-xs text-zinc-400">Casas decimais
                    <input type="number" min={0} max={8} value={decimalPlaces} onChange={event => setDecimalPlaces(Number(event.target.value))} className={inputClass} />
                  </label>
                  <label className="space-y-1 text-xs text-zinc-400">Tema
                    <select value={theme} onChange={event => setTheme(event.target.value)} className={inputClass}>
                      <option value="SYSTEM">Do sistema</option>
                      <option value="LIGHT">Claro</option>
                      <option value="DARK">Escuro</option>
                    </select>
                  </label>
                </div>
              </section>

              <section aria-labelledby="accessibility-title" className="space-y-4 border-b border-zinc-800 pb-8">
                <h2 id="accessibility-title" className="flex items-center gap-2 text-sm font-semibold">
                  <Accessibility size={16} className="text-cyan-400" />
                  Acessibilidade
                </h2>
                <div className="flex flex-wrap gap-5">
                  {[
                    ['Reduzir movimento', reducedMotion, setReducedMotion],
                    ['Contraste elevado', highContrast, setHighContrast],
                    ['Texto maior', largerText, setLargerText],
                  ].map(([label, checked, setter]) => (
                    <label key={String(label)} className="flex items-center gap-2 text-sm text-zinc-300">
                      <input
                        type="checkbox"
                        checked={Boolean(checked)}
                        onChange={event => (setter as (value: boolean) => void)(event.target.checked)}
                        className="h-4 w-4 accent-cyan-500"
                      />
                      {String(label)}
                    </label>
                  ))}
                </div>
                <button type="button" onClick={() => void saveAll()} disabled={saving} className={buttonClass}>
                  {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  Salvar preferências
                </button>
              </section>

              <section aria-labelledby="analytical-title" className="space-y-4 border-b border-zinc-800 pb-8">
                <div>
                  <h2 id="analytical-title" className="flex items-center gap-2 text-sm font-semibold">
                    <ShieldCheck size={16} className="text-cyan-400" />
                    Padrões, favoritos e referências
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500">Padrões analíticos só são usados com seu consentimento e sempre aparecem na resposta.</p>
                </div>
                {analyticalItems.length === 0 ? (
                  <p className="text-sm text-zinc-500">Nenhum padrão analítico ou favorito salvo.</p>
                ) : (
                  <div className="divide-y divide-zinc-800" data-testid="analytical-preference-list">
                    {analyticalItems.map(item => (
                      <div key={item.preference_id} className="grid gap-3 py-4 sm:grid-cols-[1fr_auto] sm:items-center">
                        <div>
                          <p className="text-sm font-semibold">{item.preference_key}</p>
                          <p className="mt-1 text-xs text-zinc-500">
                            {item.origin.source_label} · {item.status} · {item.risk}
                            {item.expires_at ? ` · expira em ${formatDate(item.expires_at)}` : ''}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {item.risk === 'VISIBLE_ANALYTICAL_DEFAULT' && (
                            <button type="button" onClick={() => void toggleConsent(item)} disabled={saving} className={buttonClass}>
                              <ShieldCheck size={14} />
                              {item.consent?.status === 'GRANTED' ? 'Revogar consentimento' : 'Conceder consentimento'}
                            </button>
                          )}
                          <button type="button" onClick={() => void setPreferenceStatus(item)} disabled={saving} className={buttonClass}>
                            <EyeOff size={14} />
                            {item.status === 'ACTIVE' ? 'Desativar' : 'Reativar'}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section aria-labelledby="privacy-title" className="space-y-4 pb-10">
                <div>
                  <h2 id="privacy-title" className="flex items-center gap-2 text-sm font-semibold">
                    <FileClock size={16} className="text-cyan-400" />
                    Privacidade e controle
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500">O perfil não armazena consultas, respostas, SQL ou dados empresariais.</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => void toggleProfile()} disabled={saving} className={buttonClass}>
                    <EyeOff size={14} />
                    {profile.status === 'ACTIVE' ? 'Desativar perfil' : 'Reativar perfil'}
                  </button>
                  <button type="button" onClick={() => void exportProfile()} disabled={saving || !capabilities?.export_enabled} className={buttonClass}>
                    <Download size={14} />
                    Exportar JSON
                  </button>
                  <button type="button" onClick={() => setDeleteOpen(true)} disabled={saving || !capabilities?.deletion_enabled} className={cn(buttonClass, 'border-red-500/30 text-red-300')}>
                    <Trash2 size={14} />
                    Solicitar exclusão
                  </button>
                </div>
              </section>
            </>
          ) : null}
        </div>
      </main>

      {deleteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="presentation">
          <div role="alertdialog" aria-modal="true" aria-labelledby="delete-title" className="w-full max-w-md rounded-md border border-zinc-700 bg-zinc-950 p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="delete-title" className="text-base font-semibold">Solicitar exclusão do perfil</h2>
                <p className="mt-2 text-sm text-zinc-400">A aplicação das preferências será interrompida. A auditoria mínima obrigatória será preservada.</p>
              </div>
              <button type="button" onClick={() => setDeleteOpen(false)} className="h-8 w-8 rounded-md text-zinc-400 hover:bg-zinc-800" aria-label="Fechar">
                <X size={16} className="mx-auto" />
              </button>
            </div>
            <label className="mt-4 block space-y-1 text-xs text-zinc-400">
              Motivo opcional
              <textarea value={deleteReason} onChange={event => setDeleteReason(event.target.value)} maxLength={500} className="min-h-24 w-full rounded-md border border-zinc-700 bg-zinc-900 p-3 text-sm text-zinc-100 outline-none focus:border-red-400" />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setDeleteOpen(false)} className={buttonClass}>Cancelar</button>
              <button type="button" onClick={() => void requestDeletion()} disabled={saving} className={cn(buttonClass, 'border-red-500/40 text-red-300')}>
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                Confirmar solicitação
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
