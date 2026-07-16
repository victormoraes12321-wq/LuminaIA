'use client'

import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'react'

// ── GlassCard ─────────────────────────────────────────────────

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  /** Extra padding preset */
  padding?: 'none' | 'sm' | 'md' | 'lg'
  /** Disable hover lift effect */
  noHover?: boolean
  /** Enable animated gradient border on hover */
  gradientBorder?: boolean
  /** Make card act like a button (adds cursor-pointer) */
  clickable?: boolean
}

const paddingMap = {
  none: '',
  sm:   'p-4',
  md:   'p-5',
  lg:   'p-7',
} as const

export function GlassCard({
  children,
  className,
  padding = 'md',
  noHover = false,
  gradientBorder = false,
  clickable = false,
  ...props
}: GlassCardProps) {
  return (
    <div
      className={cn(
        'lumina-card',
        paddingMap[padding],
        !noHover && 'hover:cursor-default',
        gradientBorder && 'card-gradient-border',
        clickable && 'cursor-pointer interactive',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

// ── CardHeader ────────────────────────────────────────────────

interface CardHeaderProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
  icon?: React.ReactNode
}

export function CardHeader({ title, subtitle, actions, icon }: CardHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-3 mb-4">
      <div className="flex items-center gap-2.5 min-w-0">
        {icon && (
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-lumina-500/10 flex items-center justify-center text-lumina-500">
            {icon}
          </div>
        )}
        <div className="min-w-0">
          <h3 className="text-sm font-semibold truncate" style={{ color: 'rgb(var(--text-primary))' }}>
            {title}
          </h3>
          {subtitle && (
            <p className="text-xs mt-0.5 truncate" style={{ color: 'rgb(var(--text-muted))' }}>
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {actions && <div className="flex-shrink-0">{actions}</div>}
    </div>
  )
}

// ── CardDivider ───────────────────────────────────────────────

export function CardDivider({ className }: { className?: string }) {
  return (
    <div
      className={cn('h-px w-full my-4', className)}
      style={{ background: 'rgb(var(--border) / 0.5)' }}
    />
  )
}
