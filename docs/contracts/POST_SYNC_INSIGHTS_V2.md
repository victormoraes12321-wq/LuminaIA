# Governed Post-Sync Insights V2 Specification

**Contract Version:** `lumina.post-sync-insights/1.0`
**Status:** Certified & Active
**Scope:** Deterministic, tenant-isolated post-sync analytical insights.

---

## 1. Overview

Post-Sync Insights V2 transforms a completed and reconciled data synchronization into a small, certified, explainable set of tenant-scoped analytical insights.

## 2. Detectors

1. `MetricChangeDetector`
2. `TargetAttainmentDetector`
3. `ThresholdBreachDetector`
4. `RankingMovementDetector`
5. `RobustAnomalyDetector`
6. `FreshnessDegradationDetector`
7. `CompletenessDegradationDetector`
8. `ReconciliationVarianceDetector`
9. `SourceVolumeChangeDetector`
10. `NewDataAvailableDetector`

## 3. Governance Guarantees

- Zero uncertified insights published to feed.
- Zero floating point calculations (uses `Decimal`).
- Zero LLM-generated numbers.
- Fail-closed in `LEGACY_ONLY` mode.
- User-scoped acknowledgement and dismissal.
