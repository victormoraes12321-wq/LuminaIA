import { getApiBase } from "@/lib/utils";
import {
  PostSyncInsightDetailV2,
  PostSyncInsightListItemV2,
  PostSyncInsightSeverityV2,
} from "@/types/post_sync_insights_v2";
import { POST_SYNC_INSIGHTS_CONFIG } from "./config";

export async function fetchPostSyncInsights(params?: {
  severity?: PostSyncInsightSeverityV2;
  include_dismissed?: boolean;
}): Promise<PostSyncInsightListItemV2[]> {
  if (POST_SYNC_INSIGHTS_CONFIG.mode === "LEGACY_ONLY" || !POST_SYNC_INSIGHTS_CONFIG.frontendEnabled) {
    return [];
  }

  const query = new URLSearchParams();
  if (params?.severity) query.set("severity", params.severity);
  if (params?.include_dismissed) query.set("include_dismissed", "true");

  const res = await fetch(`${getApiBase()}/api/v2/post-sync-insights?${query.toString()}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch insights: ${res.status}`);
  }

  const data = await res.json();
  return data.items || [];
}

export async function fetchPostSyncInsightDetail(insightId: string): Promise<PostSyncInsightDetailV2 | null> {
  if (POST_SYNC_INSIGHTS_CONFIG.mode === "LEGACY_ONLY" || !POST_SYNC_INSIGHTS_CONFIG.frontendEnabled) {
    return null;
  }

  const res = await fetch(`${getApiBase()}/api/v2/post-sync-insights/${insightId}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });

  if (!res.ok) return null;
  return await res.json();
}

export async function acknowledgePostSyncInsight(insightId: string, note?: string): Promise<boolean> {
  const res = await fetch(`${getApiBase()}/api/v2/post-sync-insights/${insightId}/acknowledge`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": `ack-ui-${insightId}-${Date.now()}`,
    },
    body: JSON.stringify({ note }),
    credentials: "include",
  });

  return res.ok;
}

export async function dismissPostSyncInsight(insightId: string, reason = "NOT_RELEVANT"): Promise<boolean> {
  const res = await fetch(`${getApiBase()}/api/v2/post-sync-insights/${insightId}/dismiss`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": `dsm-ui-${insightId}-${Date.now()}`,
    },
    body: JSON.stringify({ reason }),
    credentials: "include",
  });

  return res.ok;
}
