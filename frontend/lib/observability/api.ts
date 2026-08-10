import { getApiBase } from '@/lib/utils'
import type {
  EvaluationRegressionV2,
  EvaluationRunV2,
  EvaluationSuiteV2,
  ObservabilitySummaryV2,
  OperationalMetricDefinitionV2,
  OperationalMetricRollupV2,
  SloEvaluationV2,
} from '@/types/observability_v2'

export async function fetchObservabilitySummary(): Promise<ObservabilitySummaryV2> {
  const res = await fetch(`${getApiBase()}/api/v2/observability/summary`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch observability summary: ${res.status}`)
  }
  return res.json()
}

export async function fetchObservabilityMetrics(): Promise<{
  definitions: OperationalMetricDefinitionV2[]
  rollups: OperationalMetricRollupV2[]
}> {
  const res = await fetch(`${getApiBase()}/api/v2/observability/metrics`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch observability metrics: ${res.status}`)
  }
  return res.json()
}

export async function fetchObservabilitySlos(): Promise<{
  slos: any[]
  evaluations: SloEvaluationV2[]
}> {
  const res = await fetch(`${getApiBase()}/api/v2/observability/slos`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch observability slos: ${res.status}`)
  }
  return res.json()
}

export async function fetchEvaluationSuites(): Promise<{ suites: EvaluationSuiteV2[] }> {
  const res = await fetch(`${getApiBase()}/api/v2/evaluations/suites`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch evaluation suites: ${res.status}`)
  }
  return res.json()
}

export async function triggerEvaluationRun(suiteKind: string): Promise<EvaluationRunV2> {
  const res = await fetch(`${getApiBase()}/api/v2/evaluations/runs?suite=${encodeURIComponent(suiteKind)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`Failed to trigger evaluation run: ${res.status}`)
  }
  return res.json()
}

export async function fetchEvaluationRuns(): Promise<{ runs: EvaluationRunV2[] }> {
  const res = await fetch(`${getApiBase()}/api/v2/evaluations/runs`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch evaluation runs: ${res.status}`)
  }
  return res.json()
}

export async function fetchEvaluationRegressions(): Promise<{ regressions: EvaluationRegressionV2[] }> {
  const res = await fetch(`${getApiBase()}/api/v2/evaluations/regressions`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch evaluation regressions: ${res.status}`)
  }
  return res.json()
}
