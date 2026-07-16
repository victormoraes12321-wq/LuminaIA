'use client'

import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import type { ChartDataPie } from '@/types/lumina'

// ── Glassmorphism Tooltip ──────────────────────────────────────

interface PieTooltipProps {
  active?: boolean
  payload?: Array<{
    name: string
    value: number
    payload: { color: string }
  }>
}

function PieTooltip({ active, payload }: PieTooltipProps) {
  if (!active || !payload?.length) return null
  const entry = payload[0]
  return (
    <div
      className="glass-strong rounded-xl px-4 py-3 shadow-lumina"
      style={{ border: '1px solid rgb(var(--accent) / 0.2)' }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className="w-2.5 h-2.5 rounded-full"
          style={{ background: entry.payload.color }}
        />
        <span className="text-xs font-semibold" style={{ color: 'rgb(var(--text-primary))' }}>
          {entry.name}
        </span>
      </div>
      <p className="text-lg font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
        {entry.value.toFixed(1)}%
      </p>
    </div>
  )
}

// ── Custom Legend ──────────────────────────────────────────────

interface PieLegendProps {
  data: ChartDataPie
  activeIndex: number | null
  onHover: (i: number | null) => void
}

function PieLegend({ data, activeIndex, onHover }: PieLegendProps) {
  return (
    <div className="flex flex-col gap-2 justify-center min-w-0">
      {data.labels.map((label, i) => (
        <button
          key={label}
          className="flex items-center gap-2.5 text-left group rounded-lg px-2 py-1 transition-colors hover:bg-[rgb(var(--bg-elevated))]"
          onMouseEnter={() => onHover(i)}
          onMouseLeave={() => onHover(null)}
        >
          <span
            className="w-2.5 h-2.5 rounded-full flex-shrink-0 transition-transform group-hover:scale-125"
            style={{
              background: data.colors[i],
              opacity: activeIndex !== null && activeIndex !== i ? 0.35 : 1,
            }}
          />
          <div className="min-w-0 flex-1">
            <p
              className="text-xs font-medium truncate transition-colors"
              style={{
                color: activeIndex === i
                  ? 'rgb(var(--text-primary))'
                  : 'rgb(var(--text-secondary))',
              }}
            >
              {label}
            </p>
          </div>
          <span
            className="text-xs font-bold flex-shrink-0"
            style={{
              color: activeIndex === i ? data.colors[i] : 'rgb(var(--text-muted))',
            }}
          >
            {data.values[i]?.toFixed(1)}%
          </span>
        </button>
      ))}
    </div>
  )
}

// ── PieChartComponent ─────────────────────────────────────────

import { useState } from 'react'

interface PieChartComponentProps {
  data: ChartDataPie
}

export function PieChartComponent({ data }: PieChartComponentProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null)

  const chartData = data.labels.map((label, i) => ({
    name: label,
    value: data.values[i],
    color: data.colors[i],
  }))

  // Find largest segment for center label
  const maxIndex = data.values.indexOf(Math.max(...data.values))
  const centerLabel = data.labels[maxIndex]

  return (
    <div className="flex gap-4 items-center h-full">
      {/* Donut chart */}
      <div className="flex-shrink-0 w-[180px] h-[180px] relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={56}
              outerRadius={84}
              paddingAngle={2}
              dataKey="value"
              animationBegin={0}
              animationDuration={800}
              animationEasing="ease-out"
              onMouseEnter={(_, index) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                  stroke="transparent"
                  opacity={activeIndex !== null && activeIndex !== index ? 0.4 : 1}
                  style={{ cursor: 'pointer', transition: 'opacity 0.2s ease' }}
                />
              ))}
            </Pie>
            <Tooltip content={<PieTooltip />} />
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          {activeIndex !== null ? (
            <>
              <p className="text-base font-bold" style={{ color: data.colors[activeIndex] }}>
                {data.values[activeIndex]?.toFixed(1)}%
              </p>
              <p className="text-[10px] text-center px-3 leading-tight mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
                {data.labels[activeIndex]}
              </p>
            </>
          ) : (
            <>
              <p className="text-base font-bold" style={{ color: data.colors[maxIndex] }}>
                {data.values[maxIndex]?.toFixed(1)}%
              </p>
              <p className="text-[10px] px-2 text-center leading-tight mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
                {centerLabel?.split(' ')[0]}
              </p>
            </>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex-1 overflow-y-auto thin-scroll max-h-[180px]">
        <PieLegend
          data={data}
          activeIndex={activeIndex}
          onHover={setActiveIndex}
        />
      </div>
    </div>
  )
}
