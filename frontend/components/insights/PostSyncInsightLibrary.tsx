"use client";

import React, { useEffect, useState } from "react";
import {
  PostSyncInsightDetailV2,
  PostSyncInsightListItemV2,
  PostSyncInsightSeverityV2,
} from "@/types/post_sync_insights_v2";
import {
  acknowledgePostSyncInsight,
  dismissPostSyncInsight,
  fetchPostSyncInsightDetail,
  fetchPostSyncInsights,
} from "@/lib/insights/client";
import { PostSyncInsightCard } from "./PostSyncInsightCard";
import { POST_SYNC_INSIGHTS_CONFIG } from "@/lib/insights/config";

export const PostSyncInsightLibrary: React.FC = () => {
  const [items, setItems] = useState<PostSyncInsightListItemV2[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSeverity, setSelectedSeverity] = useState<PostSyncInsightSeverityV2 | "ALL">("ALL");
  const [activeInsight, setActiveInsight] = useState<PostSyncInsightDetailV2 | null>(null);
  const [refreshCount, setRefreshCount] = useState(0);

  const isEnabled =
    POST_SYNC_INSIGHTS_CONFIG.mode !== "LEGACY_ONLY" && POST_SYNC_INSIGHTS_CONFIG.frontendEnabled;

  const refresh = () => setRefreshCount((c) => c + 1);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!isEnabled) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const data = await fetchPostSyncInsights({
          severity: selectedSeverity === "ALL" ? undefined : selectedSeverity,
        });
        if (!cancelled) setItems(data);
      } catch {
        if (!cancelled) setItems([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void run();
    return () => { cancelled = true; };
  }, [isEnabled, selectedSeverity, refreshCount]);

  const handleSelect = async (item: PostSyncInsightListItemV2) => {
    const detail = await fetchPostSyncInsightDetail(item.insight_id);
    setActiveInsight(detail);
  };

  const handleAcknowledge = async (id: string) => {
    await acknowledgePostSyncInsight(id);
    refresh();
  };

  const handleDismiss = async (id: string) => {
    await dismissPostSyncInsight(id);
    refresh();
  };

  if (!isEnabled) {
    return (
      <div data-testid="insights-disabled-banner" className="p-8 text-center bg-slate-900 border border-slate-800 rounded-2xl">
        <h2 className="text-lg font-bold text-slate-200 mb-2">Feed de Insights Desativado</h2>
        <p className="text-sm text-slate-400">
          O módulo de insights pós-sincronização V2 permanece fail-closed no modo de produção.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="insights-library" className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Feed de Insights Pós-Sincronização</h1>
          <p className="text-sm text-slate-400">
            Insights analíticos determinísticos e certificados gerados após reconciliação.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-400">Severidade:</label>
          <select
            data-testid="severity-filter"
            value={selectedSeverity}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
              setSelectedSeverity(e.target.value as PostSyncInsightSeverityV2 | "ALL")
            }
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
          >
            <option value="ALL">Todas</option>
            <option value="CRITICAL">Crítica</option>
            <option value="HIGH">Alta</option>
            <option value="MEDIUM">Média</option>
            <option value="LOW">Baixa</option>
            <option value="INFO">Informativa</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div data-testid="insights-loading" className="p-12 text-center text-slate-400 text-sm">
          Carregando insights...
        </div>
      ) : items.length === 0 ? (
        <div data-testid="insights-empty" className="p-12 text-center bg-slate-900/50 border border-slate-800 rounded-2xl text-slate-400 text-sm">
          Nenhum insight encontrado para os filtros selecionados.
        </div>
      ) : (
        <div data-testid="insights-grid" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item) => (
            <PostSyncInsightCard
              key={item.insight_id}
              item={item}
              onSelect={handleSelect}
              onAcknowledge={handleAcknowledge}
              onDismiss={handleDismiss}
            />
          ))}
        </div>
      )}

      {activeInsight && (
        <div
          data-testid="insight-detail-modal"
          className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50"
        >
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-xl w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full border bg-indigo-500/20 text-indigo-300 border-indigo-500/30">
                {activeInsight.insight.category}
              </span>
              <button
                data-testid="close-modal-btn"
                onClick={() => setActiveInsight(null)}
                className="text-slate-400 hover:text-slate-200 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <h2 className="text-lg font-bold text-slate-100">{activeInsight.insight.summary.headline}</h2>
            <p className="text-sm text-slate-300">{activeInsight.insight.summary.detail}</p>

            <div className="bg-slate-950 p-4 rounded-xl space-y-2 border border-slate-800">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Evidência Certificada</h4>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                <div>Fórmula: <code className="text-indigo-300">{activeInsight.insight.evidence.formula}</code></div>
                <div>Checksum: <span className="font-mono text-slate-400">{activeInsight.insight.evidence.checksum.slice(0, 12)}...</span></div>
                <div>Período Atual: {activeInsight.insight.evidence.current_period}</div>
                <div>Período Base: {activeInsight.insight.evidence.baseline_period}</div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setActiveInsight(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 rounded-lg"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
