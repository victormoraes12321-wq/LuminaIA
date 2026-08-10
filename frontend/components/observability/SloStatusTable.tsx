'use client'

import React from 'react'
import type { SloEvaluationV2 } from '@/types/observability_v2'

interface Props {
  evaluations: SloEvaluationV2[]
}

export function SloStatusTable({ evaluations }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 mb-6" data-testid="slo-status-table">
      <h3 className="text-lg font-bold text-slate-100 mb-4">Status dos SLOs Governaos</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-800 text-xs uppercase text-slate-400">
            <tr>
              <th className="p-3">SLO ID</th>
              <th className="p-3">Meta (%)</th>
              <th className="p-3">Atual (%)</th>
              <th className="p-3">Budget Restante</th>
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {evaluations.map((e) => (
              <tr key={e.slo_id} className="hover:bg-slate-800/40">
                <td className="p-3 font-mono text-xs text-slate-200">{e.slo_id}</td>
                <td className="p-3 font-mono text-slate-400">{e.target_percentage}%</td>
                <td className="p-3 font-mono font-bold text-emerald-400">{e.current_percentage}%</td>
                <td className="p-3 font-mono text-blue-300">{e.error_budget.remaining_budget_percentage}%</td>
                <td className="p-3">
                  <span
                    className={`px-2 py-0.5 text-xs font-bold rounded ${
                      e.status === 'HEALTHY'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : e.status === 'AT_RISK'
                        ? 'bg-amber-950 text-amber-400 border border-amber-800'
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}
                  >
                    {e.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
