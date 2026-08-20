'use client'

/**
 * EFunnelChart — Gráfico de Funil com Apache ECharts
 * Perfeito para demonstrar fluxos de conversão de funil de vendas.
 */

import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import { useEChartsReflow } from './useEChartsReflow'
import type { EChartTooltipParam } from './echartsTypes'

interface FunnelItem {
  name: string
  value: number
}

interface EFunnelChartProps {
  data: {
    values: FunnelItem[]
  }
  height?: number | string
}

const PALETTE = ['#6C63FF', '#00D2D3', '#FF6B6B', '#FECA57', '#48DBFB']

export function EFunnelChart({ data, height = 340 }: EFunnelChartProps) {
  const { chartRef, containerRef } = useEChartsReflow()

  const option = useMemo(() => {
    const sortedData = (data.values || []).map((item, idx) => ({
      name: item.name,
      value: item.value,
      itemStyle: {
        color: PALETTE[idx % PALETTE.length],
        borderRadius: 4
      }
    }))

    return {
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 1000,
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(15,15,20,0.92)',
        borderColor: 'rgba(108,99,255,0.3)',
        borderWidth: 1,
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        extraCssText: 'border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,0.4);',
        formatter: (p: EChartTooltipParam) => {
          return `<div style="font-weight:600;margin-bottom:4px;color:#94a3b8">${p.name}</div>
          <div style="color:#fff;font-size:14px;font-weight:700">
            Conversão: ${p.value}%
          </div>`
        }
      },
      legend: {
        data: sortedData.map(item => item.name),
        textStyle: { color: '#94a3b8', fontSize: 11 },
        icon: 'roundRect',
        bottom: 0,
        left: 'center'
      },
      series: [
        {
          name: 'Funil de Vendas',
          type: 'funnel',
          left: '10%',
          top: 24,
          bottom: 52,
          width: '80%',
          min: 0,
          max: 100,
          minSize: '0%',
          maxSize: '100%',
          sort: 'descending',
          gap: 3,
          label: {
            show: true,
            position: 'inside',
            formatter: '{b}: {c}%',
            color: '#fff',
            fontSize: 10
          },
          labelLine: {
            show: false
          },
          itemStyle: {
            borderColor: 'rgba(15,15,20,0.6)',
            borderWidth: 1
          },
          emphasis: {
            label: {
              fontSize: 12,
              fontWeight: 'bold'
            }
          },
          data: sortedData
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
