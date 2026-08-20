# LuminaAI V2 RC1 release manifest

- Certification: `RC-01.2`
- Date: `2026-08-11`
- Branch: `codex/lumina-v2-release-candidate`
- Candidate: `21cd3ba1895b6111d4a04e1b5ff7d9701cd85181`
- Source authority: fresh `git archive` of the exact candidate
- Decision: `LUMINA V2 RC1 — FULL_SUITE_CERTIFIED`
- RC1 checkpoint: `AUTHORIZED`
- Future homologation/staging checkpoint: `AUTHORIZED`
- Production, rollout, tag and push: `NOT AUTHORIZED`

## Candidate identity and hygiene

| Gate | Result |
|---|---|
| Raw archive SHA-256 | `7bd6bba1efad2ec1fb5974b295d651bba6814cca798595e0c7145444f85c4bfb` |
| Archive files | 1,668 |
| Real `.env` | 0; two safe templates present |
| `venv` / `.venv` | 0 |
| Runtime logs / scratch / test reports | 0 at extraction |
| Operational credential artifacts | 0 |
| Required personal paths | 0 |
| Real secrets | 0; historical classification remains `SYNTHETIC_ONLY` |
| Environment matrix | 67 documented rows, 66 unique variables; shared dashboard AI mode is intentional |
| Prompt 19–26 corpora/docs | present |

The original worktree was never used as release source. Existing local environment files, virtual environments, logs, whitepapers, scripts and tracked modifications were preserved and excluded from the candidate execution.

## Reproducibility and build

| Gate | Result |
|---|---|
| Portability | PASS |
| Dependency manifests | no local/file links; no new dependencies |
| `npm ci --offline` | PASS; 454 packages, 0 vulnerabilities |
| Python environment | declared dependencies validated with the existing external Python 3.12.10 toolchain; `pip check` PASS; fresh offline install unavailable because the pip cache was empty |
| Python AST | 853/853 parsed; 0 errors |
| ESLint | PASS; 0 errors, 13 existing warnings |
| TypeScript | PASS; 0 errors |
| Frontend build R1 | PASS; 38.83 s |
| Frontend build R2 | PASS; 33.38 s |
| Routes | 29 total; 21 static; 8 dynamic; identical between builds |
| Docker Compose test config | PASS |

## Database and runtime

PostgreSQL was disposable and bound only to `127.0.0.1:55432/luminaai_test`. The operational database, host port 5432 and Oracle were not accessed.

| Gate | Result |
|---|---|
| Initial database | empty; 0 application tables; migration ledger absent |
| Core baseline | 28 tables; 140 migration-owned tables excluded from `create_all` |
| Migration chain | v12.0 through v26.0 PASS |
| Second migration run | PASS; no duplicate object or schema drift |
| Migration integrity | PASS; canonical aggregate `19b04af000f396227914215c4d6290eedf9b2483e79146dcc66037503ad5f712` |
| Structural counts | 174 tables, 2,083 columns, 169 PKs, 198 FKs, 148 uniques, 249 checks, 587 indexes, 44 trigger events |
| Structural manifest | reproducible; final R1/R2 `b642bd10dd11d7f37508dda02c74855ae614a309533805959fb89d2a46d6be51` |
| Ledger | records v12.0–v16.0 by implementation; v17–v26 entrypoints applied; declared target v26 |
| Synthetic state | 3 tenants, 8 users, 17 sales facts, plus conversation, dashboard, insight, observability, queue, cache and materialization records |
| Startup/liveness/readiness | PASS; healthy and ready in `LEGACY_ONLY` |
| Controlled DB failure | liveness remained healthy; readiness became degraded/false; recovery PASS |
| Missing V2 prerequisite | fail-closed, readiness false |
| Schema mismatch | v25 upgrade required, v27 too new and missing manifest all blocked readiness |
| Import side effects | 0 worker, rollout, migration, external network, Oracle or real provider starts |

