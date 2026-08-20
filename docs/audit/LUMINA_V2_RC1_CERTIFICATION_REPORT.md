# LuminaAI V2 RC1 certification report

Date: `2026-08-11`. Candidate: `21cd3ba1895b6111d4a04e1b5ff7d9701cd85181` on `codex/lumina-v2-release-candidate`.

## Executive decision

**LUMINA V2 RC1 — FULL_SUITE_CERTIFIED**

**RC1 CHECKPOINT — AUTHORIZED**

**HOMOLOGATION/STAGING — AUTHORIZED FOR A FUTURE SEPARATELY APPROVED ACTION**

The certification used only a fresh `git archive` of the exact SHA. The original dirty worktree, local environments and uncommitted files were not release inputs. Production remains off and no tag, push, rollout or migration is authorized.

## Evidence summary

- Archive: 1,668 files; SHA-256 `7bd6bba1efad2ec1fb5974b295d651bba6814cca798595e0c7145444f85c4bfb`.
- Hygiene: real env 0, venv 0, runtime logs 0, credential artifacts 0, scratch/reports 0, personal runtime dependencies 0, real secrets 0.
- Portability: PASS. The external Python 3.12.10 environment supplied declared dependencies only; all source/config/fixtures came from the archive. The local pip cache could not support a fresh offline install; `pip check` and the complete suite passed. `npm ci --offline` installed 454 packages with 0 vulnerabilities.
- Static/build: 853 AST files, 0 errors; lint 0 errors/13 warnings; TypeScript PASS; two builds PASS with identical 29-route structure.
- Database: empty start; 28 core tables; v12–v26 PASS twice; 174 tables, 2,083 columns, 169 PKs, 198 FKs, 148 uniques, 249 checks, 587 indexes and 44 trigger events.
- Runtime: startup/liveness/readiness PASS; DB-loss, missing V2 prerequisite and schema mismatch fail closed; import side effects 0.
- OpenAPI: DEFAULT 190/216 at `ab2ed7a6…`; COMBINED 256/289 at `c4f7c673…`; experimental path counts 5/22/11/7/10/11 and missing 0.
- Acceptance: numerical 60/60; continuity 50/50; typo 25/25; impossible 15/15; causality 10/10; no mismatches, contamination, fabrication or causal overclaim.
- Directed backend: Prompt 26 security 36 PASS; cross-subsystem matrix 334 PASS.
- Backend full: 2,088 passed, 0 failed/errors/skipped/xfailed/XPASS, 2 deprecation warnings, 1,725.08 seconds.
- Browser: 432 passed, 0 failed/skipped, four viewports, 844.47 seconds. Pending tenant switch/logout, refresh, back/forward, repeated submit, accessibility and sanitized error states passed.
- Backup/restore: dump PASS; Manifest A and B both `f46921e5…`; 10 numerical checks before/after equal; post-restore startup and restart persistence PASS.
- Two-instance: both ready on the same database; identity/state equal, tenants isolated, one queue claimant, shared cache/materialization authority.
- Forbidden accesses: OpenAI 0, Oracle 0, operational DB 0, port 5432 access 0, real provider 0, external network 0.
- Bugs: no product bug; unresolved CRITICAL/HIGH/MEDIUM/LOW all 0.

## Execution incidents and disposition

Three non-product incidents were observed and resolved without changing candidate code:

1. The first backend full run had one portability-test failure because the previously executed Playwright suite had generated its reports inside the clean tree. Those generated directories were moved outside the tree; no product assertion failed.
2. The second backend full run was externally terminated near completion when Docker Desktop stopped. Docker was restarted without image pull and the suite was rerun from the clean tree.
3. The first post-restore harness used the test bootstrap helper, which allowed migration-owned models into `Base.metadata.create_all` and created duplicate equivalent indexes. That disposable database was discarded. The authoritative cycle recreated only 28 core tables, excluded 140 migration-owned tables, applied v12–v26 and restored the dump. Its final schema exactly matches the audited counts.

Several rejected harness attempts — invalid synthetic JSON, missing synthetic OpenAI variable, an incorrect migration import namespace, an omitted `pg_restore` user and an unsupported PowerShell encoding name — failed before their affected transaction or operation and were corrected. They do not represent candidate defects.

## Deterministic artifacts

| Artifact | Evidence |
|---|---|
| Archive | `7bd6bba1efad2ec1fb5974b295d651bba6814cca798595e0c7145444f85c4bfb` |
| DEFAULT OpenAPI | `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b` |
| COMBINED OpenAPI | `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c` |
| Migrations v12–v26 | `19b04af000f396227914215c4d6290eedf9b2483e79146dcc66037503ad5f712` |
| Final schema R1/R2 | `b642bd10dd11d7f37508dda02c74855ae614a309533805959fb89d2a46d6be51` |
| RC corpora | `f1ba92669b861c7ab30a50d57a81f4a4aa6b3ef9ce62ad88c53dce9a8879e4e5` |
| Backup manifest A/B | `f46921e5b71d1577f8e26dc6350efe066619ad1bdf7c54b01b7f562268cc5cfd` |
| Numerical subset before/after | `f1288138a2fcfdf87efe3d175e2db778156e49e6b5d3f0c3f997b143ccdd4a22` |
| Blueprint Git/LF | `2f2c79e87d0b1564b3ba04f40b0aba0b05430b411edafdd6064028a7e2403744` |

All ten contract exporters passed in two cycles. The final set contains 353 files. Regeneration on Windows produces expected CRLF representation differences; eight generated files also incorporate current Prompt 26 security enums or currently registered OpenAPI component schemas. The two exporter cycles were identical, so the gate is deterministic; no candidate runtime source was modified.

## Commands and outcomes

The executed families were: Git read-only locks and `git archive`; redacted hygiene/path/secret scans; offline dependency checks; AST, lint, TypeScript and two Next builds; Docker Compose validation; guarded PostgreSQL bootstrap/migrations/introspection; isolated uvicorn health/readiness probes; clean-process OpenAPI export; all contract/corpus exporters; directed pytest matrices; complete backend pytest; full Playwright; `pg_dump`/database recreation/migrations/`pg_restore`; restart and two-instance concurrency probes.

The backend full suite's authoritative third run returned exit 0 with `2088 passed, 2 warnings in 1725.08s`. Playwright returned exit 0 with `432 passed` in 844.47 seconds.

## Not executed

- No fresh offline Python installation: pip cache unavailable; the external declared-dependency environment was used as toolchain.
- No `npm run test:load`: it targets a running backend/load environment and was not authorized for this isolated RC certification.
- No installer, operational start/stop scripts, host firewall change, cache cleanup or operational port termination.
- No Oracle, real OpenAI/provider, external network, operational PostgreSQL, host port 5432, production migration, worker, canary, rollout, homologation start, tag, commit or push.

## Dependencies, migrations and Git

No dependency, lockfile or migration changed; v27 is absent. The only intentional RC-01.2 worktree changes are this report and the release manifest, both left unstaged and uncommitted. All unrelated local modifications and untracked files remain preserved.

## Final production posture

Production is `OFF / LEGACY_ONLY`. Global emergency disable and feature kill switches remain active. Queue worker and performance certification are disabled. Rollout execution is disabled, stage is `DISABLED`, canary percentage is 0, canary allowlist is empty, and production migrations executed are 0.

This report certifies only the exact SHA and authorizes the RC1 checkpoint plus a future separately controlled homologation/staging phase. It does not perform or authorize production activation.
