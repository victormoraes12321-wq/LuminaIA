'use client'

import React from 'react'
import type { EvaluationRegressionV2 } from '@/types/observability_v2'

interface Props {
  regressions: EvaluationRegressionV2[]
}

export function RegressionPanel({ regressions }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 mb-6" data-testid="regression-panel">
      <h3 className="text-lg font-bold text-slate-100 mb-4">Regressões de Avaliação Detectadas ({regressions.length})</h3>
      {regressions.length === 0 ? (
        <div className="text-emerald-400 text-sm py-4 font-semibold" data-testid="no-regressions">
          ✅ Nenhuma regressão funcional, de segurança ou de tenant detectada contra baselines certificados.
        </div>
      ) : (
        <div className="space-y-3">
          {regressions.map((reg) => (
            <div key={reg.regression_id} className="p-4 bg-red-950/40 border border-red-900 rounded-md">
              <div className="flex justify-between items-center mb-1">
                <span className="font-mono text-xs font-bold text-red-300">{reg.case_id} ({reg.suite})</span>
                <span className="text-xs font-bold text-red-400 uppercase">{reg.regression_type}</span>
              </div>
              <p className="text-xs text-slate-300 mt-1">{reg.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
