'use client';

import React, { useState } from 'react';
import { MaterializationPublicationV2 } from '../../types/smart_cache_materialization';

interface MaterializationInspectorProps {
  onPublish: (definitionId: string, snapshotId: string) => Promise<MaterializationPublicationV2 | null>;
  onRollback: (definitionId: string, toSnapshotId: string) => Promise<boolean>;
}

export const MaterializationInspector: React.FC<MaterializationInspectorProps> = ({
  onPublish,
  onRollback,
}) => {
  const [defId, setDefId] = useState('');
  const [snapId, setSnapId] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [pubResult, setPubResult] = useState<MaterializationPublicationV2 | null>(null);

  const handlePublishSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!defId.trim() || !snapId.trim()) return;
    setIsProcessing(true);
    const res = await onPublish(defId.trim(), snapId.trim());
    setPubResult(res);
    setIsProcessing(false);
  };

  const handleRollbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!defId.trim() || !snapId.trim()) return;
    setIsProcessing(true);
    await onRollback(defId.trim(), snapId.trim());
    setIsProcessing(false);
  };

  return (
    <div className="space-y-6 text-slate-100" id="materialization-inspector-panel">
      <div className="border-b border-slate-700 pb-4">
        <h2 className="text-xl font-bold text-cyan-400">Materialização Analítica Governada V2</h2>
        <p className="text-sm text-slate-400">
          Publicação atômica de snapshots analíticos pré-computados com prova factual e rollback.
        </p>
      </div>

      <form onSubmit={handlePublishSubmit} className="bg-slate-900 p-4 rounded-lg border border-slate-800 space-y-4">
        <h3 className="text-sm font-bold text-slate-200">Publicação Atômica de Snapshot</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">Definition ID</label>
            <input
              type="text"
              placeholder="Ex: def_faturamento_mensal"
              value={defId}
              onChange={(e) => setDefId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 px-3 py-1.5 text-sm text-slate-100 rounded focus:outline-none focus:border-cyan-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">Snapshot ID</label>
            <input
              type="text"
              placeholder="Ex: snap_faturamento_v2"
              value={snapId}
              onChange={(e) => setSnapId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 px-3 py-1.5 text-sm text-slate-100 rounded focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={isProcessing || !defId.trim() || !snapId.trim()}
            className="px-4 py-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white text-xs font-semibold rounded"
          >
            Publicar Snapshot
          </button>
          <button
            type="button"
            onClick={handleRollbackSubmit}
            disabled={isProcessing || !defId.trim() || !snapId.trim()}
            className="px-4 py-1.5 bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white text-xs font-semibold rounded"
          >
            Rollback para Snapshot
          </button>
        </div>
      </form>

      {pubResult && (
        <div className="p-4 bg-slate-900 border border-emerald-500/40 rounded-lg text-sm text-emerald-300">
          <strong>Snapshot Publicado com Sucesso:</strong> Definition {pubResult.definition_id} → Active Snapshot {pubResult.active_snapshot_id} (Publicado em {pubResult.published_at})
        </div>
      )}
    </div>
  );
};
