'use client'

import { cn } from '@/lib/utils'

// ── Badge ─────────────────────────────────────────────────────

type BadgeVariant =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral'
  | 'lumina'

type BadgeSize = 'xs' | 'sm' | 'md'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  size?: BadgeSize
  dot?: boolean
  className?: string
}

const variantClasses: Record<BadgeVariant, string> = {
  success: 'badge-success',
  warning: 'badge-warning',
  danger:  'badge-danger',
  info:    'badge-info',
  neutral: 'badge-neutral',
  lumina:  'badge-lumina',
}

const sizeClasses: Record<BadgeSize, string> = {
  xs: 'text-[10px] px-1.5 py-0.5 leading-tight',
  sm: 'text-xs px-2 py-0.5',
  md: 'text-xs px-2.5 py-1',
}

// ── Map status strings to variants ────────────────────────────

export const statusVariantMap: Record<string, BadgeVariant> = {
  APROVADO:          'success',
  ATIVO:             'success',
  CONCLUÍDO:         'success',
  PAGO:              'success',
  PENDENTE:          'warning',
  EM_PROCESSAMENTO:  'info',
  EM_ANÁLISE:        'info',
  CANCELADO:         'danger',
  REJEITADO:         'danger',
  INATIVO:           'neutral',
  RASCUNHO:          'neutral',
}

export function getStatusVariant(status: string): BadgeVariant {
  return statusVariantMap[status.toUpperCase()] ?? 'neutral'
}

export function Badge({
  children,
  variant = 'neutral',
  size = 'sm',
  dot = false,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
    >
      {dot && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full flex-shrink-0',
            {
              'bg-cyan-400':    variant === 'success',
              'bg-yellow-400':  variant === 'warning',
              'bg-red-400':     variant === 'danger',
              'bg-teal-400':    variant === 'info',
              'bg-zinc-400':    variant === 'neutral',
              'bg-violet-400':  variant === 'lumina',
            },
          )}
        />
      )}
      {children}
    </span>
  )
}

// ── StatusBadge convenience wrapper ───────────────────────────

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant={getStatusVariant(status)} dot size="sm">
      {status.replace(/_/g, ' ')}
    </Badge>
  )
}

// ── TrendBadge ────────────────────────────────────────────────

interface TrendBadgeProps {
  value: number
  suffix?: string
}

export function TrendBadge({ value, suffix = '%' }: TrendBadgeProps) {
  const isPositive = value > 0
  const isNeutral  = value === 0

  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 text-xs font-semibold px-1.5 py-0.5 rounded-md',
        isNeutral  ? 'text-zinc-400 bg-zinc-400/10' :
        isPositive ? 'text-emerald-400 bg-emerald-400/10' :
                     'text-red-400 bg-red-400/10',
      )}
    >
      {isPositive ? '↑' : isNeutral ? '→' : '↓'}
      {Math.abs(value).toFixed(1)}{suffix}
    </span>
  )
}
