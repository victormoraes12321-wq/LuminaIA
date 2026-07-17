'use client'

/**
 * EPieChart - Gráfico de Rosca (Donut) Interativo com Apache ECharts
 * Recursos: rotação animada na entrada, legenda interativa clicável,
 * tooltip com percentual e valor absoluto, label no centro com total,
 * efeito de destaque ao hover, auto-reflow e auto-layout responsivo.
 */

import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import type { ChartDataPie } from '@/types/lumina'
import { useEChartsReflow } from './useEChartsReflow'
import type { EChartTooltipParam } from './echartsTypes'
import { tooltipCss, useEChartTheme } from './chartTheme'

const PALETTE = [
  '#6C63FF', '#00D2D3', '#FF6B6B', '#FECA57',
  '#48DBFB', '#FF9FF3', '#54A0FF', '#5F27CD',
  '#01CBC6', '#FF6348', '#FFBE76', '#7BED9F',
]

interface EPieChartProps {
  data: ChartDataPie
  height?: number | string
}

function formatCompact(value: number): string {
  if (isNaN(value) || !isFinite(value) || value <= 0) return '0'
  if (value >= 1000000000) return `${(value / 1000000000).toFixed(1)}B`
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
  return value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
}

export function EPieChart({ data, height = 320 }: EPieChartProps) {
  const { chartRef, containerRef, width } = useEChartsReflow()
  const theme = useEChartTheme()

  // 1. Agrupamento em Top 6 + Outros para evitar dezenas de fatias e sobreposição de legendas
  const processedData = useMemo(() => {
    const rawLabels = Array.isArray(data?.labels) ? data.labels : []
    const rawValues = Array.isArray(data?.values) ? data.values : []

    const items = rawLabels.map((label, i) => {
      const parsedValue = Number(rawValues[i])
      const val = Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : 0
      return {
        label: label || `Item ${i + 1}`,
        value: val,
        color: data?.colors?.[i]
      }
    }).filter((item) => item.value > 0)

    // Ordena decrescente por valor para pegar os maiores faturamentos/quantidades
    items.sort((a, b) => b.value - a.value)

    const maxFatias = 7
    if (items.length <= maxFatias) {
      return items
    }

    const topItems = items.slice(0, maxFatias - 1)
    const restItems = items.slice(maxFatias - 1)
    const restValue = restItems.reduce((sum, x) => sum + x.value, 0)

    return [
      ...topItems,
      {
        label: 'Outros',
        value: restValue,
        color: '#94a3b8'
      }
    ]
  }, [data])

  const option = useMemo(() => {
    const total = processedData.reduce((sum, item) => sum + item.value, 0)
    const isCompact = width < 550

    const pieData = processedData.map((item, i) => ({
      name: item.label,
      value: item.value,
      itemStyle: {
        color: item.color ?? PALETTE[i % PALETTE.length],
        borderRadius: 6,
        borderWidth: 2,
        borderColor: theme.itemBorder,
      },
    }))

    // Layout responsivo
    const legendConfig = isCompact
      ? {
          orient: 'horizontal' as const,
          bottom: 0,
          left: 'center' as const,
          textStyle: { color: theme.textMuted, fontSize: 10 },
          itemWidth: 8,
          itemHeight: 8,
        }
      : {
          orient: 'vertical' as const,
          right: 8,
          top: 'center' as const,
          textStyle: {
            color: theme.textMuted,
            fontSize: 11,
            rich: {
              a: { color: theme.textMuted, fontSize: 11 },
              b: { color: theme.textPrimary, fontSize: 11, fontWeight: 'bold', padding: [0, 0, 0, 4] },
            },
          },
          icon: 'circle',
          itemWidth: 10,
          itemHeight: 10,
          itemGap: 8,
          formatter: (name: string) => {
            const item = processedData.find(x => x.label === name)
            const val = item ? item.value : 0
            const pct = total > 0 ? (val / total) * 100 : 0
            return `{a|${name}} {b|${pct.toFixed(1)}%}`
          },
        }

    const pieCenter = isCompact ? ['50%', '42%'] : ['32%', '50%']
    const centerTextLeft = isCompact ? '50%' : '32%'
    const centerTextTop = isCompact ? '37%' : '45%'
    const totalTextTop = isCompact ? '47%' : '56%'

    return {
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 1200,
      animationEasing: 'cubicOut',
      tooltip: {
        trigger: 'item',
        backgroundColor: theme.tooltipBg,
        borderColor: theme.tooltipBorder,
        borderWidth: 1,
        textStyle: { color: theme.textSecondary, fontSize: 12 },
        extraCssText: tooltipCss(theme),
        formatter: (p: EChartTooltipParam) => {
          const value = typeof p.value === 'number' ? p.value : 0
          const pct = total > 0 ? (value / total) * 100 : 0
          return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
            <span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:${p.color}"></span>
            <span style="color:${theme.textMuted};font-weight:600">${p.name}</span>
          </div>
          <div style="color:${theme.textPrimary};font-size:16px;font-weight:700">${value.toLocaleString('pt-BR')}</div>
          <div style="color:${theme.textMuted};font-size:11px">Participação: ${pct.toFixed(1)}%</div>`
        },
      },
      legend: legendConfig,
      graphic: [
        {
          type: 'text',
          left: centerTextLeft,
          top: centerTextTop,
          style: {
            text: formatCompact(total),
            fill: theme.textPrimary,
            font: 'bold 18px Inter, sans-serif',
            textAlign: 'center',
          },
          z: 100,
        },
        {
          type: 'text',
          left: centerTextLeft,
          top: totalTextTop,
          style: {
            text: 'Total',
            fill: theme.textMuted,
            font: '11px Inter, sans-serif',
            textAlign: 'center',
          },
          z: 100,
        },
      ],
      series: [
        {
          name: 'Participação',
          type: 'pie',
          radius: isCompact ? ['40%', '65%'] : ['45%', '72%'],
          center: pieCenter,
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6 },
          label: {
            show: false,
            position: 'center',
          },
          emphasis: {
            label: { show: false },
            itemStyle: {
              shadowBlur: 20,
              shadowOffsetX: 0,
              shadowColor: 'rgba(108,99,255,0.5)',
              scale: true,
              scaleSize: 6,
            },
          },
          labelLine: { show: false },
          data: pieData,
        },
      ],
    }
  }, [processedData, theme, width])

  if (processedData.length === 0) {
    return (
      <div
        ref={containerRef}
        className="flex min-h-[260px] w-full items-center justify-center rounded-xl border px-6 text-center"
        style={{
          background: 'rgb(var(--bg-surface) / 0.72)',
          borderColor: 'rgb(var(--border) / 0.55)',
        }}
      >
        <div>
          <p className="text-sm font-semibold" style={{ color: 'rgb(var(--text-secondary))' }}>Sem dados numericos para este grafico</p>
          <p className="mt-1 text-xs" style={{ color: 'rgb(var(--text-muted))' }}>A consulta retornou, mas nao ha valores positivos para montar a distribuicao.</p>
        </div>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="w-full h-full min-h-[260px]">
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


