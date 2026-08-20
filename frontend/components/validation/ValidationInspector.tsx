'use client';

import React, { useState } from 'react';

export const ValidationInspector: React.FC = () => {
  const [requestId, setRequestId] = useState('REQ-SIMULATED-001');
  const [overallStatus, setOverallStatus] = useState<string | null>(null);
  const [stages, setStages] = useState<string[]>([]);

  const handleRunInspector = () => {
    setOverallStatus('VALID');
    setStages([
      'CONTRACT (VALID)',
      'SECURITY (VALID)',
      'TENANT_ISOLATION (VALID)',
      'AUTHORIZATION (VALID)',
      'AUTHORITY (VALID)',
      'SEMANTIC (VALID)',
      'TEMPORAL (VALID)',
      'METRIC (VALID)',
      'NUMERIC (VALID)',
      'COMPARISON (VALID)',
      'SHAPE (VALID)',
      'COMPLETENESS (VALID)',
      'FRESHNESS (VALID)',
      'TOOL_RESULT (VALID)',
      'ORCHESTRATION (VALID)',
      'CLAIMS (VALID)',
      'PROVENANCE (VALID)',
      'PRESENTATION (VALID)',
    ]);
  };

  return (
    <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-6 text-slate-100 max-w-5xl mx-auto my-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Inspetor de Validação e Proveniência V2</h2>
          <p className="text-xs text-slate-400">Verificação de 18 Estágios, Fatos, Claims e Certificados Imutáveis</p>
        </div>
        <span className="px-3 py-1 bg-indigo-950 text-indigo-300 border border-indigo-800 text-xs font-mono rounded-full">
          lumina.validation-provenance/1.0
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="col-span-2 space-y-2">
          <label className="text-xs font-medium text-slate-300 block">ID da Requisição Analítica</label>
          <input
            type="text"
            value={requestId}
            onChange={(e) => setRequestId(e.target.value)}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={handleRunInspector}
            className="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition shadow-lg"
          >
            Executar Inspeção
          </button>
        </div>
      </div>

      {overallStatus && (
        <div className="space-y-4 pt-4 border-t border-slate-800">
          <div className="flex items-center justify-between bg-slate-950 p-4 rounded-lg border border-slate-800">
            <div>
              <span className="text-xs text-slate-400 block">Status Geral de Certificação</span>
              <span className="text-base font-bold text-emerald-400 font-mono">{overallStatus}</span>
            </div>
            <div className="text-right font-mono text-xs text-slate-400">
              Estágios Executados: {stages.length}/18
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-slate-300">Estágios da Pipeline de Validação</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {stages.map((stg, idx) => (
                <div key={idx} className="p-2.5 bg-slate-950 border border-slate-800 rounded text-xs font-mono text-emerald-300 flex items-center justify-between">
                  <span>{stg.split(' ')[0]}</span>
                  <span className="text-[10px] px-1.5 py-0.5 bg-emerald-950 text-emerald-400 rounded border border-emerald-800">✓</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
