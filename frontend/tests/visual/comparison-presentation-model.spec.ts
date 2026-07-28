import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'
import {
  buildComparisonCsv,
  buildComparisonPresentationModel,
  getComparisonRendererFeatureFlags,
} from '../../components/comparison'
import {
  classifyRawValue,
  formatComparisonValue,
} from '../../components/comparison/comparisonFormatters'
import {
  buildComparisonResponse,
  buildLegacyComparisonResponse,
  type ComparisonFixtureScenario,
} from '../fixtures/comparisonResponse'

const scenarios: ComparisonFixtureScenario[] = [
  'period',
  'multi_period',
  'entity',
  'metric_incompatible',
  'actual_target',
  'partial',
  'zero_denominator',
  'null_missing',
  'multiple_visualizations',
  'timeout',
  'blocked',
]

test('adapter V2 preserves operands, values, calculations and visualization order', () => {
  const model = buildComparisonPresentationModel(buildComparisonResponse('period'))
  expect(model.presentationVersion).toBe('lumina.comparison-presentation/1.0')
  expect(model.operands).toHaveLength(2)
  expect(model.operands.map(item => item.rawValue)).toEqual(['300.00', '400.00'])
  expect(model.calculations.find(item => item.calculation === 'ABSOLUTE_DIFFERENCE')?.rawResult).toBe('100.00')
  expect(model.calculations.find(item => item.calculation === 'PERCENTAGE_DIFFERENCE')?.rawResult).toBe('33.33')
  expect(model.visualizations.map(item => item.kind)).toEqual(['BAR', 'TABLE'])
})

test('adapter is idempotent and does not mutate its input', () => {
  const response = buildComparisonResponse('multiple_visualizations')
  const before = structuredClone(response)
  const first = buildComparisonPresentationModel(response)
  const second = buildComparisonPresentationModel(response)
  expect(first).toEqual(second)
  expect(response).toEqual(before)
})

test('adapter V1 remains compatible without a sidecar', () => {
  const model = buildComparisonPresentationModel(buildLegacyComparisonResponse())
  expect(model.comparisonKind).toBe('LEGACY_COMPARISON')
  expect(model.technicalMetadata).toBeNull()
  expect(model.operands).toHaveLength(2)
  expect(model.visualizations.map(item => item.kind)).toEqual(['BAR'])
})

test('null, missing, zero and not applicable remain distinct', () => {
  const model = buildComparisonPresentationModel(buildComparisonResponse('null_missing'))
  expect(model.operands.map(item => item.valueState)).toEqual(['VALUE', 'NULL', 'MISSING'])
  expect(classifyRawValue('0.00')).toBe('ZERO')
  expect(formatComparisonValue(null, 'BRL', 'NULL')).toBe('Sem valor')
  expect(formatComparisonValue(null, 'BRL', 'MISSING')).toBe('Sem registro')
  expect(formatComparisonValue(null, 'PERCENT', 'NOT_APPLICABLE')).toBe('Nao aplicavel')
})

test('zero denominator never becomes zero percent', () => {
  const model = buildComparisonPresentationModel(buildComparisonResponse('zero_denominator'))
  const percentage = model.calculations.find(item => item.calculation === 'PERCENTAGE_DIFFERENCE')
  expect(percentage?.zeroDenominator).toBe(true)
  expect(percentage?.rawResult).toBeNull()
  expect(percentage?.formattedResult).toBe('Nao aplicavel')
})

test('RBAC restricts technical metadata and provenance', () => {
  const consulta = buildComparisonPresentationModel(
    buildComparisonResponse('period', 'CONSULTA'),
    { role: 'CONSULTA' },
  )
  const gestor = buildComparisonPresentationModel(
    buildComparisonResponse('period', 'GESTOR'),
    { role: 'GESTOR' },
  )
  const admin = buildComparisonPresentationModel(
    buildComparisonResponse('period', 'ADMIN'),
    { role: 'ADMIN' },
  )
  expect(consulta.provenance).toBeNull()
  expect(consulta.technicalMetadata).toBeNull()
  expect(gestor.provenance?.sourceLabel).toBe('PostgreSQL analitico')
  expect(gestor.technicalMetadata).toBeNull()
  expect(admin.validation.checks).toHaveLength(2)
  expect(admin.technicalMetadata?.executorVersion).toBe('lumina.comparison-executor/1.0')
})

test('CSV exports raw values and excludes sensitive fields', () => {
  const model = buildComparisonPresentationModel(buildComparisonResponse('period'))
  const csv = buildComparisonCsv(model)
  expect(csv).toContain('300.00')
  expect(csv).toContain('400.00')
  expect(csv).toContain('100.00')
  expect(csv.toLowerCase()).not.toContain('select ')
  expect(csv.toLowerCase()).not.toContain('binds')
  expect(csv.toLowerCase()).not.toContain('connection_string')
})

test('all presentation states remain explicit', () => {
  const expected: Partial<Record<ComparisonFixtureScenario, string>> = {
    period: 'SUCCESS',
    partial: 'PARTIAL',
    timeout: 'TIMEOUT',
    blocked: 'BLOCKED',
  }
  for (const [scenario, status] of Object.entries(expected)) {
    const model = buildComparisonPresentationModel(
      buildComparisonResponse(scenario as ComparisonFixtureScenario),
    )
    expect(model.status).toBe(status)
  }
})

