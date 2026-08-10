'use client'

import React from 'react'
import type { OperationalMetricDefinitionV2, OperationalMetricRollupV2 } from '@/types/observability_v2'

interface Props {
  definitions?: OperationalMetricDefinitionV2[]
  rollups: OperationalMetricRollupV2[]
}

export function OperationalMetricSummary({ definitions: _definitions, rollups }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 mb-6" data-testid="operational-metric-summary">
      <h3 className="text-lg font-bold text-slate-100 mb-4">Métricas Operacionais Registradas</h3>
      {rollups.length === 0 ? (
        <div className="text-slate-400 text-sm py-4" data-testid="metrics-empty">Nenhum rollup de métrica operacional registrado nesta janela.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800 text-xs uppercase text-slate-400">
              <tr>
                <th className="p-3">Métrica</th>
                <th className="p-3">Count</th>
                <th className="p-3">Soma</th>
                <th className="p-3">Min</th>
                <th className="p-3">Max</th>
                <th className="p-3">Média</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {rollups.map((r, i) => (
                <tr key={i} className="hover:bg-slate-800/40">
                  <td className="p-3 font-mono text-xs text-blue-300">{r.metric_id}</td>
                  <td className="p-3 font-mono">{r.count}</td>
                  <td className="p-3 font-mono">{r.sum_value}</td>
                  <td className="p-3 font-mono">{r.min_value}</td>
                  <td className="p-3 font-mono">{r.max_value}</td>
                  <td className="p-3 font-mono">{r.avg_value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
