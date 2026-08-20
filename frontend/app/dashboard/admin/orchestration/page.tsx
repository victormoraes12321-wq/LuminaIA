'use client';

import React, { useEffect, useState } from 'react';
import OrchestrationInspector from '@/components/orchestration/OrchestrationInspector';
import { getApiBase } from '@/lib/utils';

export default function AIOrchestrationAdminPage() {
  const [models, setModels] = useState<any[]>([]);
  const [prompts, setPrompts] = useState<any[]>([]);
  const [inspectionResult, setInspectionResult] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchData = async () => {
    try {
      const apiBase = getApiBase();
      const [modelsRes, promptsRes] = await Promise.all([
        fetch(`${apiBase}/api/v2/ai-orchestration/models`, { credentials: 'include' }),
        fetch(`${apiBase}/api/v2/ai-orchestration/prompts`, { credentials: 'include' }),
      ]);
      if (modelsRes.ok) {
        const mData = await modelsRes.json();
        setModels(mData);
      }
      if (promptsRes.ok) {
        const pData = await promptsRes.json();
        setPrompts(pData);
      }
    } catch (err) {
      console.error('Error fetching AI Orchestration admin data:', err);
    }
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const handleSimulate = async (userQuery: string) => {
    setLoading(true);
    try {
      const apiBase = getApiBase();
      const res = await fetch(`${apiBase}/api/v2/ai-orchestration/inspector/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ user_query: userQuery }),
      });
      if (res.ok) {
        const simData = await res.json();
        setInspectionResult(simData.response);
      }
    } catch (err) {
      console.error('Simulation error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 bg-slate-950 min-h-screen text-slate-100">
      <header className="space-y-2">
        <h1 className="text-3xl font-extrabold text-slate-50 tracking-tight">
          Painel de Orquestracao de IA e Controle de Tokens
        </h1>
        <p className="text-slate-400 text-sm">
          Governanca de modelos de linguagem, mascaras de sistema, limites de tokens e simulacao inspecionavel.
        </p>
      </header>

      {/* Inspector Simulator */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-slate-200">Simulador & Inspector</h2>
        <OrchestrationInspector data={inspectionResult} onSimulate={handleSimulate} />
      </section>

      {/* Registered Models & Prompts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <section className="bg-slate-900 p-6 rounded-xl border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-slate-200">Modelos Canonicos Registrados</h3>
          <div className="space-y-3">
            {models.map((m, idx) => (
              <div key={idx} className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between items-center text-xs font-mono">
                <div>
                  <p className="font-bold text-emerald-400">{m.canonical_model_id}</p>
                  <p className="text-slate-500">Provider: {m.provider_id}</p>
                </div>
                <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded">Ativo</span>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-slate-900 p-6 rounded-xl border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-slate-200">Prompt Templates Server-Controlled</h3>
          <div className="space-y-3">
            {prompts.map((p, idx) => (
              <div key={idx} className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono space-y-1">
                <p className="font-bold text-slate-200">{p.template_id}</p>
                <p className="text-slate-400 text-[11px]">{p.description}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
