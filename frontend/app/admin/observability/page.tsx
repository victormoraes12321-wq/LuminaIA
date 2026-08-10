'use client'

import React, { useEffect, useState } from 'react'
import { OBSERVABILITY_CONFIG } from '@/lib/observability/config'
import {
  fetchObservabilityMetrics,
  fetchObservabilitySlos,
  fetchObservabilitySummary,
} from '@/lib/observability/api'
import type {
  ObservabilitySummaryV2,
  OperationalMetricDefinitionV2,
  OperationalMetricRollupV2,
  SloEvaluationV2,
} from '@/types/observability_v2'
import { ObservabilityOverview } from '@/components/observability/ObservabilityOverview'
import { OperationalMetricSummary } from '@/components/observability/OperationalMetricSummary'
import { SloStatusTable } from '@/components/observability/SloStatusTable'

export default function ObservabilityAdminPage() {
  const [summary, setSummary] = useState<ObservabilitySummaryV2 | null>(null)
  const [metrics, setMetrics] = useState<{ definitions: OperationalMetricDefinitionV2[]; rollups: OperationalMetricRollupV2[] }>({ definitions: [], rollups: [] })
  const [evaluations, setEvaluations] = useState<SloEvaluationV2[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let isMounted = true
    async function loadData() {
      try {
        const sum = await fetchObservabilitySummary()
        const met = await fetchObservabilityMetrics()
        const slo = await fetchObservabilitySlos()
        if (isMounted) {
          setSummary(sum)
          setMetrics(met)
          setEvaluations(slo.evaluations)
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Erro ao carregar dados de observabilidade')
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }
    loadData()
    return () => {
      isMounted = false
    }
  }, [])

  if (OBSERVABILITY_CONFIG.mode === 'LEGACY_ONLY') {
    return (
      <div className="p-8 max-w-7xl mx-auto" data-testid="observability-disabled-banner">
        <div className="bg-amber-950/40 border border-amber-800 rounded-lg p-6 text-amber-300">
          <h2 className="text-xl font-bold mb-2">Painel de Observabilidade Desativado</h2>
          <p className="text-sm">
            O modo de observabilidade atual é <code className="bg-amber-900/60 px-2 py-0.5 rounded font-mono">LEGACY_ONLY</code>.
            Para habilitar o painel administrativo, altere a configuração no servidor.
          </p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto text-slate-400 font-mono text-sm" data-testid="observability-loading">
        Carregando telemetria operacional V2...
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div className="p-8 max-w-7xl mx-auto text-red-400 font-mono text-sm" data-testid="observability-error">
        Falha ao carregar observabilidade: {error}
      </div>
    )
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <ObservabilityOverview summary={summary} />
      <SloStatusTable evaluations={evaluations} />
      <OperationalMetricSummary definitions={metrics.definitions} rollups={metrics.rollups} />
    </div>
  )
}