test('empty, not applicable, clarification, out of scope, unsupported and error stay distinct', () => {
  const emptyResponse = buildComparisonResponse('period')
  emptyResponse.analytical_contract!.datasets[0].rows = []
  emptyResponse.analytical_contract!.datasets[0].row_count = 0
  expect(buildComparisonPresentationModel(emptyResponse).status).toBe('EMPTY')

  const readinessCases = [
    ['CLARIFICATION_REQUIRED', 'CLARIFICATION_REQUIRED'],
    ['OUT_OF_SCOPE', 'OUT_OF_SCOPE'],
    ['UNSUPPORTED', 'UNSUPPORTED'],
    ['ERROR', 'ERROR'],
  ] as const
  for (const [readiness, expected] of readinessCases) {
    const response = buildComparisonResponse('period')
    response.analytical_contract!.intent.readiness = readiness
    expect(buildComparisonPresentationModel(response).status).toBe(expected)
  }

  const notApplicable = buildComparisonPresentationModel(
    buildComparisonResponse('zero_denominator'),
  )
  expect(notApplicable.calculations.find(
    calculation => calculation.calculation === 'PERCENTAGE_DIFFERENCE',
  )?.status).toBe('NOT_APPLICABLE')
})

test('feature flags default to disabled outside explicit rollout', () => {
  const flags = getComparisonRendererFeatureFlags()
  expect(flags.enabled).toBe(false)
  expect(flags.shadowMode).toBe(false)
})

test('adapter preserves controlled high-volume comparisons without silent reduction', () => {
  const response = buildComparisonResponse('period')
  const contract = response.analytical_contract!
  const comparison = contract.intent.comparison!
  const templateOperand = comparison.operands[1]
  for (let index = 2; index < 10; index += 1) {
    comparison.operands.push({
      ...structuredClone(templateOperand),
      operand_id: `periodo_${index + 1}`,
      label: `Periodo ${index + 1}`,
    })
  }

  const sourceRow = contract.datasets[0].rows[0]
  contract.datasets[0].rows = Array.from({ length: 500 }, (_, index) => ({
    ...structuredClone(sourceRow),
    alignment_key: `bucket_${(index % 50) + 1}`,
    target_operand_id: comparison.operands[(index % 9) + 1].operand_id,
  }))
  contract.datasets[0].row_count = 500

  const startedAt = performance.now()
  const model = buildComparisonPresentationModel(response)
  const durationMs = performance.now() - startedAt

  expect(model.operands).toHaveLength(10)
  expect(model.datasets[0].rows).toHaveLength(500)
  expect(new Set(model.datasets[0].rows.map(row => row.alignment_key)).size).toBe(50)
  expect(durationMs).toBeLessThan(2_000)
})

test('area, pie and safe pie fallback follow backend visualization semantics', () => {
  const area = buildComparisonPresentationModel(buildComparisonResponse('area'))
  expect(area.visualizations[0]).toMatchObject({ kind: 'AREA', compatible: true })

  const pie = buildComparisonPresentationModel(buildComparisonResponse('pie'))
  expect(pie.visualizations[0]).toMatchObject({ kind: 'PIE', compatible: true })
  expect(pie.calculations.filter(item => item.calculation === 'SHARE')).toHaveLength(2)

  const unsupportedPieResponse = buildComparisonResponse('period')
  unsupportedPieResponse.analytical_contract!.visualizations[0].kind = 'PIE_CHART'
  const fallback = buildComparisonPresentationModel(unsupportedPieResponse)
  expect(fallback.visualizations[0]).toMatchObject({
    kind: 'PIE',
    compatible: false,
    incompatibilityReason: 'Pizza exige participacao oficial do backend.',
  })
})

test('golden presentation summaries remain deterministic', () => {
  const goldenPath = resolve(process.cwd(), 'tests/golden/comparison-presentation-v2.json')
  const golden = JSON.parse(readFileSync(goldenPath, 'utf8')) as Record<string, unknown>
  const actual: Record<string, unknown> = {}
  for (const scenario of scenarios) {
    const model = buildComparisonPresentationModel(buildComparisonResponse(scenario))
    actual[scenario] = {
      kind: model.comparisonKind,
      operands: model.operands.length,
      status: model.status,
      visualizations: model.visualizations.map(item => item.kind),
    }
  }
  const legacy = buildComparisonPresentationModel(buildLegacyComparisonResponse())
  actual.legacy = {
    kind: legacy.comparisonKind,
    operands: legacy.operands.length,
    status: legacy.status,
    visualizations: legacy.visualizations.map(item => item.kind),
  }
  expect(actual).toEqual(golden)
})

test('frontend presentation source contains no financial formulas or parseFloat', () => {
  const adapter = readFileSync(
    resolve(process.cwd(), 'components/comparison/comparisonPresentationAdapter.ts'),
    'utf8',
  )
  const renderer = readFileSync(
    resolve(process.cwd(), 'components/comparison/ComparisonRenderer.tsx'),
    'utf8',
  )
  const source = `${adapter}\n${renderer}`
  expect(source).not.toContain('parseFloat')
  expect(source).not.toMatch(/target\s*-\s*baseline/)
  expect(source).not.toMatch(/\/\s*Math\.abs\s*\(\s*baseline/)
  expect(source).not.toMatch(/\.sort\s*\(/)
})
