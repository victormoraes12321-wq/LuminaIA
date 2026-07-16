'use client'

/**
 * ELineChart — Gráfico de Linhas Animado com Apache ECharts
 * Recursos: linha suave com área preenchida, gradiente, zoom interativo,
 * tooltip flutuante, suporte a múltiplos eixos Y, auto-reflow e
 * tratamento avançado de labels.
 */

import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import type { ChartDataBar } from '@/types/lumina'
import type { EChartTooltipParam } from './echartsTypes'
import { useEChartsReflow } from './useEChartsReflow'
import { tooltipCss, useEChartTheme } from './chartTheme'

const PALETTE = [
  '#6C63FF',
  '#00D2D3',
  '#FF6B6B',
  '#FECA57',
  '#48DBFB',
]

const AREA_COLORS = [
  ['rgba(108,99,255,0.25)', 'rgba(108,99,255,0.00)'],
  ['rgba(0,210,211,0.20)', 'rgba(0,210,211,0.00)'],
  ['rgba(255,107,107,0.20)', 'rgba(255,107,107,0.00)'],
  ['rgba(254,202,87,0.20)', 'rgba(254,202,87,0.00)'],
]

interface ELineChartProps {
  data: ChartDataBar
  height?: number | string
  filled?: boolean
}

export function ELineChart({ data, height = 340, filled = false }: ELineChartProps) {
  const { chartRef, containerRef, width } = useEChartsReflow()
  const theme = useEChartTheme()

  const option = useMemo(() => {
    // Breakpoint de compactação
    const isCompact = width < 550
    const xAxisLabelRotate = data.labels.length > 6 ? (isCompact ? 45 : 30) : 0
    const xAxisLabelInterval = isCompact ? 'auto' : 0

    // Calcula padding inferior dinamicamente
    const maxLabelLength = Math.max(...data.labels.map(l => l ? String(l).length : 0), 0)
    const bottomPadding = xAxisLabelRotate > 0
      ? Math.min(110, 36 + maxLabelLength * 4.5)
      : (data.datasets.length > 1 ? 48 : 28)

    const series = data.datasets.map((ds, i) => {
      const color = PALETTE[i % PALETTE.length]
      const [areaTop, areaBottom] = AREA_COLORS[i % AREA_COLORS.length]

      return {
        name: ds.label,
        type: 'line',
        data: ds.data,
        smooth: 0.4,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { color, width: 2.5 },
        itemStyle: { color, borderColor: theme.itemBorder, borderWidth: 1.5 },
        emphasis: {
          scale: true,
          focus: 'series',
          lineStyle: { width: 3 },
        },
        areaStyle: ds.fill || filled ? {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: areaTop },
              { offset: 1, color: areaBottom },
            ],
          },
        } : undefined,
      }
    })

    return {
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 1200,
      animationEasing: 'cubicOut',
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          crossStyle: { color: 'rgba(108,99,255,0.4)', type: 'dashed' },
          lineStyle: { color: 'rgba(108,99,255,0.4)', type: 'dashed' },
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
              <span style="display:inline-block;width:12px;height:3px;border-radius:2px;background:${p.color}"></span>
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
        itemWidth: 16,
        itemHeight: 3,
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
        boundaryGap: false,
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
  }, [data, filled, theme, width])

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
