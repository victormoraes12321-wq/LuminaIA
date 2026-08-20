'use client'

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'
import type { Theme, ThemeContextValue } from '@/types/lumina'

// ── Context ────────────────────────────────────────────────────

const ThemeContext = createContext<ThemeContextValue | null>(null)

const STORAGE_KEY = 'luminaai-theme'

function applyTheme(t: Theme) {
  document.documentElement.setAttribute('data-theme', t)
  document.documentElement.classList.toggle('dark', t === 'dark')
}

// ── Provider ───────────────────────────────────────────────────

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('dark')
  const [mounted, setMounted] = useState(false)

  // Hydration: read from localStorage or system preference
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Theme | null
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const initial: Theme = stored ?? (systemPrefersDark ? 'dark' : 'light')

    applyTheme(initial)
    queueMicrotask(() => {
      setTheme(initial)
      setMounted(true)
    })
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme(prev => {
      const next: Theme = prev === 'dark' ? 'light' : 'dark'
      localStorage.setItem(STORAGE_KEY, next)
      applyTheme(next)
      return next
    })
  }, [])

  const value: ThemeContextValue = {
    theme,
    toggleTheme,
    isDark: theme === 'dark',
  }

  // Prevent hydration flash: render invisible shell until theme is determined
  if (!mounted) {
    return (
      <div
        data-theme="dark"
        style={{
          visibility: 'hidden',
          background: 'rgb(9, 9, 11)',
          minHeight: '100dvh',
        }}
        aria-hidden
      />
    )
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

// ── Hook ───────────────────────────────────────────────────────

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) {
    throw new Error('useTheme must be used within <ThemeProvider>')
  }
  return ctx
}
