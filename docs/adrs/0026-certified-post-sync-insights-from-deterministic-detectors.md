# 26. Certified Post-Sync Insights from Deterministic Detectors

- **Status:** Accepted
- **Date:** 2026-08-06
- **Context:** Following data synchronization and reconciliation, enterprise users require timely, certified, explainable insights regarding metric changes, target achievements, threshold breaches, ranking movements, and data quality issues.

## Decision

We adopt `lumina.post-sync-insights/1.0` as the canonical contract for post-sync insights:
1. Insights are generated exclusively from 10 static, deterministic detectors.
2. Financial calculations remain in `Decimal` and avoid LLM-generated values.
3. Outbox and execution are tenant-scoped and fail-closed under `LEGACY_ONLY`.

## Consequences

- Zero uncertified insights enter the public feed.
- Production remains `LEGACY_ONLY` until full rollout approval in Prompt 26.
