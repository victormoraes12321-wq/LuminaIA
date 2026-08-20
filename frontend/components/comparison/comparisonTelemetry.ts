import type {
  ComparisonPresentationModel,
  ComparisonUserRole,
} from './comparisonPresentationTypes'

export interface ComparisonPresentationTelemetry {
  presentationVersion: string
  comparisonKind: string
  renderer: 'COMPARISON_V2' | 'LEGACY_FALLBACK' | 'SHADOW'
  operandCount: number
  datasetCount: number
  rowCount: number
  visualizationCount: number
  partial: boolean
  truncated: boolean
  status: string
  adaptationDurationMs: number
  fallbackUsed: boolean
  featureEnabled: boolean
  shadowDivergence: boolean
  structuralFingerprint: string | null
  role: ComparisonUserRole
  errorCode: string | null
}

export function structuralFingerprint(model: ComparisonPresentationModel): string {
  return [
    model.presentationVersion,
    model.comparisonKind,
    model.status,
    model.operands.length,
    model.datasets.length,
    model.datasets.reduce((total, dataset) => total + dataset.rowCount, 0),
    model.visualizations.map(item => item.kind).join('|'),
    model.partial ? 'partial' : 'complete',
    model.truncated ? 'truncated' : 'full',
  ].join(':')
}

export function emitComparisonTelemetry(
  telemetry: ComparisonPresentationTelemetry,
): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent('lumina:comparison-presentation', {
    detail: telemetry,
  }))
}
