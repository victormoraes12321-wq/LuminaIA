'use client'

import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { useEChartsReflow } from '@/components/charts/useEChartsReflow'
import { tooltipCss, useEChartTheme } from '@/components/charts/chartTheme'
import { toChartNumber } from './comparisonFormatters'
import type {
  ComparisonPresentationModel,
  ComparisonVisualizationPresentation,
} from './comparisonPresentationTypes'

const SERIES_COLORS = ['#625bf6', '#0891b2', '#d97706', '#db2777', '#4f46e5', '#0f766e']

interface ComparisonChartProps {
  model: ComparisonPresentationModel
  visualization: ComparisonVisualizationPresentation
}

function chartDescription(model: ComparisonPresentationModel): string {
  const operands = model.operands
    .slice(0, 6)
    .map(item => `${item.label}: ${item.formattedValue}`)
    .join('; ')
  const direction = model.calculations.find(item => item.calculation === 'DIRECTION')
    ?? model.calculations.find(item => item.direction !== 'NOT_APPLICABLE')
  const suffix = direction ? ` Direcao informada: ${direction.direction}.` : ''
  const warning = model.partial || model.truncated
    ? ' Resultado parcial ou truncado.'
    : ''
  return `${model.comparisonKind}. ${operands}.${suffix}${warning}`
}

export function ComparisonChart({ model, visualization }: ComparisonChartProps) {
  const { chartRef, containerRef, width } = useEChartsReflow()
  const theme = useEChartTheme()
  const description = chartDescription(model)

  const option = useMemo<EChartsOption>(() => {
    const labels = model.operands.map(item => item.shortLabel)
    const values = model.operands.map(item => toChartNumber(item.rawValue))
    const longLabels = labels.some(label => label.length > 18)
    const horizontal = visualization.kind === 'BAR' && (longLabels || width < 620)
    const base: EChartsOption = {
      backgroundColor: 'transparent',
      animationDuration: 500,
      textStyle: { color: theme.textSecondary },
      tooltip: {
        trigger: visualization.kind === 'PIE' ? 'item' as const : 'axis' as const,
        backgroundColor: theme.tooltipBg,
        borderColor: theme.tooltipBorder,
        borderWidth: 1,
        textStyle: { color: theme.textSecondary, fontSize: 12 },
        extraCssText: tooltipCss(theme),
      },
      legend: {
        type: 'scroll',
        bottom: 0,
        textStyle: { color: theme.textMuted, fontSize: 11 },
      },
    }

    if (visualization.kind === 'PIE') {
      const shares = model.calculations.filter(
        item => item.calculation === 'SHARE' && item.rawResult !== null,
      )
      return {
        ...base,
        series: [{
          name: visualization.title,
          type: 'pie',
          radius: ['42%', '70%'],
          center: ['50%', '45%'],
          avoidLabelOverlap: true,
          data: shares.flatMap((item, index) => {
            const value = toChartNumber(item.rawResult)
            if (value === null) return []
            return [{
              name: model.operands.find(
                operand => operand.operandId === item.targetOperandId,
              )?.shortLabel ?? item.targetOperandId,
              value,
              itemStyle: { color: SERIES_COLORS[index % SERIES_COLORS.length] },
            }]
          }),
          label: {
            color: theme.textSecondary,
            formatter: '{b}: {d}%',
          },
        }],
      }
    }

    const isLine = visualization.kind === 'LINE' || visualization.kind === 'AREA'
    const series: EChartsOption['series'] = isLine
      ? [{
        name: model.operands[0]?.metricLabel ?? 'Valor',
        type: 'line',
        data: values,
        connectNulls: false,
        smooth: false,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { color: SERIES_COLORS[0], width: 2.5 },
        itemStyle: { color: SERIES_COLORS[0] },
        areaStyle: visualization.kind === 'AREA'
          ? { color: 'rgba(98,91,246,0.16)' }
          : undefined,
      }]
      : [{
        name: model.operands[0]?.metricLabel ?? 'Valor',
        type: 'bar',
        data: values,
        barMaxWidth: 44,
        itemStyle: {
          color: SERIES_COLORS[0],
          borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
        },
      }]

    const categoryAxis = {
      type: 'category' as const,
      data: labels,
      axisLabel: {
        color: theme.axis,
        fontSize: 10,
        hideOverlap: true,
        overflow: 'truncate' as const,
        width: horizontal ? 140 : 90,
        rotate: !horizontal && labels.length > 6 ? 30 : 0,
      },
      axisLine: { lineStyle: { color: theme.axisLine } },
      axisTick: { show: false },
    }
    const valueAxis = {
      type: 'value' as const,
      scale: false,
      axisLabel: { color: theme.axis, fontSize: 10 },
      splitLine: { lineStyle: { color: theme.grid, type: 'dashed' as const } },
    }
    return {
      ...base,
      grid: {
        top: 20,
        right: 20,
        bottom: labels.length > 6 && !horizontal ? 76 : 46,
        left: horizontal ? 150 : 58,
        containLabel: true,
      },
      xAxis: horizontal ? valueAxis : categoryAxis,
      yAxis: horizontal ? categoryAxis : valueAxis,
      dataZoom: labels.length > 12
        ? [{ type: 'inside', start: 0, end: Math.max(20, 1200 / labels.length) }]
        : undefined,
      series,
    }
  }, [model, theme, visualization, width])

  return (
    <figure
      ref={containerRef}
      className="m-0 min-h-[320px] w-full"
      role="img"
      aria-label={description}
      data-testid={`comparison-chart-${visualization.kind.toLowerCase()}`}
    >
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height: 340, width: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge
        aria-hidden="true"
      />
      <figcaption className="sr-only">{description}</figcaption>
    </figure>
  )
}
