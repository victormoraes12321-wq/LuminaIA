'use client'

/**
 * EAreaChart — Gráfico de Área "Onda Viva" com Apache ECharts
 * Recursos: gradiente animado, múltiplas séries empilhadas,
 * efeito de onda ao hover, tooltip estilo premium, auto-reflow e
 * tratamento avançado de labels.
 */

import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import type { ChartDataBar } from '@/types/lumina'
import type { EChartTooltipParam } from './echartsTypes'
import { useEChartsReflow } from './useEChartsReflow'
import { tooltipCss, useEChartTheme } from './chartTheme'

const SERIES_CONFIGS = [
  {
    color: '#6C63FF',
    areaTop: 'rgba(108,99,255,0.35)',
    areaBottom: 'rgba(108,99,255,0.03)',
  },
  {
    color: '#00D2D3',
    areaTop: 'rgba(0,210,211,0.25)',
    areaBottom: 'rgba(0,210,211,0.02)',
  },
  {
    color: '#FF6B6B',
    areaTop: 'rgba(255,107,107,0.20)',
    areaBottom: 'rgba(255,107,107,0.02)',
  },
  {
    color: '#FECA57',
    areaTop: 'rgba(254,202,87,0.20)',
    areaBottom: 'rgba(254,202,87,0.02)',
  },
]

interface EAreaChartProps {
  data: ChartDataBar
  height?: number | string
}

export function EAreaChart({ data, height = 340 }: EAreaChartProps) {
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
      const cfg = SERIES_CONFIGS[i % SERIES_CONFIGS.length]

      return {
        name: ds.label,
        type: 'line',
        data: ds.data,
        smooth: 0.5,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: cfg.color, width: 2 },
        itemStyle: { color: cfg.color, borderColor: theme.itemBorder, borderWidth: 2 },
        emphasis: {
          scale: true,
          focus: 'series',
          lineStyle: { width: 3 },
          itemStyle: { symbolSize: 8 },
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: cfg.areaTop },
              { offset: 1, color: cfg.areaBottom },
            ],
          },
          shadowColor: cfg.areaTop,
          shadowBlur: 10,
        },
      }
    })

    return {
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 1400,
      animationEasing: 'cubicOut',
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'line',
          lineStyle: { color: 'rgba(108,99,255,0.5)', type: 'dashed', width: 1.5 },
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
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color}"></span>
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
