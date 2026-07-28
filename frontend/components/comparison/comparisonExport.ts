import type { ComparisonPresentationModel } from './comparisonPresentationTypes'

function escapeCsv(value: string | number | boolean | null): string {
  if (value === null) return ''
  const text = String(value)
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function buildComparisonCsv(model: ComparisonPresentationModel): string {
  const rows: Array<Array<string | number | boolean | null>> = [
    ['presentation_version', model.presentationVersion],
    ['comparison_id', model.comparisonId],
    ['comparison_kind', model.comparisonKind],
    ['status', model.status],
    ['partial', model.partial],
    ['truncated', model.truncated],
    [],
    [
      'record_type',
      'operand_id',
      'label',
      'metric_id',
      'unit',
      'period',
      'entity',
      'raw_value',
      'calculation',
      'baseline_operand_id',
      'target_operand_id',
      'direction',
      'value_state',
      'status',
    ],
  ]

  for (const operand of model.operands) {
    rows.push([
      'OPERAND',
      operand.operandId,
      operand.label,
      operand.metricId,
      operand.unit,
      operand.periodLabel,
      operand.entityLabel,
      operand.rawValue,
      null,
      operand.isBaseline ? operand.operandId : null,
      operand.isTarget ? operand.operandId : null,
      null,
      operand.valueState,
      operand.status,
    ])
  }

  for (const calculation of model.calculations) {
    rows.push([
      'CALCULATION',
      null,
      calculation.alignmentKey,
      calculation.metricId,
      null,
      null,
      null,
      calculation.rawResult,
      calculation.calculation,
      calculation.baselineOperandId,
      calculation.targetOperandId,
      calculation.direction,
      calculation.zeroDenominator ? 'NOT_APPLICABLE' : 'VALUE',
      calculation.status,
    ])
  }

  if (model.alignment.missingBucketCount > 0) {
    rows.push([
      'NOTICE', null, 'Buckets ausentes', null, null, null, null,
      model.alignment.missingBucketCount, null, null, null, null, 'MISSING', model.status,
    ])
  }
  if (model.alignment.nullBucketCount > 0) {
    rows.push([
      'NOTICE', null, 'Buckets nulos', null, null, null, null,
      model.alignment.nullBucketCount, null, null, null, null, 'NULL', model.status,
    ])
  }

  return `\uFEFF${rows.map(row => row.map(escapeCsv).join(',')).join('\r\n')}\r\n`
}

export function downloadComparisonCsv(model: ComparisonPresentationModel): void {
  const blob = new Blob([buildComparisonCsv(model)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `comparacao_${model.comparisonId.replace(/[^a-zA-Z0-9_-]/g, '_')}.csv`
  anchor.style.display = 'none'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
