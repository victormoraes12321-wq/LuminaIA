# LuminaAI V2 RC1 environment matrix (Prompts 19-26)

This document is the release-candidate inventory for configuration introduced by Prompts 19-26. Runtime code and `backend/config.py` remain authoritative. All values below are non-secret; real connection strings, cryptographic keys and provider keys belong only in an approved secret manager or untracked local `.env`.

## Backend variables

| Prompt | Variable | Purpose | Allowed values | Safe default | Required environments | Production restriction | Secret |
|---|---|---|---|---|---|---|---|
| 19 | — | Dashboard Blueprint V2 is contract-only. | No runtime variable. | N/A | None | No runtime activation. | no |
| 20 | `DASHBOARD_BACKEND_MODE` | Select governed dashboard backend mode. | `LEGACY_ONLY`, `SHADOW_VALIDATE`, `V2_AUTHORING`, `V2_PUBLISHED_READ`, `V2_RUNTIME` | `LEGACY_ONLY` | all | Keep `LEGACY_ONLY` until approved rollout. | no |
| 20 | `DASHBOARD_ADMIN_APIS_ENABLED` | Enable admin endpoints. | boolean | `false` | all | `false` baseline. | no |
| 20 | `DASHBOARD_RUNTIME_APIS_ENABLED` | Enable runtime endpoints. | boolean | `false` | all | `false` baseline. | no |
| 20 | `DASHBOARD_PUBLISHING_ENABLED` | Permit publish requests. | boolean | `false` | all | Requires approval and active migration. | no |
| 20 | `DASHBOARD_ROLLBACK_ENABLED` | Permit rollback requests. | boolean | `false` | all | Requires approval and active migration. | no |
| 20 | `DASHBOARD_COLLABORATORS_ENABLED` | Permit collaborator management. | boolean | `false` | all | Requires approval and RBAC. | no |
| 20 | `DASHBOARD_RUNTIME_CACHE_ENABLED` | Enable governed runtime cache. | boolean | `false` | all | Off until certified. | no |
| 20 | `DASHBOARD_MATERIALIZATION_ENABLED` | Enable governed materialization. | boolean | `false` | all | Off until certified. | no |
| 20 | `DASHBOARD_AUDIT_ENABLED` | Enable V2 audit surfaces. | boolean | `false` | all | Off until schema and retention approval. | no |
| 20 | `DASHBOARD_LEGACY_IMPORT_DRY_RUN_ENABLED` | Permit dry-run legacy import. | boolean | `false` | development, test, staging | Production activation requires explicit approval; never persists in dry-run. | no |
| 20 | `DASHBOARD_TENANT_ALLOWLIST` | Restrict eligible tenants. | JSON/list of tenant UUIDs | `[]` | all | Empty is fail-closed. | no |
| 22 | `DASHBOARD_AI_ASSISTANCE_MODE` | Select governed AI-assistance mode. | `LEGACY_ONLY`, `SHADOW_ANALYZE`, `AI_PROPOSAL_PREVIEW`, `AI_DRAFT_CREATE`, `AI_ASSISTED_EDIT` | `LEGACY_ONLY` | all | Keep `LEGACY_ONLY` until approved rollout. | no |
| 22 | `DASHBOARD_AI_APIS_ENABLED` | Enable AI assistance endpoints. | boolean | `false` | all | `false` baseline. | no |
| 22 | `DASHBOARD_AI_FRONTEND_ENABLED` | Expose AI assistance capability. | boolean | `false` | all | Backend capability still authoritative. | no |
| 22 | `DASHBOARD_AI_FAKE_PROVIDER_ENABLED` | Use deterministic fake provider. | boolean | `false` | test only | Prohibited by production validator. | no |
| 22 | `DASHBOARD_AI_FEEDBACK_ENABLED` | Enable proposal feedback. | boolean | `false` | all | Off until governance approval. | no |
| 22 | `DASHBOARD_AI_EVALUATIONS_ENABLED` | Enable AI proposal evaluation. | boolean | `false` | test, staging | Off in production baseline. | no |
| 22 | `DASHBOARD_AI_TENANT_ALLOWLIST` | Restrict eligible tenants. | JSON/list of tenant UUIDs | `[]` | all | Empty is fail-closed. | no |
| 22 | `DASHBOARD_AI_MAX_INPUT_CHARACTERS` | Bound prompt input. | integer 128-20000 | `4000` | all | Must remain bounded. | no |
| 22 | `DASHBOARD_AI_MAX_OUTPUT_TOKENS` | Bound model output. | integer 64-4000 | `1200` | all | Must remain bounded. | no |
| 22 | `DASHBOARD_AI_MAX_TOOL_CALLS` | Bound tool calls. | integer 0-32 | `12` | all | Must remain bounded. | no |
| 22 | `DASHBOARD_AI_MAX_DURATION_MS` | Bound request duration. | integer 100-60000 | `15000` | all | Must remain bounded. | no |
| 23 | `POST_SYNC_INSIGHTS_MODE` | Select post-sync insight mode. | `LEGACY_ONLY`, `SHADOW_DETECT`, `V2_INSIGHTS_READ`, `V2_INSIGHTS_PUBLISH`, `V2_INSIGHTS_AUTO_RUN` | `LEGACY_ONLY` | all | Keep `LEGACY_ONLY` until approved rollout. | no |
| 23 | `POST_SYNC_INSIGHTS_APIS_ENABLED` | Enable post-sync APIs. | boolean | `false` | all | `false` baseline. | no |
| 23 | `POST_SYNC_INSIGHTS_FRONTEND_ENABLED` | Expose post-sync UI. | boolean | `false` | all | Backend capability still authoritative. | no |
| 23 | `POST_SYNC_INSIGHTS_OUTBOX_CONSUMER_ENABLED` | Consume technical sync outbox. | boolean | `false` | staging only before production approval | Off in production baseline. | no |
| 23 | `POST_SYNC_INSIGHTS_AUTO_RUN_ENABLED` | Automatically run insight generation. | boolean | `false` | test, staging | Off in production baseline. | no |
| 23 | `POST_SYNC_INSIGHTS_TENANT_ALLOWLIST` | Restrict eligible tenants. | JSON/list of tenant UUIDs | `[]` | all | Empty is fail-closed. | no |
| 24 | `OBSERVABILITY_MODE` | Select observability/evaluation mode. | `LEGACY_ONLY`, `SHADOW_OBSERVE`, `V2_OBSERVABILITY_READ`, `V2_EVALUATIONS` | `LEGACY_ONLY` | all | Keep `LEGACY_ONLY` until approved rollout. | no |
| 24 | `OBSERVABILITY_APIS_ENABLED` | Enable governed observability APIs. | boolean | `false` | all | `false` baseline. | no |
| 24 | `OBSERVABILITY_FRONTEND_ENABLED` | Expose governed observability UI. | boolean | `false` | all | Backend capability still authoritative. | no |
| 25 | `WORK_QUEUE_MODE` | Select governed queue mode. | `LEGACY_ONLY`, `SHADOW_QUEUE`, `V2_BACKGROUND_JOBS`, `V2_QUEUE_ADMIN`, `V2_PERFORMANCE_CERTIFICATION` | `LEGACY_ONLY` | all | Keep `LEGACY_ONLY` until approved rollout. | no |
| 25 | `WORK_QUEUE_APIS_ENABLED` | Enable queue APIs. | boolean | `false` | all | `false` baseline. | no |
| 25 | `WORK_QUEUE_FRONTEND_ENABLED` | Expose queue UI. | boolean | `false` | all | Backend capability still authoritative. | no |
| 25 | `WORK_QUEUE_WORKER_ENABLED` | Start background worker. | boolean | `false` | test, staging | Prohibited by production validator. | no |
| 25 | `WORK_QUEUE_MAX_CONCURRENCY` | Bound global concurrency. | integer 1-100 | `10` | all | Applies only when worker is approved. | no |
| 25 | `WORK_QUEUE_PER_TENANT_CONCURRENCY` | Bound per-tenant concurrency. | integer 1-50 | `3` | all | Applies only when worker is approved. | no |
| 25 | `WORK_QUEUE_LEASE_DURATION_SECONDS` | Set job lease duration. | integer 5-3600 | `60` | all | Applies only when worker is approved. | no |
| 25 | `WORK_QUEUE_HEARTBEAT_INTERVAL_SECONDS` | Set worker heartbeat. | integer 1-600 | `15` | all | Must be below approved lease. | no |
| 25 | `WORK_QUEUE_TENANT_ALLOWLIST` | Restrict eligible tenants. | JSON/list of tenant UUIDs | `[]` | all | Empty is fail-closed. | no |
| 25 | `PERFORMANCE_CERTIFICATION_MODE` | Enable isolated certification behavior. | boolean | `false` | test, staging | Prohibited by production validator. | no |
| 26 | `SECURITY_ROLLOUT_MODE` | Select security/readiness exposure. | `LEGACY_ONLY`, `AUDIT_ONLY`, `V2_READINESS` | `LEGACY_ONLY` | all | Keep `LEGACY_ONLY` until approved rollout. | no |
| 26 | `SECURITY_ROLLOUT_APIS_ENABLED` | Enable governed security rollout APIs. | boolean | `false` | all | `false` baseline. | no |
| 26 | `ROLLOUT_EXECUTION_ENABLED` | Permit rollout execution. | boolean | `false` | staging only before production approval | Prohibited by production baseline validator. | no |
| 26 | `ROLLOUT_STAGE` | Select rollout stage. | `DISABLED`, `AUDIT_ONLY`, `SHADOW`, `INTERNAL`, `CANARY`, `EXPANDED`, `FULL`, `PAUSED`, `ROLLED_BACK` | `DISABLED` | all | Must be `DISABLED` in production baseline. | no |
| 26 | `ROLLOUT_CANARY_PERCENTAGE` | Set canary percentage. | integer 0-100 | `0` | staging only before production approval | Must be `0` in production baseline. | no |
| 26 | `ROLLOUT_CANARY_TENANT_ALLOWLIST` | Restrict canary tenants. | JSON/list of tenant UUIDs | `[]` | all | Must be empty in production baseline. | no |
| 26 | `V2_GLOBAL_EMERGENCY_DISABLE` | Global fail-closed switch. | boolean | `true` | all | Keep `true` until approved rollout. | no |
| 26 | `KILL_SWITCH_DASHBOARD_V2_READ` | Disable V2 dashboard reads. | boolean | `true` | all | Keep `true` until approved rollout. | no |
| 26 | `KILL_SWITCH_DASHBOARD_V2_AUTHORING` | Disable V2 dashboard authoring. | boolean | `true` | all | Keep `true` until approved rollout. | no |
| 26 | `KILL_SWITCH_DASHBOARD_AI` | Disable dashboard AI. | boolean | `true` | all | Keep `true` until approved rollout. | no |
| 26 | `KILL_SWITCH_POST_SYNC_INSIGHTS` | Disable post-sync insights. | boolean | `true` | all | Keep `true` until approved rollout. | no |
| 26 | `KILL_SWITCH_OBSERVABILITY_V2` | Disable V2 observability. | boolean | `true` | all | Keep `true` until approved rollout. | no |
| 26 | `KILL_SWITCH_EVALUATIONS_V2` | Disable V2 evaluations. | boolean | `true` | all | Keep `true` until approved rollout. | no |
| 26 | `KILL_SWITCH_WORK_QUEUE_V2` | Disable V2 queue. | boolean | `true` | all | Keep `true` until approved rollout. | no |
| 26 | `KILL_SWITCH_PERFORMANCE_CERTIFICATION` | Disable performance certification. | boolean | `true` | all | Keep `true` until approved rollout. | no |

