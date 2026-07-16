'use client'

/**
 * ETreemapChart — Gráfico de Árvore (Treemap) com Apache ECharts
 * Excelente para exibir tamanhos relativos de categorias e subcategorias de forma aninhada.
 */

import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import { useEChartsReflow } from './useEChartsReflow'
import type { EChartTooltipParam } from './echartsTypes'

interface TreemapItem {
  name: string
  value: number
  children?: TreemapItem[]
}

interface ETreemapChartProps {
  data: {
    children: TreemapItem[]
  }
  height?: number | string
}

export function ETreemapChart({ data, height = 340 }: ETreemapChartProps) {
  const { chartRef, containerRef } = useEChartsReflow()

  const option = useMemo(() => {
    return {
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 1200,
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(15,15,20,0.92)',
        borderColor: 'rgba(108,99,255,0.3)',
        borderWidth: 1,
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        extraCssText: 'border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,0.4);',
        formatter: (p: EChartTooltipParam) => {
          const value = typeof p.value === 'number' ? p.value : 0
          return `<div style="font-weight:600;margin-bottom:4px;color:#94a3b8">${p.name}</div>
          <div style="color:#fff;font-size:14px;font-weight:700">
            Participação: ${value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}
          </div>`
        }
      },
      series: [
        {
          name: 'Proporção',
          type: 'treemap',
          visibleMin: 300,
          data: data.children,
          leafDepth: 1,
          roam: 'move',
          breadcrumb: {
            show: true,
            height: 22,
            bottom: 0,
            itemStyle: {
              color: 'rgba(30,30,40,0.9)',
              borderColor: 'rgba(108,99,255,0.2)',
              textStyle: { color: '#94a3b8', fontSize: 10 }
            }
          },
          label: {
            show: true,
            formatter: '{b}\n{c}',
            fontSize: 11,
            color: '#fff'
          },
          itemStyle: {
            borderColor: 'rgba(15,15,20,0.8)',
            borderWidth: 2,
            gapWidth: 1
          },
          levels: [
            {
              itemStyle: {
                borderColor: '#1e1e24',
                borderWidth: 4,
                gapWidth: 4
              }
            },
            {
              color: ['#6C63FF', '#00D2D3', '#FF6B6B', '#FECA57', '#48DBFB', '#FF9FF3'],
              colorMappingBy: 'value',
              itemStyle: {
                gapWidth: 1
              }
            }
          ]
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
