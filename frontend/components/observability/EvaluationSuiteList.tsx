'use client'

import React from 'react'
import type { EvaluationSuiteV2 } from '@/types/observability_v2'

interface Props {
  suites: EvaluationSuiteV2[]
  onRunSuite: (kind: string) => void
}

export function EvaluationSuiteList({ suites, onRunSuite }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 mb-6" data-testid="evaluation-suite-list">
      <h3 className="text-lg font-bold text-slate-100 mb-4">Suítes de Avaliação Disponíveis ({suites.length})</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {suites.map((s) => (
          <div key={s.suite_id} className="bg-slate-800/60 p-4 rounded-md border border-slate-700 flex justify-between items-center">
            <div>
              <div className="font-bold text-sm text-slate-200">{s.title}</div>
              <div className="text-xs text-slate-400 mt-1">{s.description}</div>
              <div className="text-xs text-indigo-400 mt-2 font-mono">{s.case_count} casos sintéticos determinísticos</div>
            </div>
            <button
              onClick={() => onRunSuite(s.kind)}
              className="ml-4 px-3 py-1.5 text-xs font-semibold rounded bg-blue-600 hover:bg-blue-500 text-white transition-colors"
              data-testid={`run-suite-btn-${s.kind}`}
            >
              Executar
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
