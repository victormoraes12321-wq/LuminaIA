'use client'

import { cn } from '@/lib/utils'

const CHART_SKELETON_BAR_HEIGHTS = [34, 52, 68, 49, 76, 58, 82, 61, 45, 70, 56, 64]

// ── Individual Skeleton ────────────────────────────────────────

interface SkeletonProps {
  className?: string
  height?: string | number
  width?: string | number
  rounded?: string
  style?: React.CSSProperties
}

export function Skeleton({ className, height, width, rounded = 'rounded-lg', style }: SkeletonProps) {
  return (
    <div
      className={cn('skeleton', rounded, className)}
      style={{ height, width, ...style }}
      aria-hidden
    />
  )
}

// ── KPI Skeleton Row ───────────────────────────────────────────

function KPISkeletonCard() {
  return (
    <div className="lumina-card p-5 space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-6 w-12 rounded-full" />
      </div>
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-10 w-full rounded-lg" />
    </div>
  )
}

// ── Chart Skeleton ─────────────────────────────────────────────

function ChartSkeletonCard({ tall = false }: { tall?: boolean }) {
  return (
    <div className={cn('lumina-card p-5 flex flex-col gap-4', tall ? 'min-h-[380px]' : 'min-h-[280px]')}>
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-3 w-28" />
          <Skeleton className="h-2.5 w-40" />
        </div>
        <Skeleton className="h-7 w-16 rounded-lg" />
      </div>

      {/* Fake bar chart */}
      <div className="flex-1 flex items-end gap-2 pt-4 pb-1">
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="flex-1 skeleton rounded-t-sm"
            style={{
              height: `${CHART_SKELETON_BAR_HEIGHTS[i % CHART_SKELETON_BAR_HEIGHTS.length]}%`,
              animationDelay: `${i * 0.08}s`,
            }}
          />
        ))}
      </div>

      {/* X-axis labels */}
      <div className="flex gap-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="flex-1 h-2" />
        ))}
      </div>
    </div>
  )
}

// ── Table Skeleton ─────────────────────────────────────────────

function TableSkeletonCard() {
  return (
    <div className="lumina-card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-8 w-48 rounded-xl" />
      </div>

      {/* Table header */}
      <div className="flex gap-4 pb-2" style={{ borderBottom: '1px solid rgb(var(--border) / 0.4)' }}>
        {[4, 6, 3, 3, 2].map((w, i) => (
          <Skeleton key={i} className={`h-2.5 flex-${w}`} style={{ flex: w }} />
        ))}
      </div>

      {/* Rows */}
      {Array.from({ length: 6 }).map((_, row) => (
        <div key={row} className="flex gap-4 items-center">
          {[4, 6, 3, 3, 2].map((w, i) => (
            <Skeleton
              key={i}
              className="h-3"
              style={{ flex: w, animationDelay: `${row * 0.05 + i * 0.02}s` }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

// ── Full Skeleton Grid (Dashboard Loading State) ───────────────

export function SkeletonGrid() {
  return (
    <div className="bento-grid w-full" aria-label="Carregando dados..." role="status">
      {/* KPI row — full width */}
      <div className="bento-span-12 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3.5">
        {Array.from({ length: 5 }).map((_, i) => (
          <KPISkeletonCard key={i} />
        ))}
      </div>

      {/* Main chart — 8/12 */}
      <div className="bento-span-8">
        <ChartSkeletonCard tall />
      </div>

      {/* Side chart — 4/12 */}
      <div className="bento-span-4 hidden md:block">
        <div className="lumina-card p-5 h-full min-h-[380px] flex flex-col gap-4">
          <Skeleton className="h-3 w-24" />
          {/* Fake donut */}
          <div className="flex-1 flex items-center justify-center">
            <div className="relative w-44 h-44">
              <Skeleton className="w-full h-full rounded-full" />
              <div
                className="absolute inset-8 rounded-full"
                style={{ background: 'rgb(var(--bg-surface))' }}
              />
            </div>
          </div>
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center gap-2">
                <Skeleton className="w-2.5 h-2.5 rounded-full flex-shrink-0" />
                <Skeleton className="flex-1 h-2.5" style={{ animationDelay: `${i * 0.1}s` }} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Table — full width */}
      <div className="bento-span-12">
        <TableSkeletonCard />
      </div>
    </div>
  )
}

// ── Inline skeleton (single line) ─────────────────────────────

export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className="h-3"
          style={{
            width: i === lines - 1 ? '60%' : '100%',
            animationDelay: `${i * 0.07}s`,
          }}
        />
      ))}
    </div>
  )
}
