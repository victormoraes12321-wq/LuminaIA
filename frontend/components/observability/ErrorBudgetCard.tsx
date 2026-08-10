'use client'

import React from 'react'
import type { ErrorBudgetV2 } from '@/types/observability_v2'

interface Props {
  budget: ErrorBudgetV2
}

export function ErrorBudgetCard({ budget }: Props) {
  return (
    <div className="bg-slate-800/80 border border-slate-700 rounded-md p-4" data-testid={`error-budget-card-${budget.slo_id}`}>
      <div className="flex justify-between items-center mb-2">
        <span className="font-mono text-xs text-slate-300">{budget.slo_id}</span>
        <span className="text-xs font-bold text-slate-400">Meta: {budget.target_percentage}%</span>
      </div>
      <div className="w-full bg-slate-900 rounded-full h-2.5 mb-2 overflow-hidden">
        <div
          className="bg-emerald-500 h-2.5 rounded-full"
          style={{ width: `${budget.remaining_budget_percentage}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-400">
        <span>Consumido: {budget.consumed_budget_percentage}%</span>
        <span>Restante: {budget.remaining_budget_percentage}%</span>
      </div>
    </div>
  )
}
