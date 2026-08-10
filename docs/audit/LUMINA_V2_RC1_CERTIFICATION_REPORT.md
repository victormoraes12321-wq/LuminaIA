# LuminaAI V2 RC-01.1 remediation report

Date: 2026-08-10. Initial checkpoint: `150743f8c926973416a5e33155ea11922e52f707`. The remediation is limited to RC-01 blockers. Production remains off and no tag or push is authorized.

## Root causes and resolutions

- Source hygiene: a real `.env`, local virtualenv, runtime logs and one credential-named operational report were historically tracked. They were removed from the index without deleting local copies; ignore rules and manifest tests prevent recurrence.
- Portability: two executable scripts used workstation-specific paths, an exporter test depended on an uncommitted interpreter, and a migration immutability test compared platform line endings. Repository-relative paths, `sys.executable`, LF canonicalization and regressions resolve these defects.
- Readiness: `/health/deep` treated every component as required, read the wrong AI status key and counted test-disabled scheduler/provider states as degradation. Requiredness is now explicit and mode-aware; required PostgreSQL/config/schema failures remain fail-closed.
- Acceptance evidence: deterministic synthetic corpora and five missing pending-request/navigation/error browser journeys are now versioned and separately runnable.
- Environment documentation: safe templates and a 67-variable Prompt 19-26 matrix now document defaults, allowed values, environment constraints, production restrictions and secret classification.

## Historical secret exposure assessment

Removed artifact contents are never printed or copied into this report. Redacted metadata classified the historical `.env` and credential report as `SYNTHETIC_ONLY`; `CREDENTIAL_ROTATION_REQUIRED=false`. Three existing source candidates found by token-pattern scanning are deterministic exporter/performance placeholders and also classify `SYNTHETIC_ONLY`. Real secret findings in the staged tree are zero. History was not rewritten. Production remains blocked until a production security review confirms the assessment.

## Mandatory 87-field report

