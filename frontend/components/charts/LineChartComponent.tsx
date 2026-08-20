'use client'

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCompact, shortenLabel } from '@/lib/utils'
import type { ChartDataLine } from '@/types/lumina'

// ── Custom Tooltip ─────────────────────────────────────────────

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: string
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="glass-strong rounded-xl px-4 py-3 shadow-lumina"
      style={{ border: '1px solid rgb(var(--accent) / 0.2)', minWidth: 170 }}
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

// ── Custom Dot ─────────────────────────────────────────────────

function CustomDot({ cx = 0, cy = 0, stroke = '#6C63FF', active = false }: {
  cx?: number; cy?: number; stroke?: string; active?: boolean
}) {
  if (!active) return null
  return (
    <circle
      cx={cx}
      cy={cy}
      r={5}
      fill={stroke}
      stroke="rgb(var(--bg-surface))"
      strokeWidth={2}
    />
  )
}

// ── LineChartComponent ────────────────────────────────────────

interface LineChartComponentProps {
  data: ChartDataLine
}

export function LineChartComponent({ data }: LineChartComponentProps) {
  const chartData = data.labels.map((label, i) => {
    const point: Record<string, string | number> = { label: shortenLabel(label) }
    data.datasets.forEach(ds => {
      point[ds.label] = ds.data[i] ?? 0
    })
    return point
  })

  // Check if we need a secondary Y axis
  const hasSecondaryAxis = data.datasets.some(ds => ds.yAxisID === 'y1')

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={chartData}
        margin={{ top: 8, right: hasSecondaryAxis ? 52 : 8, left: 0, bottom: 0 }}
      >
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
          yAxisId="y"
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 11, fill: 'rgb(var(--text-muted))' }}
          tickFormatter={formatCompact}
          width={52}
        />
        {hasSecondaryAxis && (
          <YAxis
            yAxisId="y1"
            orientation="right"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: 'rgb(var(--text-muted))' }}
            tickFormatter={v => `${v}%`}
            width={44}
          />
        )}
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11, paddingTop: 12, color: 'rgb(var(--text-muted))' }}
          iconType="circle"
          iconSize={8}
        />

        {data.datasets.map((ds) => (
          <Line
            key={ds.label}
            type="monotone"
            dataKey={ds.label}
            yAxisId={ds.yAxisID ?? 'y'}
            stroke={typeof ds.borderColor === 'string' ? ds.borderColor : '#6C63FF'}
            strokeWidth={2}
            strokeDasharray={ds.borderDash?.join(' ')}
            dot={false}
            activeDot={<CustomDot stroke={typeof ds.borderColor === 'string' ? ds.borderColor : '#6C63FF'} active />}
            isAnimationActive
            animationDuration={900}
            animationEasing="ease-out"
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
