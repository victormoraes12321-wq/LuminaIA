"use client";

import React from "react";
import { PostSyncInsightListItemV2 } from "@/types/post_sync_insights_v2";

interface Props {
  item: PostSyncInsightListItemV2;
  onSelect: (item: PostSyncInsightListItemV2) => void;
  onAcknowledge: (id: string) => void;
  onDismiss: (id: string) => void;
}

const severityColors: Record<string, string> = {
  CRITICAL: "bg-red-500/20 text-red-400 border-red-500/30",
  HIGH: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  MEDIUM: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  LOW: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  INFO: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

export const PostSyncInsightCard: React.FC<Props> = ({
  item,
  onSelect,
  onAcknowledge,
  onDismiss,
}) => {
  return (
    <div
      data-testid={`insight-card-${item.insight_id}`}
      className={`p-4 rounded-xl border transition-all ${
        item.is_acknowledged
          ? "bg-slate-900/40 border-slate-800 opacity-85"
          : "bg-slate-900/90 border-slate-700/80 shadow-lg hover:border-indigo-500/50"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span
          className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
            severityColors[item.severity] || severityColors.INFO
          }`}
        >
          {item.severity}
        </span>
        <span className="text-xs text-slate-400">
          {new Date(item.published_at).toLocaleDateString("pt-BR")}
        </span>
      </div>

      <h3
        onClick={() => onSelect(item)}
        className="text-sm font-semibold text-slate-100 mb-1 cursor-pointer hover:text-indigo-400"
      >
        {item.headline}
      </h3>

      <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-800/60">
        <span className="text-xs font-medium text-indigo-300">
          {item.metric_label}: {item.formatted_delta}
        </span>
        <div className="flex items-center gap-2">
          {!item.is_acknowledged && (
            <button
              data-testid={`ack-btn-${item.insight_id}`}
              onClick={() => onAcknowledge(item.insight_id)}
              className="text-xs px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              Ciente
            </button>
          )}
          {!item.is_dismissed && (
            <button
              data-testid={`dismiss-btn-${item.insight_id}`}
              onClick={() => onDismiss(item.insight_id)}
              className="text-xs px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-red-400"
            >
              Ocultar
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