1. status: `RC-01.1 REMEDIATED; RC-01 RE-RUN AUTHORIZED`.
2. branch: `codex/lumina-v2-release-candidate`.
3. initial HEAD: `150743f8c926973416a5e33155ea11922e52f707`.
4. worktree entries: 36 expanded entries at remediation start; all 29 pre-existing local inputs preserved.
5. RC fixes discovered: 4 prior fixes (two personal-path sites, interpreter portability, CRLF/LF canonicalization) plus 4 RC blocker groups (source hygiene, readiness, corpora/browser evidence, environment matrix).
6. tracked `backend/.env` before: 1.
7. tracked `backend/.env` after: 0.
8. local `backend/.env` preserved: yes.
9. tracked venv files before: 2,752.
10. tracked venv files after: 0.
11. local venv preserved: yes (`backend/venv` and untracked `backend/.venv`).
12. tracked runtime logs before: 69.
13. tracked runtime logs after: 0.
14. credential-named files: one operational report removed from tracking; source modules with governed credential logic are not classified as credential artifacts.
15. secret classification: `SYNTHETIC_ONLY`; staged real secret findings 0.
16. credential rotation required: false on available evidence; production review remains mandatory.
17. `.gitignore` changes: ignore real env, `backend/venv/`, operational credential report, runtime logs, scratch and test reports; preserve safe examples and synthetic fixtures.
18. environment template: backend and frontend safe examples present; secret values are `<required-secret>` only.
19. personal path fixes: 2 source sites fixed; required personal absolute paths 0.
20. migration CRLF/LF fix: historical hash comparison canonicalizes CRLF to LF; migration files themselves unchanged.
21. health/deep root cause: optional/disabled components were aggregated as required and AI status used a non-existent key.
22. health/deep resolution: explicit `required_in_current_mode`, policy-disabled neutral state, mode-aware schema compatibility, required dependencies fail closed.
23. LEGACY_ONLY readiness: `healthy`, `ready_for_traffic=true` with healthy PostgreSQL.
24. failure readiness: controlled PostgreSQL failure yields `degraded`, `ready_for_traffic=false`; `/health` remains healthy.
25. numerical corpus count: 60.
26. numerical corpus hash: `f1ba92669b861c7ab30a50d57a81f4a4aa6b3ef9ce62ad88c53dce9a8879e4e5`.
27. numerical corpus test result: 60/60 cases passed independent test-only SQL/Decimal oracle.
28. continuity conversations: 5.
29. continuity turns: 50.
30. continuity result: 50/50 turn contracts passed.
31. typo corpus count: 25.
32. typo result: 25/25 passed (`RESOLVE`, `CLARIFY`, `REJECT`).
33. impossible corpus count: 15.
34. impossible result: 15/15 passed; fabricated answer, metric and source = 0.
35. causality corpus count: 10.
36. causality result: 10/10 passed; causal claims without evidence = 0.
37. two-view cases: 4.
38. three-view cases: 2.
39. four-plus-view cases: 2.
40. browser RC journeys: login/chat/continuity/dashboard/refresh reused; 5 missing journeys added (tenant switch during request, logout during request, back/forward, repeated action, error state), 20 viewport executions passed.
41. environment variables documented: 67 across backend/frontend Prompts 19-26; Prompt 19 is explicitly contract-only with no runtime variable.
42. directed readiness tests: 23 passed, 0 failed/skipped/xfailed; staged portability+readiness 9 passed.
43. backend collected: 2,088 in the full staged-tree run.
44. backend passed: 2,088.
45. backend failed: 0.
46. backend skipped: 0 (also 0 errors/xfailed/XPASS); 2 historical Pydantic warnings.
47. Playwright total: 432.
48. Playwright passed: 432.
49. Playwright failed: 0.
50. Playwright skipped: 0.
51. lint: PASS, 0 errors / 13 historical warnings.
52. TypeScript: PASS, 0 errors.
53. build: PASS.
54. AST: staged source 853 parsed / 0 errors.
55. Docker: `docker compose -f docker-compose.test.yml config -q` PASS.
56. DEFAULT OpenAPI: 190 paths / 216 operations / `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b`, identical twice.
57. COMBINED OpenAPI: 256 paths / 289 operations / `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c`, identical twice.
58. migrations: unchanged; no migration created or executed by RC-01.1.
59. dependencies: unchanged (`backend/requirements.txt` and `frontend/package.json`).
60. lockfiles: unchanged (`frontend/package-lock.json`).
61. blueprints: unchanged; SHA-256 `bc29edcd9cf0973cb580a49d081f8dd4773c1cb20877da7d50f299e39821a63b`.
62. staged files: 2,851 expected after final documentation staging.
63. staged removals: 2,823 (2,752 venv, 69 logs, `.env`, credential report).
64. staged additions: 18 expected after final documentation staging.
65. staged secret scan: 0 real findings; 3 existing deterministic source placeholders classified `SYNTHETIC_ONLY`.
66. staged hygiene: PASS; real env, venv, runtime logs, credential report and scratch absent; safe templates present.
67. staged portability: PASS, 4/4 in worktree and included in staged 9/9 preflight.
68. new commit message: `fix: harden RC portability, readiness and acceptance corpora`.
69. new full SHA: recorded in the post-commit release handoff; a commit cannot self-reference its own SHA.
70. clean archive: required post-commit audit and recorded in the release handoff.
71. archive `.env`: required absent by the post-commit audit.
72. archive venv: required absent by the post-commit audit.
73. archive logs: required absent by the post-commit audit.
74. archive credential files: required absent by the post-commit audit.
75. archive scratch: required absent by the post-commit audit.
76. archive corpora: required present by the post-commit audit.
77. archive env docs: required present by the post-commit audit.
78. tags: 0 new; six existing tags unchanged.
79. pushes: 0.
80. production: OFF / unauthorized.
81. rollout: disabled / unauthorized.
82. canary: 0 / unauthorized.
83. worker: disabled / unauthorized.
84. production migration: not executed / unauthorized.
85. historical secret risk: `SYNTHETIC_ONLY`; no automatic history rewrite; production re-review required.
86. production security gate: BLOCKED until a future approved production process; all kill switches remain enabled.
87. final decision: `RC-01 RE-RUN AUTHORIZED` after exact commit and clean-archive confirmation in the handoff; production remains blocked and unauthorized.

## Commands and outcomes

Git inventory/removal used index-only operations and preserved physical files. Corpora exporters were run twice with equal hashes. Directed pytest ran against local PostgreSQL test port 55432 with Oracle/OpenAI/network disabled. Frontend lint, TypeScript, build and Playwright ran on isolated port 3100. Staged export used `git checkout-index`; staged hygiene, portability, AST, OpenAPI and readiness passed. No backup/restore rerun was performed because RC-01.1 explicitly authorizes staged preflight instead.

## Not executed

No installer, operational start/stop, load test, Oracle, real provider, external network, host PostgreSQL 5432, production migration, worker, canary, rollout, tag or push was executed. These actions are outside remediation scope or explicitly prohibited.
