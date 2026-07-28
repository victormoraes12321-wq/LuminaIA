import type { AnalyticalResponseV2, QueryResponse } from '@/types/lumina'

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isAnalyticalResponseV2(value: unknown): value is AnalyticalResponseV2 {
  if (!isRecord(value) || !isRecord(value.contract) || !isRecord(value.intent)) {
    return false
  }
  return (
    value.contract.schema_name === 'lumina.analytics' &&
    value.contract.schema_version === '2.0' &&
    Array.isArray(value.intent.time_windows) &&
    Array.isArray(value.intent.requested_visualizations) &&
    Array.isArray(value.datasets) &&
    Array.isArray(value.visualizations)
  )
}

/**
 * Keeps the V1 rendering surface stable and validates the optional V2 sidecar.
 * Business values and visualization data are never synthesized here.
 */
export function normalizeQueryResponse(value: unknown): QueryResponse {
  if (!isRecord(value) || typeof value.query_id !== 'string') {
    throw new Error('Resposta de consulta invalida.')
  }

  const response = value as unknown as QueryResponse
  if (value.analytical_contract === undefined || value.analytical_contract === null) {
    return response
  }
  if (!isAnalyticalResponseV2(value.analytical_contract)) {
    throw new Error('Contrato analitico V2 invalido.')
  }
  return {
    ...response,
    analytical_contract: value.analytical_contract,
  }
}
