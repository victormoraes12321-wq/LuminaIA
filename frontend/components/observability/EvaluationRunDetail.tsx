'use client'

import React from 'react'
import type { EvaluationRunV2 } from '@/types/observability_v2'

interface Props {
  run: EvaluationRunV2
  onClose: () => void
}

export function EvaluationRunDetail({ run, onClose }: Props) {
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50" data-testid="evaluation-run-detail-modal">
      <div className="bg-slate-900 border border-slate-800 rounded-lg max-w-3xl w-full p-6 shadow-xl max-h-[85vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold text-slate-100">Execução {run.run_id}</h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white font-bold text-lg"
            data-testid="close-modal-btn"
          >
            ✕
          </button>
        </div>

        <div className="bg-slate-800/50 p-4 rounded mb-4 text-xs font-mono grid grid-cols-2 gap-2 text-slate-300">
          <div>Suíte: {run.suite}</div>
          <div>Duração: {run.duration_ms}ms</div>
          <div>Total de casos: {run.total_cases}</div>
          <div>Checksum: {run.checksum.slice(0, 16)}...</div>
        </div>

        <h4 className="font-bold text-sm text-slate-200 mb-2">Resultados Sintéticos</h4>
        <div className="space-y-2">
          {run.results.map((res) => (
            <div key={res.result_id} className="p-3 bg-slate-800/40 rounded border border-slate-800 flex justify-between items-center">
              <div>
                <span className="font-mono text-xs font-bold text-blue-300 mr-2">{res.case_id}</span>
                <span className="text-xs text-slate-400">Duração: {res.duration_ms}ms</span>
              </div>
              <span
                className={`px-2 py-0.5 text-xs font-bold rounded ${
                  res.outcome === 'PASS' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-red-950 text-red-400 border border-red-800'
                }`}
              >
                {res.outcome}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
