export const OBSERVABILITY_CONFIG = {
  contractVersion: "lumina.observability-metrics-evaluations/1.0",
  mode: process.env.NEXT_PUBLIC_OBSERVABILITY_MODE || "LEGACY_ONLY",
  apisEnabled: process.env.NEXT_PUBLIC_OBSERVABILITY_APIS_ENABLED === "true",
  frontendEnabled: process.env.NEXT_PUBLIC_OBSERVABILITY_FRONTEND_ENABLED === "true",
};