## Frontend variables

| Prompt | Variable | Purpose | Allowed values | Safe default | Required environments | Production restriction | Secret |
|---|---|---|---|---|---|---|---|
| 21 | `DASHBOARD_UI_MODE` | Server-side dashboard UI guard. | `LEGACY_ONLY`, `V2_PREVIEW`, `V2_READ`, `V2_AUTHORING`, `V2_SIDE_CHAT` | `LEGACY_ONLY` | all | Server and backend capabilities remain authoritative. | no |
| 21 | `DASHBOARD_UI_PREVIEW_ALLOWLISTED` | Permit preview in production. | boolean | `false` | production | Without `true`, production preview fails to `LEGACY_ONLY`; approval still required. | no |
| 21 | `NEXT_PUBLIC_DASHBOARD_UI_MODE` | Public ergonomic UI mirror. | same UI modes | `LEGACY_ONLY` | all | Never grants access. | no |
| 22 | `DASHBOARD_AI_ASSISTANCE_MODE` | Server-side AI UI guard. | same AI modes as backend | `LEGACY_ONLY` | all | Backend capability remains authoritative. | no |
| 22 | `NEXT_PUBLIC_DASHBOARD_AI_ASSISTANCE_MODE` | Public ergonomic AI mirror. | same AI modes as backend | `LEGACY_ONLY` | all | Never grants access. | no |
| 23 | `NEXT_PUBLIC_POST_SYNC_INSIGHTS_MODE` | Public post-sync UI mode. | same post-sync modes as backend | `LEGACY_ONLY` | all | Never grants access. | no |
| 23 | `NEXT_PUBLIC_POST_SYNC_INSIGHTS_APIS_ENABLED` | Client API ergonomics. | boolean | `false` | all | Never grants access. | no |
| 23 | `NEXT_PUBLIC_POST_SYNC_INSIGHTS_FRONTEND_ENABLED` | Client visibility ergonomics. | boolean | `false` | all | Never grants access. | no |
| 24 | `NEXT_PUBLIC_OBSERVABILITY_MODE` | Public observability UI mode. | same observability modes as backend | `LEGACY_ONLY` | all | Never grants access. | no |
| 24 | `NEXT_PUBLIC_OBSERVABILITY_APIS_ENABLED` | Client API ergonomics. | boolean | `false` | all | Never grants access. | no |
| 24 | `NEXT_PUBLIC_OBSERVABILITY_FRONTEND_ENABLED` | Client visibility ergonomics. | boolean | `false` | all | Never grants access. | no |

