'use client'

import React from 'react'
import type { EvaluationRunV2 } from '@/types/observability_v2'

interface Props {
  runs: EvaluationRunV2[]
  onSelectRun: (run: EvaluationRunV2) => void
}

export function EvaluationRunList({ runs, onSelectRun }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 mb-6" data-testid="evaluation-run-list">
      <h3 className="text-lg font-bold text-slate-100 mb-4">Histórico de Execuções ({runs.length})</h3>
      {runs.length === 0 ? (
        <div className="text-slate-400 text-sm py-4" data-testid="runs-empty">Nenhuma suíte executada ainda.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800 text-xs uppercase text-slate-400">
              <tr>
                <th className="p-3">Run ID</th>
                <th className="p-3">Suíte</th>
                <th className="p-3">Casos</th>
                <th className="p-3">Passaram</th>
                <th className="p-3">Duração</th>
                <th className="p-3">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {runs.map((r) => (
                <tr key={r.run_id} className="hover:bg-slate-800/40">
                  <td className="p-3 font-mono text-xs text-blue-300">{r.run_id}</td>
                  <td className="p-3 font-mono text-xs">{r.suite}</td>
                  <td className="p-3">{r.total_cases}</td>
                  <td className="p-3 text-emerald-400 font-bold">{r.passed_cases}/{r.total_cases}</td>
                  <td className="p-3 font-mono text-xs">{r.duration_ms}ms</td>
                  <td className="p-3">
                    <button
                      onClick={() => onSelectRun(r)}
                      className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700"
                      data-testid={`view-run-btn-${r.run_id}`}
                    >
                      Detalhes
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
