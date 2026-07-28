import type {
  ComparisonDirection,
  ComparisonValueState,
} from './comparisonPresentationTypes'

const decimalParts = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
}).formatToParts(1000.5)

const decimalSeparator = decimalParts.find(part => part.type === 'decimal')?.value ?? ','
const groupSeparator = decimalParts.find(part => part.type === 'group')?.value ?? '.'
const currencySymbol = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
}).formatToParts(0).find(part => part.type === 'currency')?.value ?? 'R$'

function normalizeDecimal(value: string | number): {
  negative: boolean
  integer: string
  fraction: string
} | null {
  const raw = typeof value === 'number' ? String(value) : value.trim()
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(raw)
  if (!match) return null
  return {
    negative: match[1] === '-',
    integer: match[2].replace(/^0+(?=\d)/, ''),
    fraction: match[3] ?? '',
  }
}

function groupInteger(value: string): string {
  return value.replace(/\B(?=(\d{3})+(?!\d))/g, groupSeparator)
}

function formatDecimalString(
  value: string | number,
  minimumFractionDigits: number,
  maximumFractionDigits: number,
): string | null {
  const normalized = normalizeDecimal(value)
  if (!normalized) return null
  const fraction = normalized.fraction
    .slice(0, maximumFractionDigits)
    .padEnd(minimumFractionDigits, '0')
  const sign = normalized.negative ? '-' : ''
  return `${sign}${groupInteger(normalized.integer)}${fraction ? `${decimalSeparator}${fraction}` : ''}`
}

export function classifyRawValue(
  value: string | number | null,
  explicitState?: ComparisonValueState,
): ComparisonValueState {
  if (explicitState) return explicitState
  if (value === null) return 'NULL'
  const normalized = normalizeDecimal(value)
  if (!normalized) return 'NOT_APPLICABLE'
  const isZero = /^0*$/.test(normalized.integer) && /^0*$/.test(normalized.fraction)
  return isZero ? 'ZERO' : 'VALUE'
}

export function formatComparisonValue(
  value: string | number | null,
  unit: string,
  state: ComparisonValueState,
): string {
  if (state === 'MISSING') return 'Sem registro'
  if (state === 'NULL') return 'Sem valor'
  if (state === 'NOT_APPLICABLE') return 'Nao aplicavel'
  if (state === 'RESTRICTED') return 'Acesso restrito'
  if (state === 'TRUNCATED') return 'Resultado parcial'
  if (value === null) return 'Sem valor'

  const normalizedUnit = unit.toUpperCase()
  if (normalizedUnit === 'BRL' || normalizedUnit === 'CURRENCY') {
    const formatted = formatDecimalString(value, 2, 2)
    return formatted === null ? 'Valor invalido' : `${currencySymbol} ${formatted}`
  }
  if (normalizedUnit === 'PERCENT' || normalizedUnit === 'PERCENTAGE' || normalizedUnit === '%') {
    const formatted = formatDecimalString(value, 2, 4)
    return formatted === null ? 'Valor invalido' : `${formatted}%`
  }
  if (normalizedUnit === 'COUNT' || normalizedUnit === 'QUANTITY' || normalizedUnit === 'INTEGER') {
    const formatted = formatDecimalString(value, 0, 0)
    return formatted ?? 'Valor invalido'
  }
  return formatDecimalString(value, 0, 4) ?? 'Valor invalido'
}

export function directionLabel(direction: ComparisonDirection): string {
  switch (direction) {
    case 'INCREASE':
      return 'Aumentou'
    case 'DECREASE':
      return 'Diminuiu'
    case 'STABLE':
      return 'Permaneceu estavel'
    default:
      return 'Nao aplicavel'
  }
}

export function calculationLabel(calculation: string): string {
  const labels: Record<string, string> = {
    VALUE: 'Valor comparado',
    ABSOLUTE_DIFFERENCE: 'Diferenca',
    PERCENTAGE_DIFFERENCE: 'Variacao percentual',
    DIRECTION: 'Direcao',
    SHARE: 'Participacao',
    RANK: 'Posicao no ranking',
  }
  return labels[calculation] ?? calculation.replace(/_/g, ' ')
}

export function formatDateTime(value: string | null): string {
  if (!value) return 'Nao informado'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Nao informado'
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}

export function toChartNumber(value: string | number | null): number | null {
  if (value === null) return null
  const normalized = normalizeDecimal(value)
  if (!normalized) return null
  const converted = Number(
    `${normalized.negative ? '-' : ''}${normalized.integer}.${normalized.fraction || '0'}`,
  )
  return Number.isFinite(converted) ? converted : null
}
