'use client';

import React from 'react';
import { PublicProvenanceSummaryV2 } from '@/types/validation_provenance';

interface PublicProvenancePanelProps {
  summary: PublicProvenanceSummaryV2;
  onClose: () => void;
}

export const PublicProvenancePanel: React.FC<PublicProvenancePanelProps> = ({ summary, onClose }) => {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      role="dialog"
      aria-labelledby="provenance-title"
      aria-modal="true"
    >
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4 text-slate-100">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <span className="text-emerald-400 text-xl font-bold">✓</span>
            <h3 id="provenance-title" className="text-lg font-semibold tracking-wide">
              Origem dos Dados e Proveniência
            </h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Fechar painel de proveniência"
            className="text-slate-400 hover:text-slate-200 text-sm px-2 py-1 rounded bg-slate-800"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3 text-sm">
          <div>
            <span className="text-slate-400 block text-xs uppercase font-medium">Métricas Utilizadas</span>
            <p className="font-medium text-slate-200">{summary.metric_names.join(', ') || 'N/A'}</p>
          </div>

          <div>
            <span className="text-slate-400 block text-xs uppercase font-medium">Período</span>
            <p className="font-medium text-slate-200">{summary.period_description || 'Período Solicitado'}</p>
          </div>

          <div>
            <span className="text-slate-400 block text-xs uppercase font-medium">Fonte dos Dados</span>
            <p className="font-medium text-slate-200">{summary.data_source_description}</p>
          </div>

          <div>
            <span className="text-slate-400 block text-xs uppercase font-medium">Status da Validação</span>
            <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
              {summary.validation_status}
            </span>
          </div>

          {summary.truncated && (
            <div className="p-3 bg-amber-950/40 border border-amber-800/50 rounded-lg text-amber-300 text-xs">
              ⚠️ <strong>Aviso:</strong> O resultado foi truncado devido aos limites operacionais de exibição.
            </div>
          )}

          {summary.warnings.length > 0 && (
            <div className="space-y-1">
              <span className="text-slate-400 block text-xs uppercase font-medium">Alertas</span>
              <ul className="list-disc list-inside text-xs text-amber-300 space-y-0.5">
                {summary.warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="pt-2 border-t border-slate-800 flex justify-between text-xs text-slate-500 font-mono">
            <span>Contrato: {summary.contract_version}</span>
            <span>Checksum: {summary.certification_checksum.slice(0, 12)}...</span>
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};
