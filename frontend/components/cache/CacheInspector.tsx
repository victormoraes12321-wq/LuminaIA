'use client';

import React, { useState } from 'react';
import { CacheStatisticsV2, CacheEvictionResultV2 } from '../../types/smart_cache_materialization';

interface CacheInspectorProps {
  stats: CacheStatisticsV2 | null;
  onRunGc: (dryRun: boolean) => Promise<CacheEvictionResultV2 | null>;
  onInvalidateTag: (tag: string) => Promise<boolean>;
}

export const CacheInspector: React.FC<CacheInspectorProps> = ({
  stats,
  onRunGc,
  onInvalidateTag,
}) => {
  const [tagInput, setTagInput] = useState('');
  const [gcResult, setGcResult] = useState<CacheEvictionResultV2 | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleGc = async (dryRun: boolean) => {
    setIsProcessing(true);
    const res = await onRunGc(dryRun);
    setGcResult(res);
    setIsProcessing(false);
  };

  const handleInvalidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tagInput.trim()) return;
    setIsProcessing(true);
    await onInvalidateTag(tagInput.trim());
    setTagInput('');
    setIsProcessing(false);
  };

  return (
    <div className="space-y-6 text-slate-100" id="cache-inspector-panel">
      <div className="flex items-center justify-between border-b border-slate-700 pb-4">
        <div>
          <h2 className="text-xl font-bold text-cyan-400">Inspeção de Cache Inteligente V2</h2>
          <p className="text-sm text-slate-400">
            Monitoramento de hit rate, retenção, chaves auditáveis e descarte de entradas expiradas.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleGc(true)}
            disabled={isProcessing}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 text-xs font-semibold rounded"
          >
            GC Dry-Run
          </button>
          <button
            onClick={() => handleGc(false)}
            disabled={isProcessing}
            className="px-3 py-1.5 bg-cyan-700 hover:bg-cyan-600 text-white text-xs font-semibold rounded"
          >
            Executar GC
          </button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
            <span className="text-xs text-slate-400 font-semibold block">Total Lookups</span>
            <span className="text-2xl font-bold text-slate-100">{stats.total_lookups}</span>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
            <span className="text-xs text-slate-400 font-semibold block">Hit Rate</span>
            <span className="text-2xl font-bold text-emerald-400">
              {(stats.hit_rate * 100).toFixed(1)}%
            </span>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
            <span className="text-xs text-slate-400 font-semibold block">Entradas Ativas</span>
            <span className="text-2xl font-bold text-cyan-300">{stats.active_entries_count}</span>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
            <span className="text-xs text-slate-400 font-semibold block">Bytes em Cache</span>
            <span className="text-2xl font-bold text-amber-400">
              {(stats.active_payload_bytes / 1024).toFixed(1)} KB
            </span>
          </div>
        </div>
      )}

      {gcResult && (
        <div className="p-3 bg-slate-800/80 border border-cyan-500/30 rounded text-sm text-cyan-200">
          <strong>Resultado GC ({gcResult.dry_run ? 'Simulação' : 'Executado'}):</strong>{' '}
          {gcResult.evicted_count} entradas expiradas identificadas,{' '}
          {(gcResult.bytes_freed / 1024).toFixed(1)} KB liberados.
        </div>
      )}

      <form onSubmit={handleInvalidate} className="bg-slate-900 p-4 rounded-lg border border-slate-800 space-y-3">
        <h3 className="text-sm font-bold text-slate-200">Invalidação Seletiva por Tag de Dependência</h3>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Ex: dataset:vendas ou metric:faturamento"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-700 px-3 py-1.5 text-sm text-slate-100 rounded focus:outline-none focus:border-cyan-500"
          />
          <button
            type="submit"
            disabled={isProcessing || !tagInput.trim()}
            className="px-4 py-1.5 bg-rose-700 hover:bg-rose-600 disabled:opacity-50 text-white text-xs font-semibold rounded"
          >
            Invalidar Tag
          </button>
        </div>
      </form>
    </div>
  );
};
