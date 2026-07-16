'use client'

/**
 * EBarChart — Gráfico de Barras Premium com Apache ECharts
 * Recursos: animações nativas, gradiente por coluna, tooltip flutuante,
 * zoom por scroll, suporte a dark/light mode automático, auto-reflow,
 * e tratamento avançado de colisão e rotação de labels.
 */

import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import type { ChartDataBar } from '@/types/lumina'
import { getEChartColor } from './echartsTypes'
import type { EChartTooltipParam } from './echartsTypes'
import { useEChartsReflow } from './useEChartsReflow'
import { tooltipCss, useEChartTheme } from './chartTheme'

// ── Paleta de cores premium LuminaAI ──────────────────────────
const PALETTE = [
  ['#6C63FF', 'rgba(108,99,255,0.15)'],
  ['#00D2D3', 'rgba(0,210,211,0.15)'],
  ['#FF6B6B', 'rgba(255,107,107,0.15)'],
  ['#FECA57', 'rgba(254,202,87,0.15)'],
  ['#48DBFB', 'rgba(72,219,251,0.15)'],
  ['#FF9FF3', 'rgba(255,159,243,0.15)'],
]

interface EBarChartProps {
  data: ChartDataBar
  height?: number | string
}

export function EBarChart({ data, height = 340 }: EBarChartProps) {
  const { chartRef, containerRef, width } = useEChartsReflow()
  const theme = useEChartTheme()

  const option = useMemo(() => {
    // Breakpoint de compactação (notebook estreito ou coluna dividida)
    const isCompact = width < 550
    const xAxisLabelRotate = data.labels.length > 6 ? (isCompact ? 45 : 30) : 0
    const xAxisLabelInterval = isCompact ? 'auto' : 0

    // Calcula padding inferior com base no comprimento do maior label para evitar corte
    const maxLabelLength = Math.max(...data.labels.map(l => l ? String(l).length : 0), 0)
    const bottomPadding = xAxisLabelRotate > 0
      ? Math.min(110, 36 + maxLabelLength * 4.5)
      : (data.datasets.length > 1 ? 48 : 32)

    const series = data.datasets.map((ds, i) => {
      const [color] = PALETTE[i % PALETTE.length]
      const isLine = ds.type === 'line'

      if (isLine) {
        return {
          name: ds.label,
          type: 'line',
          data: ds.data,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { color, width: 2 },
          itemStyle: { color },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: color + '44' },
                { offset: 1, color: color + '00' },
              ],
            },
          },
        }
      }

      return {
        name: ds.label,
        type: 'bar',
        data: ds.data,
        barMaxWidth: 48,
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color },
              { offset: 1, color: color + '88' },
            ],
          },
          borderRadius: [6, 6, 0, 0],
        },
        emphasis: {
          itemStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color },
                { offset: 1, color: color + 'CC' },
              ],
            },
          },
        },
      }
    })

    return {
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 900,
      animationEasing: 'cubicOut',
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
          shadowStyle: { color: 'rgba(108,99,255,0.06)' },
        },
        backgroundColor: theme.tooltipBg,
        borderColor: theme.tooltipBorder,
        borderWidth: 1,
        textStyle: { color: theme.textSecondary, fontSize: 12 },
        extraCssText: tooltipCss(theme),
        formatter: (params: EChartTooltipParam[]) => {
          if (!params || params.length === 0) return ''
          let html = `<div style="font-weight:600;margin-bottom:6px;color:${theme.textMuted}">${params[0]?.axisValue || ''}</div>`
          params.forEach((p) => {
            if (!p) return
            const val = p.value
            html += `<div style="display:flex;align-items:center;gap:8px;margin:3px 0">
              <span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:${getEChartColor(p.color)}"></span>
              <span style="color:${theme.textSecondary}">${p.seriesName || ''}</span>
              <span style="font-weight:700;color:${theme.textPrimary};margin-left:auto;padding-left:12px">
                ${typeof val === 'number' ? val.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) : (val ?? '')}
              </span>
            </div>`
          })
          return html
        },
      },
      legend: {
        data: data.datasets.map(ds => ds.label),
        textStyle: { color: theme.textMuted, fontSize: 11 },
        icon: 'roundRect',
        itemWidth: 12,
        itemHeight: 8,
        bottom: 0,
      },
      grid: {
        top: 24,
        right: 16,
        bottom: bottomPadding,
        left: 48,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: data.labels,
        axisLabel: {
          color: theme.axis,
          fontSize: 10,
          rotate: xAxisLabelRotate,
          interval: xAxisLabelInterval,
          hideOverlap: true,
          formatter: (val: string) => {
            if (val && val.length > 15) {
              return val.substring(0, 12) + '...'
            }
            return val
          }
        },
        axisLine: { lineStyle: { color: theme.axisLine } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: theme.axis,
          fontSize: 11,
          formatter: (v: number) =>
            v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M`
            : v >= 1_000 ? `${(v / 1_000).toFixed(0)}k`
            : String(v),
        },
        splitLine: { lineStyle: { color: theme.grid, type: 'dashed' } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      dataZoom: data.labels.length > 12 ? [
        { type: 'inside', start: 0, end: 100 },
      ] : undefined,
      series,
    }
  }, [data, theme, width])

  return (
    <div ref={containerRef} className="w-full h-full min-h-[300px]">
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height, width: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge
      />
    </div>
  )
}
