'use client'

/**
 * EScatterChart — Gráfico de Dispersão com Agrupamento por Segmento
 * Recursos: bolhas coloridas por segmento, tooltip rico,
 * zoom/pan interativo, legenda clicável para toggle de séries,
 * auto-reflow e auto-layout responsivo.
 */

import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import type { ChartDataScatter } from '@/types/lumina'
import { useEChartsReflow } from './useEChartsReflow'
import type { EChartTooltipParam } from './echartsTypes'

const PALETTE = [
  '#6C63FF', '#00D2D3', '#FF6B6B', '#FECA57', '#48DBFB',
]

interface EScatterChartProps {
  data: ChartDataScatter
  height?: number | string
}

export function EScatterChart({ data, height = 340 }: EScatterChartProps) {
  const { chartRef, containerRef, width } = useEChartsReflow()

  const option = useMemo(() => {
    const isCompact = width < 550
    const bottomPadding = isCompact ? 64 : 52
    const leftPadding = isCompact ? 48 : 56

    const series = data.datasets.map((ds, i) => ({
      name: ds.label,
      type: 'scatter',
      symbolSize: isCompact ? 8 : 10,
      data: ds.data.map(p => [p.x, p.y]),
      itemStyle: {
        color: PALETTE[i % PALETTE.length],
        opacity: 0.8,
        borderColor: 'rgba(255,255,255,0.2)',
        borderWidth: 1,
      },
      emphasis: {
        itemStyle: {
          opacity: 1,
          shadowBlur: 16,
          shadowColor: PALETTE[i % PALETTE.length] + '80',
          scale: true,
        },
      },
    }))

    return {
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 1000,
      animationEasing: 'cubicOut',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(15,15,20,0.92)',
        borderColor: 'rgba(108,99,255,0.3)',
        borderWidth: 1,
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        extraCssText: 'border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,0.4);',
        formatter: (p: EChartTooltipParam) => {
          const value = Array.isArray(p.value) ? p.value : []
          return `<div style="color:#94a3b8;font-weight:600;margin-bottom:6px">${p.seriesName}</div>
          <div style="color:#cbd5e1">${data.eixo_x_label ?? 'X'}: <b style="color:#fff">${value[0]?.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}</b></div>
          <div style="color:#cbd5e1">${data.eixo_y_label ?? 'Y'}: <b style="color:#fff">${value[1]?.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}</b></div>`
        },
      },
      legend: {
        data: data.datasets.map(ds => ds.label),
        textStyle: { color: '#94a3b8', fontSize: 11 },
        icon: 'circle',
        itemWidth: 10,
        itemHeight: 10,
        bottom: 0,
      },
      grid: {
        top: 24,
        right: 24,
        bottom: bottomPadding,
        left: leftPadding,
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: isCompact ? undefined : data.eixo_x_label,
        nameLocation: 'middle',
        nameGap: 28,
        nameTextStyle: { color: '#64748b', fontSize: 11 },
        axisLabel: { color: '#64748b', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(100,116,139,0.1)', type: 'dashed' } },
        axisLine: { lineStyle: { color: 'rgba(100,116,139,0.2)' } },
      },
      yAxis: {
        type: 'value',
        name: isCompact ? undefined : data.eixo_y_label,
        nameLocation: 'middle',
        nameGap: 40,
        nameRotate: 90,
        nameTextStyle: { color: '#64748b', fontSize: 11 },
        axisLabel: { color: '#64748b', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(100,116,139,0.1)', type: 'dashed' } },
        axisLine: { show: false },
      },
      dataZoom: [
        { type: 'inside', xAxisIndex: 0 },
        { type: 'inside', yAxisIndex: 0 },
      ],
      series,
    }
  }, [data, width])

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
