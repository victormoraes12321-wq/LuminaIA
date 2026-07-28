import type {
  AnalyticalComparison,
  AnalyticalValidationStatus,
  ChartType,
  JsonValue,
} from '@/types/lumina'

export const COMPARISON_PRESENTATION_VERSION = 'lumina.comparison-presentation/1.0' as const

export type ComparisonUserRole = 'ADMIN' | 'GESTOR' | 'CONSULTA'

export type ComparisonPresentationStatus =
  | 'SUCCESS'
  | 'PARTIAL'
  | 'EMPTY'
  | 'NOT_APPLICABLE'
  | 'CLARIFICATION_REQUIRED'
  | 'OUT_OF_SCOPE'
  | 'UNSUPPORTED'
  | 'BLOCKED'
  | 'TIMEOUT'
  | 'ERROR'

export type ComparisonValueState =
  | 'VALUE'
  | 'ZERO'
  | 'NULL'
  | 'MISSING'
  | 'NOT_APPLICABLE'
  | 'RESTRICTED'
  | 'TRUNCATED'

export type ComparisonDirection = 'INCREASE' | 'DECREASE' | 'STABLE' | 'NOT_APPLICABLE'

export interface ComparisonOperandPresentation {
  operandId: string
  label: string
  shortLabel: string
  metricId: string
  metricLabel: string
  unit: string
  periodLabel: string | null
  entityLabel: string | null
  rawValue: string | number | null
  formattedValue: string
  valueState: ComparisonValueState
  status: string
  isBaseline: boolean
  isTarget: boolean
  isMissing: boolean
  isNull: boolean
  isPartial: boolean
  warnings: string[]
  accessibilityLabel: string
}

export interface ComparisonCalculationPresentation {
  calculation: AnalyticalComparison['calculations'][number]
  baselineOperandId: string | null
  targetOperandId: string
  metricId: string
  alignmentKey: string
  baselineRawValue: string | number | null
  targetRawValue: string | number | null
  rawResult: string | number | null
  formattedResult: string
  direction: ComparisonDirection
  status: string
  zeroDenominator: boolean
  notApplicableReason: string | null
  roundingApplied: boolean
  accessibilityLabel: string
}

export interface ComparisonDatasetPresentation {
  datasetId: string
  columns: Array<{
    key: string
    label: string
    dataType: string
  }>
  rows: Array<Record<string, JsonValue>>
  alignmentKeys: string[]
  units: Record<string, string>
  missingBuckets: number
  nullBuckets: number
  rowCount: number
  truncated: boolean
  visualCompatibility: ChartType[]
  exportable: boolean
}

export interface ComparisonVisualizationPresentation {
  id: string
  kind: ChartType
  title: string
  dataReference: string | null
  isPrimary: boolean
  priority: number
  compatible: boolean
  incompatibilityReason: string | null
  source: 'EXPLICIT' | 'BACKEND' | 'PREFERENCE' | 'DEFAULT' | 'LEGACY'
}

export interface ComparisonValidationPresentation {
  status: AnalyticalValidationStatus
  label: string
  validatorVersion: string | null
  validatedAt: string | null
  checks: Array<{
    code: string
    status: string
    message: string
    required: boolean
  }>
}

export interface ComparisonProvenancePresentation {
  sourceLabel: string
  updatedAt: string | null
  periods: string[]
  metrics: Array<{ id: string; label: string; version: string }>
  executorVersion: string | null
  plannerVersion: string | null
  normalizerVersion: string | null
  cacheStatus: string | null
  validationStatus: AnalyticalValidationStatus
  tenantIsolationVerified: boolean | null
}

export interface ComparisonPresentationModel {
  presentationVersion: typeof COMPARISON_PRESENTATION_VERSION
  comparisonId: string
  comparisonKind: AnalyticalComparison['kind'] | 'LEGACY_COMPARISON'
  title: string
  subtitle: string
  status: ComparisonPresentationStatus
  partial: boolean
  truncated: boolean
  baselineOperandId: string | null
  targetOperandIds: string[]
  operands: ComparisonOperandPresentation[]
  calculations: ComparisonCalculationPresentation[]
  datasets: ComparisonDatasetPresentation[]
  visualizations: ComparisonVisualizationPresentation[]
  alignment: {
    dimensions: string[]
    missingBucketCount: number
    nullBucketCount: number
  }
  validation: ComparisonValidationPresentation
  provenance: ComparisonProvenancePresentation | null
  warnings: string[]
  errors: string[]
  displayPolicy: {
    dense: boolean
    showTechnicalDetails: boolean
    showProvenance: boolean
    volumeWarning: boolean
  }
  exportPolicy: {
    allowed: boolean
    includeTechnicalMetadata: boolean
  }
  accessPolicy: {
    role: ComparisonUserRole
    technicalLevel: 'BASIC' | 'SUMMARY' | 'FULL'
  }
  technicalMetadata: {
    executorVersion: string | null
    plannerVersion: string | null
    normalizerVersion: string | null
    strategy: string | null
    cacheStatus: string | null
    adaptationDurationMs: number
    fallbackUsed: boolean
  } | null
}

export class ComparisonPresentationContractError extends Error {
  readonly code: string

  constructor(code: string, message: string) {
    super(message)
    this.name = 'ComparisonPresentationContractError'
    this.code = code
  }
}
