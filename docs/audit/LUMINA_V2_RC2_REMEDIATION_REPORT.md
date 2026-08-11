# LuminaAI V2 RC2 Remediation Report

## Scope and immutable baseline

- Finding scope: `HOMO-BUG-0001` and `HOMO-BUG-0002` only.
- Immutable RC1 tag: `lumina-v2-rc1`.
- Immutable RC1 SHA: `21cd3ba1895b6111d4a04e1b5ff7d9701cd85181`.
- Remediation branch: `codex/lumina-v2-rc2-remediation`.
- Production, real tenants, Oracle, real AI provider, staging workers, rollout and production migrations were not used.
- `LEGACY_ONLY` remains the conversation-state authority. The remediation invokes the already-versioned analytical V2 contract adapter as a compatibility boundary; it does not enable PostgreSQL conversation authority, semantic retrieval rollout or another V2 rollout mode.

## Reproduced deployed baseline

The official first 30 cases in `backend/tests/fixtures/rc1/numerical_truth.json` were run through a real local Uvicorn HTTP server, authenticated synthetic users and the disposable PostgreSQL clone with migrations through v26.

| Result | Count | Case IDs |
| --- | ---: | --- |
| Passed | 7 | NUM-011, NUM-012, NUM-013, NUM-015, NUM-016, NUM-017, NUM-018 |
| Failed | 23 | NUM-001–NUM-010, NUM-014, NUM-019–NUM-030 |

The reproduced baseline matched HOMO-01 exactly: 7/30 passed and 23/30 failed. No external evidence file is required by the committed regression tests.

## Root-cause aggregation

| Primary cause | Count | Affected cases | First divergent stage | Common code path |
| --- | ---: | --- | --- | --- |
| `INTENT_RESOLUTION` | 16 | NUM-001–006, NUM-019–022, NUM-025–030 | `INTENT_RESOLVED` | `NewQueryOrchestrator.run_pipeline` applied the generic revenue-basis ambiguity interception before the governed core capability; entity values were dimensions but not canonical filters. |
| `PROVIDER_FALLBACK` | 6 | NUM-007–010, NUM-023–024 | `PROVIDER_REQUIRED` | Quantity aliases and the governed default revenue metric for an explicit seller total were absent, so supported questions reached `ai_credential_manager.resolve_client`. |
| `ZERO_DEFAULT` | 1 | NUM-014 | `TEMPORAL_RESOLUTION`, surfaced at `RESPONSE_RENDERED` | “Historical” produced no singular time window, the core executor silently substituted the current month, and a zero denominator became `Decimal("0")`. |

Unknown root causes: **0**.

## The 0.00 versus 155.00 defect

`NUM-014` requests governed commercial average ticket over all available history for tenant A. The synthetic fixture proves five distinct commercial orders and commercial revenue of BRL 775.00, hence `Decimal("775.00") / Decimal(5) = Decimal("155.00")`.

The baseline lost the historical scope before execution, queried the empty current month and converted the absent denominator to zero. The fix recognizes the governed all-history scope, keeps tenant filtering in SQL, records source and commercial row cardinality, and resolves ratios through an explicit numerical fact policy. `NO_ROWS`, `NULL` and `NOT_APPLICABLE` no longer serialize as a numerical zero.

## Runtime remediation

1. The analytical contract adapter now recognizes the already-governed `unidades_vendidas` metric and emits typed equality filters for explicit numeric seller, branch and product identifiers.
2. “Total” plus an explicit governed sales entity receives the registry-backed commercial revenue default; no question or case ID lookup exists.
3. The new-query orchestrator constructs a deterministic compatibility intent when structured conversation authority is unavailable. Supported deterministic intent takes precedence over generic provider fallback and the obsolete revenue-basis popup.
4. Filtered scalar dimensions no longer become rankings. Seller, branch and product values remain bind parameters and tenant remains server-derived.
5. The PostgreSQL breakdown executor supports the governed entity scope, all-history scope, quantity aggregation and explicit row cardinality.
6. Numerical fact states are closed: `VALUE`, `ZERO`, `NULL`, `NO_ROWS`, `NOT_APPLICABLE`, `UNSUPPORTED`, `BLOCKED`, `ERROR` and `PARTIAL`.
7. The parity harness uses closed stage, failure-cause and expected-resolution-path enums and compares sanitized fingerprints without SQL, binds, credentials or raw datasets.

## Zero-default audit

The contextual static scan found 178 `or 0`, 68 `get(..., 0)` and 148 `default=0`-style occurrences in backend runtime Python. Most are counters, collection indexes, configuration limits or presentation defaults and do not establish analytical truth.

Five dangerous truth-default patterns affected this path and were fixed:

- empty aggregate rows indistinguishable from real zero;
- commercial average-ticket zero denominator;
- gross average-ticket zero denominator;
- commercial average-discount zero denominator;
- gross average-discount zero denominator.

Remaining zero normalization in the touched executor is limited to SQL arithmetic over rows already proven present, explicit count fields or presentation of an already-classified fact. The regression matrix proves positive, negative, legitimate zero, null, no rows, denominator-not-applicable, timeout/error, blocked, unsupported, provider unavailable and validation failure behavior with fabricated zero count equal to zero.

## Provider boundary

Before remediation, six deterministically supported cases reached the provider. After remediation, all 30 HTTP gate cases and all corresponding internal calls complete with provider calls equal to zero. A provider-required non-numerical request with the provider absent fails closed with no `chart_data` and no numerical fact.

## Findings

- `HOMO-BUG-0001`: remediated by the runtime changes and protected by the 30-case HTTP/parity regression.
- `HOMO-BUG-0002`: remediated by deterministic intent routing and the provider-call assertion.
- `HOMO-BUG-0003`: remains an environment limitation; no proxy, TLS, DNS, secret-manager or alerting claim is made.
- `HOMO-BUG-0004`: remains an environment limitation; no staging provider, staging Oracle or offline dependency-cache claim is made.

## Certification gates

The authoritative command results and clean-archive rerun are recorded in the final RC2-01 task report. This document deliberately does not authorize production, create an RC2 tag or replace the required RC2 full certification.
