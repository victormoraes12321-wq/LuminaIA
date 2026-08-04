'use client';

import React, { useState } from 'react';

interface Props {
  data?: any;
  onSimulate?: (query: string) => void;
}

export default function OrchestrationInspector({ data, onSimulate }: Props) {
  const [testQuery, setTestQuery] = useState('faturamento de junho de 2026');

  return (
    <div className="p-6 bg-slate-900 text-slate-100 rounded-xl shadow-2xl border border-slate-800 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-emerald-400">Inspector da Orquestracao de IA</h2>
          <p className="text-sm text-slate-400">Versao do contrato: lumina.ai-orchestration/1.0</p>
        </div>
        <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 text-xs font-semibold rounded-full border border-emerald-500/20">
          Governed State Machine Active
        </span>
      </div>

      {/* Simulator bar */}
      <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 flex items-center gap-3">
        <input
          type="text"
          value={testQuery}
          onChange={(e) => setTestQuery(e.target.value)}
          placeholder="Digite uma pergunta sintetica para inspecionar..."
          className="flex-1 bg-slate-900 border border-slate-700 text-slate-100 px-4 py-2 rounded-md text-sm focus:outline-none focus:border-emerald-500"
        />
        <button
          onClick={() => onSimulate && onSimulate(testQuery)}
          className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-4 py-2 rounded-md text-sm transition-colors"
        >
          Simular Inspecao
        </button>
      </div>

      {/* Breakdown Grid */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Estrategia & Status</h3>
            <p className="text-lg font-bold text-slate-100">{data.strategy || 'SINGLE_MODEL_CALL'}</p>
            <p className="text-sm text-emerald-400 font-mono mt-1">{data.status || 'COMPLETED'}</p>
          </div>
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Consumo de Tokens</h3>
            <p className="text-lg font-bold text-slate-100">{data.token_usage?.total_actual_tokens || 0} tokens</p>
            <p className="text-xs text-slate-400 mt-1">
              Input: {data.token_usage?.actual_input_tokens || 0} | Output: {data.token_usage?.actual_output_tokens || 0}
            </p>
          </div>
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Tempo de Execucao</h3>
            <p className="text-lg font-bold text-slate-100">{data.execution_time_ms ? `${data.execution_time_ms.toFixed(2)} ms` : 'N/A'}</p>
            <p className="text-xs text-slate-400 mt-1">Orcamento maximo: 30.000 ms</p>
          </div>
        </div>
      )}

      {/* Facts section */}
      {data?.facts && data.facts.length > 0 && (
        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
          <h3 className="text-sm font-semibold text-slate-300">Fatos Estruturados Validados (Decimal Authority)</h3>
          <div className="divide-y divide-slate-800">
            {data.facts.map((fact: any, idx: number) => (
              <div key={idx} className="py-2 flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">{fact.metric_id}</span>
                <span className="text-emerald-400 font-bold">{fact.fact_value_formatted}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
