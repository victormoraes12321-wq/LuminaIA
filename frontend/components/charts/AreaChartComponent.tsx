'use client'

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCompact, shortenLabel } from '@/lib/utils'
import type { ChartDataArea } from '@/types/lumina'

// ── Custom Tooltip ─────────────────────────────────────────────

interface AreaTooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: string
}

function AreaTooltip({ active, payload, label }: AreaTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="glass-strong rounded-xl px-4 py-3 shadow-lumina"
      style={{ border: '1px solid rgb(var(--accent) / 0.2)', minWidth: 165 }}
    >
      <p className="text-xs font-semibold mb-2" style={{ color: 'rgb(var(--text-muted))' }}>
        {label}
      </p>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center justify-between gap-4 py-0.5">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
            <span className="text-xs" style={{ color: 'rgb(var(--text-secondary))' }}>
              {p.name}
            </span>
          </div>
          <span className="text-xs font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
            {formatCompact(p.value)}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── AreaChartComponent ─────────────────────────────────────────

interface AreaChartComponentProps {
  data: ChartDataArea
}

// Palette for gradient fills
const AREA_PALETTE = [
  { stroke: '#6C63FF' },
  { stroke: '#00D2D3' },
  { stroke: '#FF6B6B' },
  { stroke: '#FECA57' },
]

export function AreaChartComponent({ data }: AreaChartComponentProps) {
  const chartData = data.labels.map((label, i) => {
    const point: Record<string, string | number> = { label: shortenLabel(label) }
    data.datasets.forEach(ds => {
      point[ds.label] = ds.data[i] ?? 0
    })
    return point
  })

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart
        data={chartData}
        margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
      >
        {/*
          SVG <defs> must be rendered as raw SVG elements inside the chart.
          Recharts forwards children of AreaChart to the underlying SVG,
          so plain JSX SVG elements work here.
        */}
        <defs>
          {data.datasets.map((ds, i) => {
            const palette = AREA_PALETTE[i % AREA_PALETTE.length]
            return (
              <linearGradient
                key={`grad-${String(ds.label)}`}
                id={`area-grad-${i}`}
                x1="0" y1="0" x2="0" y2="1"
              >
                <stop offset="0%" stopColor={palette.stroke} stopOpacity={0.35} />
                <stop offset="95%" stopColor={palette.stroke} stopOpacity={0.02} />
              </linearGradient>
            )
          })}
        </defs>

        <CartesianGrid
          strokeDasharray="3 3"
          vertical={false}
          stroke="rgb(var(--border) / 0.35)"
        />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 11, fill: 'rgb(var(--text-muted))' }}
          dy={6}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 11, fill: 'rgb(var(--text-muted))' }}
          tickFormatter={formatCompact}
          width={52}
        />
        <Tooltip content={<AreaTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11, paddingTop: 12, color: 'rgb(var(--text-muted))' }}
          iconType="circle"
          iconSize={8}
        />

        {data.datasets.map((ds, i) => {
          const palette = AREA_PALETTE[i % AREA_PALETTE.length]
          return (
            <Area
              key={String(ds.label)}
              type="monotone"
              dataKey={String(ds.label)}
              stroke={palette.stroke}
              strokeWidth={2}
              fill={`url(#area-grad-${i})`}
              dot={false}
              activeDot={{ r: 5, fill: palette.stroke, strokeWidth: 0 }}
              isAnimationActive
              animationDuration={1000}
              animationEasing="ease-out"
            />
          )
        })}
      </AreaChart>
    </ResponsiveContainer>
  )
}
