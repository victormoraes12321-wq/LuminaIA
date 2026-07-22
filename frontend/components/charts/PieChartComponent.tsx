'use client'

import { useState } from 'react'
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import type { ChartDataPie } from '@/types/lumina'

function formatPieValue(val?: number): string {
  if (val === undefined || val === null) return ''
  if (Math.abs(val) >= 100) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 2 }).format(val)
  }
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(val)
}

// ── Glassmorphism Tooltip ──────────────────────────────────────

interface PieTooltipProps {
  active?: boolean
  payload?: Array<{
    name: string
    value: number
    payload: { color: string; rawValue?: number }
  }>
}

function PieTooltip({ active, payload }: PieTooltipProps) {
  if (!active || !payload?.length) return null
  const entry = payload[0]
  const rawVal = entry.payload.rawValue

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
      {rawVal !== undefined && (
        <p className="text-base font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
          {formatPieValue(rawVal)}
        </p>
      )}
      <p className="text-xs font-medium text-emerald-400 mt-0.5">
        {entry.value.toFixed(1)}% do total
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
      {data.labels.map((label, i) => {
        const rawVal = data.valores_brutos?.[i]
        return (
          <button
            key={label}
            className="flex items-center gap-2.5 text-left group rounded-lg px-2.5 py-1.5 transition-colors hover:bg-[rgb(var(--bg-elevated))]"
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
            <div className="flex flex-col items-end flex-shrink-0">
              {rawVal !== undefined && (
                <span
                  className="text-xs font-bold"
                  style={{
                    color: activeIndex === i ? data.colors[i] : 'rgb(var(--text-primary))',
                  }}
                >
                  {formatPieValue(rawVal)}
                </span>
              )}
              <span className="text-[10px] font-semibold text-emerald-400">
                {data.values[i]?.toFixed(1)}%
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}

// ── PieChartComponent ─────────────────────────────────────────

interface PieChartComponentProps {
  data: ChartDataPie
}

export function PieChartComponent({ data }: PieChartComponentProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null)

  const chartData = data.labels.map((label: string, i: number) => ({
    name: label,
    value: data.values[i],
    rawValue: data.valores_brutos?.[i],
    color: data.colors[i],
  }))

  const maxIndex = data.values.indexOf(Math.max(...data.values))
  const centerLabel = data.labels[maxIndex]
  const centerRawVal = data.valores_brutos?.[maxIndex]

  const activeRawVal = activeIndex !== null ? data.valores_brutos?.[activeIndex] : centerRawVal

  return (
    <div className="flex gap-4 items-center h-full">
      {/* Donut chart */}
      <div className="flex-shrink-0 w-[200px] h-[200px] relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={58}
              outerRadius={88}
              paddingAngle={2}
              dataKey="value"
              animationBegin={0}
              animationDuration={800}
              animationEasing="ease-out"
              onMouseEnter={(_, index: number) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
            >
              {chartData.map((entry: { name: string; value: number; color: string; rawValue?: number }, index: number) => (
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
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none px-2">
          {activeIndex !== null ? (
            <>
              {activeRawVal !== undefined && (
                <p className="text-xs font-bold truncate max-w-full" style={{ color: data.colors[activeIndex] }}>
                  {formatPieValue(activeRawVal)}
                </p>
              )}
              <p className="text-sm font-bold text-emerald-400">
                {data.values[activeIndex]?.toFixed(1)}%
              </p>
              <p className="text-[10px] text-center px-1 truncate max-w-full leading-tight mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
                {data.labels[activeIndex]}
              </p>
            </>
          ) : (
            <>
              <p className="text-xs font-bold text-indigo-400 truncate max-w-full">
                {formatPieValue(data.valores_brutos?.reduce((a, b) => a + b, 0))}
              </p>
              <p className="text-[11px] font-semibold text-emerald-400">
                100%
              </p>
              <p className="text-[10px] px-1 text-center truncate max-w-full leading-tight mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
                Total Geral
              </p>
            </>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex-1 overflow-y-auto thin-scroll max-h-[200px]">
        <PieLegend
          data={data}
          activeIndex={activeIndex}
          onHover={setActiveIndex}
        />
      </div>
    </div>
  )
}
