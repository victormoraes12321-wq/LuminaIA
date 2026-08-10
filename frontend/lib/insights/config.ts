export const POST_SYNC_INSIGHTS_CONFIG = {
  contractVersion: "lumina.post-sync-insights/1.0",
  mode: process.env.NEXT_PUBLIC_POST_SYNC_INSIGHTS_MODE || "LEGACY_ONLY",
  apisEnabled: process.env.NEXT_PUBLIC_POST_SYNC_INSIGHTS_APIS_ENABLED === "true",
  frontendEnabled: process.env.NEXT_PUBLIC_POST_SYNC_INSIGHTS_FRONTEND_ENABLED === "true",
};
