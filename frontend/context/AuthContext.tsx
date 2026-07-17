'use client'

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ApiErrorResponse } from '@/types/lumina'
import { COOKIE_SESSION_TOKEN } from '@/lib/authSession'
import { getApiBase } from '@/lib/utils'
import { repairTextEncoding } from '@/lib/textEncoding'

export interface UserSession {
  id: string
  nome: string
  email: string
  role: 'ADMIN' | 'GESTOR' | 'CONSULTA'
  tenant_id: string
  must_change_password: boolean
}

interface AuthContextType {
  user: UserSession | null
  token: string | null
  loading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}

interface JwtPayload {
  sub: string
  tenant_id: string
  role: 'ADMIN' | 'GESTOR' | 'CONSULTA'
  must_change_password: boolean
  nome?: string
  email?: string
  exp: number
}

interface LoginPayload {
  access_token: string
  must_change_password: boolean
}

function decodeJwt(token: string): JwtPayload | null {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return null
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(char => '%' + ('00' + char.charCodeAt(0).toString(16)).slice(-2))
        .join(''),
    )
    return JSON.parse(jsonPayload) as JwtPayload
  } catch {
    return null
  }
}

function sessionFromPayload(payload: JwtPayload, fallbackEmail = ''): UserSession {
  return {
    id: payload.sub,
    nome: payload.nome ?? 'Usuario Lumina',
    email: payload.email ?? fallbackEmail,
    role: payload.role,
    tenant_id: payload.tenant_id,
    must_change_password: payload.must_change_password,
  }
}

const AuthContext = createContext<AuthContextType | null>(null)

function isProtectedPath(): boolean {
  if (typeof window === 'undefined') return false
  return window.location.pathname.startsWith('/dashboard') || window.location.pathname === '/auth/first-access'
}

function redirectToLogin(reason = 'session_expired'): void {
  if (typeof window === 'undefined' || window.location.pathname === '/login') return
  const loginUrl = new URL('/login', window.location.origin)
  loginUrl.searchParams.set('reason', reason)
  loginUrl.searchParams.set('from', `${window.location.pathname}${window.location.search}`)
  window.location.replace(loginUrl.toString())
}

async function clearAuthCookieRequest(url: string): Promise<void> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 2500)
  try {
    await fetch(url, {
      method: 'POST',
      credentials: 'include',
      cache: 'no-store',
      signal: controller.signal,
    })
  } catch {
    // A segunda rota de limpeza cobre cenarios em que backend ou frontend estejam indisponiveis.
  } finally {
    window.clearTimeout(timeoutId)
  }
}

async function clearAuthCookie(): Promise<void> {
  await Promise.allSettled([
    clearAuthCookieRequest(`${getApiBase()}/api/v1/auth/logout`),
    clearAuthCookieRequest('/api/auth/clear-session'),
  ])
}

function buildAuthFetchErrorMessage(err: unknown): string {
  if (err instanceof TypeError && /fetch/i.test(err.message)) {
    return (
      `Não consegui conectar ao backend em ${getApiBase()}. ` +
      'Verifique se o LuminaAI foi iniciado pelo script start-luminaai.ps1.'
    )
  }
  return err instanceof Error ? repairTextEncoding(err.message) : 'Erro ao realizar login.'
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserSession | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function expireClientSession(reason = 'session_expired') {
      setUser(null)
      setToken(null)
      setError(null)
      await clearAuthCookie()
      if (active && isProtectedPath()) {
        redirectToLogin(reason)
      }
    }

    async function hydrateSession() {
      try {
        const res = await fetch(`${getApiBase()}/api/v1/auth/session`, {
          credentials: 'include',
          cache: 'no-store',
        })
        if (!active) return
        if (res.ok) {
          const session = await res.json() as UserSession
          setUser(session)
          setToken(COOKIE_SESSION_TOKEN)
        } else {
          await expireClientSession('invalid_session')
        }
      } catch {
        if (active) {
          await expireClientSession('session_check_failed')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void hydrateSession()
    return () => {
      active = false
    }
  }, [])

  const logout = useCallback(async () => {
    setLoading(true)
    await clearAuthCookie()
    setToken(null)
    setUser(null)
    setError(null)
    if (typeof window !== 'undefined') {
      window.location.replace('/login')
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    setError(null)
    setLoading(true)
    try {
      const res = await fetch(`${getApiBase()}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Lumina-Cookie-Auth': '1',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      })

      if (!res.ok) {
        const errData: ApiErrorResponse = await res.json().catch(() => ({
          success: false,
          error: { code: res.status, message: 'Falha na autenticação' },
        }))
        throw new Error(repairTextEncoding(errData.error?.message ?? 'Credenciais inválidas.'))
      }

      const data = await res.json() as LoginPayload
      const payload = decodeJwt(data.access_token)
      if (!payload) {
        throw new Error('Token JWT inválido retornado pelo servidor.')
      }

      const newSession = sessionFromPayload(payload, email)
      setToken(data.access_token)
      setUser(newSession)

      window.location.href = newSession.must_change_password ? '/auth/first-access' : '/dashboard'
    } catch (err) {
      setError(buildAuthFetchErrorMessage(err))
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const changePassword = useCallback(async (oldPassword: string, newPassword: string) => {
    setError(null)
    setLoading(true)
    try {
      if (!token) {
        throw new Error('Usuario nao autenticado.')
      }

      const res = await fetch(`${getApiBase()}/api/v1/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        credentials: 'include',
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({
          error: { message: 'Erro ao alterar a senha' },
        }))
        throw new Error(repairTextEncoding(errData.error?.message ?? 'Erro ao alterar a senha.'))
      }
    } catch (err) {
      setError(err instanceof Error ? repairTextEncoding(err.message) : 'Erro ao alterar a senha.')
      throw err
    } finally {
      setLoading(false)
    }
  }, [token])

  const clearError = useCallback(() => setError(null), [])

  const value: AuthContextType = {
    user,
    token,
    loading,
    error,
    login,
    changePassword,
    logout,
    clearError,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
