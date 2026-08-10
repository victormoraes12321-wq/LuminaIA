# LuminaAI V2 RC1 remediation manifest

- Remediation: `RC-01.1`
- Date: `2026-08-10`
- Branch: `codex/lumina-v2-release-candidate`
- Initial checkpoint: `150743f8c926973416a5e33155ea11922e52f707`
- Intended commit message: `fix: harden RC portability, readiness and acceptance corpora`
- Decision: `RC1_REMEDIATED_RE_RUN_AUTHORIZED`

## Remediated release surface

- `backend/.env`: removed from Git, physical local copy preserved.
- `backend/venv/**`: 2,752 files removed from Git, physical local environment preserved.
- `runtime-logs/**`: 69 files removed from Git, physical local logs preserved.
- `backend/reports/postgres_clone_credentials.txt`: removed from Git, physical local copy preserved.
- Safe backend and frontend environment templates are versioned; real secrets use only `<required-secret>`.
- Prompt 19-26 variables and environment permissions are documented in `LUMINA_V2_RC1_ENVIRONMENT_MATRIX.md`.

## Readiness

`/health` remains process liveness. `/health/deep` now aggregates only dependencies required by the current server-controlled mode. PostgreSQL and coherent security configuration remain required; active V2 surfaces require compatible schema objects and fail closed. A scheduler or provider disabled by test policy reports `disabled_by_policy` and does not make a healthy LEGACY_ONLY test deployment unready.

Directed readiness/configuration/migration tests: 23 passed, zero failed/skipped/xfailed. Staged-tree portability plus readiness: 9 passed. Healthy LEGACY_ONLY is ready; controlled PostgreSQL failure keeps liveness healthy and blocks readiness.

## Acceptance corpora

| Corpus | Count | Result |
|---|---:|---|
| Numerical truth | 60 | PASS against independent test-only SQL/Decimal oracle |
| Continuity | 5 conversations / 50 turns | PASS |
| Typo | 25 | PASS |
| Impossible / unsupported | 15 | PASS; fabricated answer/metric/source all false |
| Causality | 10 | PASS; causal overclaim disallowed |
| Multi-view | 4 two-view, 2 three-view, 2 four-plus-view | PASS |

Canonical corpus manifest SHA-256: `f1ba92669b861c7ab30a50d57a81f4a4aa6b3ef9ce62ad88c53dce9a8879e4e5`. Two exports were byte-identical.

## Contract and build baselines

| Gate | Result |
|---|---|
| DEFAULT OpenAPI | 190 paths / 216 operations / `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b`, reproduced twice |
| COMBINED OpenAPI | 256 paths / 289 operations / `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c`, reproduced twice |
| Staged AST | 853 parsed / 0 errors |
| Docker Compose test config | PASS |
| TypeScript | PASS |
| ESLint | PASS, 0 errors / 13 historical warnings |
| Frontend build | PASS |
| Playwright | 432/432 passed, four viewports |
| Backend full staged tree | 2,088 passed / 0 failed / 0 skipped; 2 historical warnings |

Migrations, declared dependencies, `frontend/package-lock.json` and governed blueprints are unchanged. No migration, dependency installation, tag, push, worker, canary, rollout, production migration, Oracle access, real provider call or operational database access is authorized by this remediation.

## Historical secret exposure assessment

The removed environment and credential-named artifacts were inspected only through redacted metadata and classified `SYNTHETIC_ONLY`; no value is reproduced here. Credential rotation is not required by the available evidence. Git history was not rewritten. Production remains blocked behind the existing security gate and must re-evaluate this assessment before any production rollout.

## Release decision

The staged tree passes hygiene, portability, secret-safe scan, AST, OpenAPI, readiness and the full backend suite. RC-01 may be rerun from the exact remediation commit after its clean-archive post-commit audit is recorded in the release handoff. This does not authorize staging/production rollout, canary, worker startup, production migration, tag or push.
