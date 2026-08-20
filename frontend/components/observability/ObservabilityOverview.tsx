'use client'

import React from 'react'
import type { ObservabilitySummaryV2 } from '@/types/observability_v2'

interface Props {
  summary: ObservabilitySummaryV2
}

export function ObservabilityOverview({ summary }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-sm mb-6" data-testid="observability-overview">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-slate-100">Painel de Observabilidade V2</h2>
        <span className="px-3 py-1 text-xs font-semibold rounded-full bg-blue-950 text-blue-300 border border-blue-800">
          {summary.mode}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800/60 p-4 rounded-md border border-slate-700">
          <div className="text-slate-400 text-xs font-medium uppercase">Status da API</div>
          <div className="text-lg font-bold text-emerald-400 mt-1">{summary.health.status}</div>
          <div className="text-xs text-slate-500 mt-1">Uptime: {summary.health.uptime_seconds}s</div>
        </div>

        <div className="bg-slate-800/60 p-4 rounded-md border border-slate-700">
          <div className="text-slate-400 text-xs font-medium uppercase">Eventos Gravados</div>
          <div className="text-lg font-bold text-slate-100 mt-1">{summary.health.events_recorded}</div>
          <div className="text-xs text-slate-500 mt-1">Descartes: {summary.health.dropped_telemetry_count}</div>
        </div>

        <div className="bg-slate-800/60 p-4 rounded-md border border-slate-700">
          <div className="text-slate-400 text-xs font-medium uppercase">SLOs Monitorados</div>
          <div className="text-lg font-bold text-indigo-400 mt-1">{summary.slo_count}</div>
          <div className="text-xs text-slate-500 mt-1">Status: Conforme</div>
        </div>

        <div className="bg-slate-800/60 p-4 rounded-md border border-slate-700">
          <div className="text-slate-400 text-xs font-medium uppercase">Suítes de Avaliação</div>
          <div className="text-lg font-bold text-purple-400 mt-1">19 suítes</div>
          <div className="text-xs text-slate-500 mt-1">Execuções: {summary.evaluation_runs_count}</div>
        </div>
      </div>
    </div>
  )
}
