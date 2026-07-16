'use client'

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCompact, shortenLabel } from '@/lib/utils'
import type { ChartDataBar } from '@/types/lumina'

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
      className="glass-strong rounded-xl px-4 py-3 text-sm shadow-lumina"
      style={{ border: '1px solid rgb(var(--accent) / 0.2)', minWidth: 160 }}
    >
      <p className="font-semibold mb-2 text-xs" style={{ color: 'rgb(var(--text-muted))' }}>
        {label}
      </p>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: p.color }}
            />
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

// ── BarChartComponent ─────────────────────────────────────────

interface BarChartComponentProps {
  data: ChartDataBar
}

export function BarChartComponent({ data }: BarChartComponentProps) {
  // Merge labels + dataset values into Recharts format
  const chartData = data.labels.map((label, i) => {
    const point: Record<string, string | number> = {
      label: shortenLabel(label),
      fullLabel: label,
    }
    data.datasets.forEach(ds => {
      point[ds.label] = ds.data[i] ?? 0
    })
    return point
  })

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={chartData}
        margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
        barCategoryGap="28%"
        barGap={4}
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
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 11, fill: 'rgb(var(--text-muted))' }}
          tickFormatter={formatCompact}
          width={52}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgb(var(--accent) / 0.06)', radius: 4 }} />
        <Legend
          wrapperStyle={{ fontSize: 11, paddingTop: 12, color: 'rgb(var(--text-muted))' }}
          iconType="circle"
          iconSize={8}
        />

        {data.datasets.map((ds) => {
          if (ds.type === 'line') {
            return (
              <Line
                key={ds.label}
                type="monotone"
                dataKey={ds.label}
                stroke={typeof ds.borderColor === 'string' ? ds.borderColor : '#00D2D3'}
                strokeWidth={2}
                dot={{ r: 3, fill: typeof ds.borderColor === 'string' ? ds.borderColor : '#00D2D3' }}
                activeDot={{ r: 5 }}
              />
            )
          }
          return (
            <Bar
              key={ds.label}
              dataKey={ds.label}
              fill={typeof ds.backgroundColor === 'string' ? ds.backgroundColor : `#6C63FF`}
              stroke={typeof ds.borderColor === 'string' ? ds.borderColor : undefined}
              strokeWidth={0}
              radius={[4, 4, 0, 0]}
              maxBarSize={48}
              isAnimationActive
              animationDuration={700}
              animationEasing="ease-out"
            />
          )
        })}
      </BarChart>
    </ResponsiveContainer>
  )
}