## Environment permissions

| Feature | Development | Test | Homologation / staging | Production baseline |
|---|---|---|---|---|
| Prompt 19 Blueprint contract | Permitted for validation; no runtime | Permitted | Permitted | Contract only |
| Prompt 20 dashboard backend | Default off; local explicit opt-in | Permitted with disposable DB | Permitted only with migration, allowlist and approval | `LEGACY_ONLY`, APIs off |
| Prompt 21 dashboard UI | Default off; preview permitted | Permitted with mocked API | Permitted only with backend capability | `LEGACY_ONLY`; preview not allowlisted |
| Prompt 22 dashboard AI | Default off; fake provider only locally/test | Permitted with fake provider | Shadow/preview only by approval | `LEGACY_ONLY`; fake provider prohibited |
| Prompt 23 post-sync insights | Default off | Permitted with mocked Oracle and outbox | Shadow/read only by approval | `LEGACY_ONLY`; consumer and auto-run off |
| Prompt 24 observability/evaluations | Default off | Permitted | Shadow/read by approval | `LEGACY_ONLY`, APIs/UI off |
| Prompt 25 queue/performance | Default off | Permitted against disposable infrastructure | Certification only in isolated staging | `LEGACY_ONLY`; worker and certification prohibited |
| Prompt 26 rollout/security | Audit/readiness permitted locally | Permitted | Audit/shadow/canary only by separate approval | `LEGACY_ONLY`; execution off; stage disabled; canary 0; allowlist empty; all kill switches on |

## Fail-closed production baseline

Production remains blocked from V2 activation: every mode is `LEGACY_ONLY`, the worker and performance certification are disabled, rollout execution is disabled, rollout stage is `DISABLED`, canary is `0`, allowlists are empty, and the global/feature kill switches remain enabled. Migration execution, worker startup, canary activation and production rollout require separate operational approval and are not authorized by RC-01.1.