## Contracts and acceptance suites

| Gate | Result |
|---|---|
| DEFAULT OpenAPI | 190 paths / 216 operations / `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b` |
| COMBINED OpenAPI | 256 paths / 289 operations / `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c` |
| Experimental paths | cache 5; dashboards 22; dashboard AI 11; post-sync 7; observability 10; queue/performance 11; missing 0 |
| Contract exporters | all 10 PASS twice; 353 files; deterministic |
| Corpus manifest | `f1ba92669b861c7ab30a50d57a81f4a4aa6b3ef9ce62ad88c53dce9a8879e4e5` |
| Numerical truth | 60/60 PASS; mismatches 0; independent SQL/Decimal oracle |
| Continuity | 5 conversations / 50 turns PASS; contamination 0 |
| Typo | 25/25 PASS; 21 resolve, 3 clarify, 1 reject |
| Impossible | 15/15 PASS; fabricated answer/metric/source 0 |
| Causality | 10/10 PASS; overclaims 0 |
| Security Prompt 26 | 36 PASS; unresolved CRITICAL/HIGH 0 |
| Directed subsystem matrix | 334 PASS |
| Backend full suite | 2,088 PASS; 0 failed/errors/skipped/xfailed/XPASS; 2 Pydantic deprecation warnings; 1,725.08 s |
| Playwright | 432 PASS; 0 failed/skipped; desktop/tablet/mobile/ultrawide; 844.47 s |

## Backup, restore and shared-state smoke

The authoritative cycle used a data-only custom dump, excluded only the migration ledger recreated by migrations and omitted one test-created ephemeral table from the restore list.

| Gate | Result |
|---|---|
| Dump | PASS; 71,486 bytes; SHA-256 `f954a8cdb63f9ff6cc968f85f258fdf9139c82f54d69d468876c765a791667a0` |
| Manifest A | `f46921e5b71d1577f8e26dc6350efe066619ad1bdf7c54b01b7f562268cc5cfd` |
| Restore | empty DB → core baseline → v12–v26 → data restore; PASS |
| Manifest B | `f46921e5b71d1577f8e26dc6350efe066619ad1bdf7c54b01b7f562268cc5cfd` |
| Equality | Manifest A = Manifest B |
| Numerical recheck | 10 before / 10 after; 0 mismatches; result hash `f1288138a2fcfdf87efe3d175e2db778156e49e6b5d3f0c3f997b143ccdd4a22` |
| Post-restore startup | healthy, ready PASS |
| Restart persistence | conversation version, dashboard and queue state retained |
| Two instances | both ready on one DB; shared identity/state equal; tenants distinct; exactly one concurrent queue claimant; cache/materialization authority equal |

## Immutable authorities and production state

- Governed blueprint Git/LF SHA-256: `2f2c79e87d0b1564b3ba04f40b0aba0b05430b411edafdd6064028a7e2403744`.
- Windows/CRLF representation, recorded separately: `bc29edcd9cf0973cb580a49d081f8dd4773c1cb20877da7d50f299e39821a63b`.
- Dependencies and lockfiles are unchanged; migration v27 is absent.
- Real OpenAI, Oracle, operational database, host port 5432, real provider and external network accesses: 0.
- Production remains `OFF / LEGACY_ONLY`; emergency disable and kill switches active; worker/performance/rollout disabled; stage `DISABLED`; canary 0 and allowlist empty; production migrations 0.
- No functional product bug was discovered or fixed. Harness/environment incidents were corrected without changing candidate source.
- No commit, tag, push, stage, branch switch or production action was performed.

## Decision

`21cd3ba1895b6111d4a04e1b5ff7d9701cd85181` is certified as LuminaAI V2 RC1. This authorizes the RC1 checkpoint and a future, separately approved homologation/staging phase. It does not start homologation, production, rollout, canary, worker, migration, tag or push.
