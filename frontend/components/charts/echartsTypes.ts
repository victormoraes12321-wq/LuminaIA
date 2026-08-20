export type EChartColor =
  | string
  | {
      colorStops?: Array<{ color?: string }>
    }

export interface EChartTooltipParam {
  axisValue?: string | number
  seriesName?: string
  name?: string
  color?: EChartColor
  value?: number | number[]
  data?: number[]
}

export function getEChartColor(color: EChartColor | undefined): string {
  if (!color) return '#6C63FF'
  if (typeof color === 'string') return color
  return color.colorStops?.[0]?.color ?? '#6C63FF'
}
