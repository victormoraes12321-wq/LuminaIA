import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// ── CSS Class Merging ──────────────────────────────────────────

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

// ── Number Formatters ──────────────────────────────────────────

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  }).format(value)
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('pt-BR').format(value)
}

export function formatPercent(value: number, showSign = true): string {
  const sign = showSign && value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

export function formatCompact(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  }).format(value)
}

// ── Date Formatters ────────────────────────────────────────────

export function formatDate(dateStr: string): string {
  try {
    return new Intl.DateTimeFormat('pt-BR').format(new Date(dateStr))
  } catch {
    return dateStr
  }
}

export function formatRelativeTime(date: Date): string {
  const now = Date.now()
  const diff = now - date.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (seconds < 60) return 'agora mesmo'
  if (minutes < 60) return `há ${minutes} min`
  if (hours < 24) return `há ${hours}h`
  return formatDate(date.toISOString())
}

// ── String Utils ───────────────────────────────────────────────

export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str
  return `${str.slice(0, maxLength - 1)}…`
}

export function generateId(): string {
  return Math.random().toString(36).slice(2, 9) + Date.now().toString(36)
}

// ── Color Utils ────────────────────────────────────────────────

export function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// ── Chart Label Shortener ──────────────────────────────────────

export function shortenLabel(label: string, maxChars = 8): string {
  if (label.length <= maxChars) return label
  const parts = label.split('/')
  if (parts.length === 2) return parts[0]
  return label.slice(0, maxChars)
}

// ── API Utils ──────────────────────────────────────────────────

export function getApiBase(): string {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    const configuredUrl = process.env.NEXT_PUBLIC_API_URL
    const isLanAccess = hostname && !['localhost', '127.0.0.1', '::1'].includes(hostname)
    const isLoopbackAccess = ['localhost', '127.0.0.1', '::1', '[::1]'].includes(hostname)

    if (configuredUrl && isLoopbackAccess) {
      try {
        const parsed = new URL(configuredUrl)
        const configuredHost = parsed.hostname
        const configuredIsLoopback = ['localhost', '127.0.0.1', '::1', '[::1]'].includes(configuredHost)

        if (configuredIsLoopback && configuredHost !== hostname) {
          parsed.hostname = hostname
          return parsed.toString().replace(/\/$/, '')
        }
      } catch {
        // Fall through to the regular configured URL handling.
      }
    }

    if (configuredUrl && !(isLanAccess && /\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(configuredUrl))) {
      return configuredUrl
    }

    if (hostname) {
      return `http://${hostname}:8000`
    }
  }
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL
  }
  return 'http://127.0.0.1:8000'
}
