'use client'

/**
 * EHeatmapChart — Gráfico de Mapa de Calor com Apache ECharts
 * Perfeito para visualizar sazonalidade, distribuição horária/semanal ou matrizes categóricas.
 */

import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import { useEChartsReflow } from './useEChartsReflow'
import type { EChartTooltipParam } from './echartsTypes'

interface EHeatmapChartProps {
  data: {
    labels_x: string[]
    labels_y: string[]
    values: [number, number, number][] // [x_index, y_index, value]
    eixo_x_label?: string
    eixo_y_label?: string
  }
  height?: number | string
}

export function EHeatmapChart({ data, height = 340 }: EHeatmapChartProps) {
  const { chartRef, containerRef } = useEChartsReflow()

  const option = useMemo(() => {
    const values = data.values || []
    const rawValues = values.map(v => v[2])
    const maxVal = rawValues.length ? Math.max(...rawValues) : 100
    const minVal = rawValues.length ? Math.min(...rawValues) : 0

    return {
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 1000,
      tooltip: {
        position: 'top',
        backgroundColor: 'rgba(15,15,20,0.92)',
        borderColor: 'rgba(108,99,255,0.3)',
        borderWidth: 1,
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        extraCssText: 'border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,0.4);',
        formatter: (p: EChartTooltipParam) => {
          const point = p.data ?? []
          const xName = data.labels_x[point[0] ?? 0]
          const yName = data.labels_y[point[1] ?? 0]
          const val = point[2]
          return `<div style="font-weight:600;margin-bottom:4px;color:#94a3b8">${yName} ➔ ${xName}</div>
          <div style="color:#fff;font-size:14px;font-weight:700">
            Valor: ${typeof val === 'number' ? val.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) : val}
          </div>`
        }
      },
      grid: {
        top: 24,
        right: 16,
        bottom: 44,
        left: 64,
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: data.labels_x,
        splitArea: { show: true },
        axisLabel: { color: '#64748b', fontSize: 10, rotate: data.labels_x.length > 8 ? 30 : 0 },
        axisLine: { lineStyle: { color: 'rgba(100,116,139,0.2)' } }
      },
      yAxis: {
        type: 'category',
        data: data.labels_y,
        splitArea: { show: true },
        axisLabel: { color: '#64748b', fontSize: 10 },
        axisLine: { show: false }
      },
      visualMap: {
        min: minVal,
        max: maxVal,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        itemHeight: 12,
        textStyle: { color: '#94a3b8', fontSize: 10 },
        inRange: {
          color: ['rgba(108,99,255,0.1)', 'rgba(108,99,255,0.5)', '#6C63FF', '#00D2D3']
        }
      },
      series: [
        {
          name: 'Densidade',
          type: 'heatmap',
          data: values,
          label: {
            show: true,
            color: '#fff',
            fontSize: 9,
            formatter: (p: EChartTooltipParam) => {
              const val = p.data?.[2]
              return typeof val === 'number' && val >= 1000 ? `${(val / 1000).toFixed(0)}k` : String(val)
            }
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    }
  }, [data])

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
