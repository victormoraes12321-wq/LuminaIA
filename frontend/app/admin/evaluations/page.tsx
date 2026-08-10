'use client'

import React, { useEffect, useState } from 'react'
import { OBSERVABILITY_CONFIG } from '@/lib/observability/config'
import {
  fetchEvaluationRegressions,
  fetchEvaluationRuns,
  fetchEvaluationSuites,
  triggerEvaluationRun,
} from '@/lib/observability/api'
import type {
  EvaluationRegressionV2,
  EvaluationRunV2,
  EvaluationSuiteV2,
} from '@/types/observability_v2'
import { EvaluationSuiteList } from '@/components/observability/EvaluationSuiteList'
import { EvaluationRunList } from '@/components/observability/EvaluationRunList'
import { EvaluationRunDetail } from '@/components/observability/EvaluationRunDetail'
import { RegressionPanel } from '@/components/observability/RegressionPanel'

export default function EvaluationsAdminPage() {
  const [suites, setSuites] = useState<EvaluationSuiteV2[]>([])
  const [runs, setRuns] = useState<EvaluationRunV2[]>([])
  const [regressions, setRegressions] = useState<EvaluationRegressionV2[]>([])
  const [selectedRun, setSelectedRun] = useState<EvaluationRunV2 | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true
    async function loadData() {
      try {
        const s = await fetchEvaluationSuites()
        const r = await fetchEvaluationRuns()
        const reg = await fetchEvaluationRegressions()
        if (isMounted) {
          setSuites(s.suites)
          setRuns(r.runs)
          setRegressions(reg.regressions)
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Erro ao carregar suítes de avaliação')
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

  async function handleRunSuite(kind: string) {
    try {
      const newRun = await triggerEvaluationRun(kind)
      setRuns((prev) => [newRun, ...prev])
      if (newRun.regressions.length > 0) {
        setRegressions((prev) => [...newRun.regressions, ...prev])
      }
    } catch (err: any) {
      alert(`Falha ao executar suíte: ${err.message}`)
    }
  }

  if (OBSERVABILITY_CONFIG.mode === 'LEGACY_ONLY') {
    return (
      <div className="p-8 max-w-7xl mx-auto" data-testid="evaluations-disabled-banner">
        <div className="bg-amber-950/40 border border-amber-800 rounded-lg p-6 text-amber-300">
          <h2 className="text-xl font-bold mb-2">Painel de Avaliações Desativado</h2>
          <p className="text-sm">
            O modo de observabilidade atual é <code className="bg-amber-900/60 px-2 py-0.5 rounded font-mono">LEGACY_ONLY</code>.
          </p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto text-slate-400 font-mono text-sm" data-testid="evaluations-loading">
        Carregando suítes de avaliação V2...
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8 max-w-7xl mx-auto text-red-400 font-mono text-sm" data-testid="evaluations-error">
        Falha ao carregar suítes: {error}
      </div>
    )
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <RegressionPanel regressions={regressions} />
      <EvaluationSuiteList suites={suites} onRunSuite={handleRunSuite} />
      <EvaluationRunList runs={runs} onSelectRun={setSelectedRun} />
      {selectedRun && (
        <EvaluationRunDetail run={selectedRun} onClose={() => setSelectedRun(null)} />
      )}
    </div>
  )
}
