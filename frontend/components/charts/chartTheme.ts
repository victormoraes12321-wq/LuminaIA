'use client'

import { useMemo } from 'react'
import { useTheme } from '@/context/ThemeContext'

export interface EChartTheme {
  isDark: boolean
  textPrimary: string
  textSecondary: string
  textMuted: string
  axis: string
  grid: string
  axisLine: string
  tooltipBg: string
  tooltipBorder: string
  tooltipShadow: string
  itemBorder: string
  subtleSurface: string
}

export function useEChartTheme(): EChartTheme {
  const { isDark } = useTheme()

  return useMemo(() => {
    if (isDark) {
      return {
        isDark,
        textPrimary: '#f8fafc',
        textSecondary: '#cbd5e1',
        textMuted: '#94a3b8',
        axis: '#94a3b8',
        grid: 'rgba(148,163,184,0.14)',
        axisLine: 'rgba(148,163,184,0.22)',
        tooltipBg: 'rgba(15,15,20,0.94)',
        tooltipBorder: 'rgba(108,99,255,0.35)',
        tooltipShadow: '0 8px 32px rgba(0,0,0,0.45)',
        itemBorder: 'rgba(15,15,20,0.78)',
        subtleSurface: 'rgba(255,255,255,0.04)',
      }
    }

    return {
      isDark,
      textPrimary: '#0f172a',
      textSecondary: '#334155',
      textMuted: '#475569',
      axis: '#334155',
      grid: 'rgba(71,85,105,0.22)',
      axisLine: 'rgba(71,85,105,0.32)',
      tooltipBg: 'rgba(255,255,255,0.98)',
      tooltipBorder: 'rgba(148,163,184,0.65)',
      tooltipShadow: '0 12px 32px rgba(15,23,42,0.16)',
      itemBorder: 'rgba(255,255,255,0.86)',
      subtleSurface: 'rgba(15,23,42,0.04)',
    }
  }, [isDark])
}

export function tooltipCss(theme: EChartTheme): string {
  return `border-radius:10px;box-shadow:${theme.tooltipShadow};`
}
