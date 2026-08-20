# Post-Sync Insights V2 Runbook

## Configuration Flags

- `POST_SYNC_INSIGHTS_MODE`: `LEGACY_ONLY` (default), `SHADOW_DETECT`, `V2_INSIGHTS_READ`, `V2_INSIGHTS_PUBLISH`, `V2_INSIGHTS_AUTO_RUN`.
- `POST_SYNC_INSIGHTS_APIS_ENABLED`: `false` (default)
- `POST_SYNC_INSIGHTS_FRONTEND_ENABLED`: `false` (default)

## Operational Tasks

1. **Replay Run (ADMIN only):**
   ```http
   POST /api/v2/post-sync-insights/runs/{run_id}/replay
   ```

2. **Check Policies:**
   ```http
   GET /api/v2/post-sync-insights/policies
   ```
