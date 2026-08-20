# Phase 23–26 Checkpoint Manifest

Data da auditoria: 2026-08-10.

## Autoridade e escopo

- Branch de origem: `codex/phase-operations-prompts-23-26`.
- Base commit: `880477a980aeaef840ac0a5c66f8541eb6c7c349`.
- Tag de origem: `lumina-phase-dashboards-19-22`.
- Prompts abrangidos: 23, 24, 25, 26 e reconciliação 26.1.
- Objetivo: checkpoint Git dos artefatos já certificados; nenhuma feature nova.
- Produção: `LEGACY_ONLY`; worker, performance, rollout e canary desligados.

## Inventário de entrada

| Classe | Arquivos |
|---|---:|
| Worktree total expandido | 288 |
| Tracked modified | 35 |
| Untracked | 253 |
| Deleted/renamed | 0 |
| P23 | 56 |
| P24 | 66 |
| P25 | 49 |
| P26 | 83 |
| Certification docs existentes | 5 |
| Protected | 13 |
| Local runtime | 6 |
| Temporary/out-of-scope encoding | 10 |
| Unknown | 0 |

O próprio manifesto acrescenta um sexto `CERTIFICATION_DOC`. O staged tree
esperado contém 260 arquivos: 234 additions, 26 modifications e 0 deletions.

Dimensões do staged tree esperado:

| Dimensão | Arquivos |
|---|---:|
| Backend | 118 |
| Frontend | 25 |
| Tests | 37 |
| Docs | 112 |
| Scripts | 5 |
| Migrations | 3 |

`Tests` é subconjunto de backend/frontend e não deve ser somado às demais linhas.

## Allowlist P23 — Post-Sync Insights

- `backend/contracts/post_sync_insights_v2/**`
- `backend/database/migration_v24_0.py`
- `backend/models/post_sync_insights_v2.py`
- `backend/routers/post_sync_insights_v2.py`
- `backend/services/post_sync_insights_v2/**`
- `backend/services/sync_service.py`
- `backend/testing/test_database.py`
- `backend/tests/test_post_sync_insights_v2_*.py`
- `backend/tests/test_dashboard_ai_assistance_v2_migration_chain.py`
- `backend/tests/test_migration_v12_0.py`
- `docs/adrs/0026-certified-post-sync-insights-from-deterministic-detectors.md`
- `docs/contracts/POST_SYNC_INSIGHTS_V2.md`
- `docs/contracts/post_sync_insights_v2/**`
- `docs/operation/POST_SYNC_INSIGHTS_RUNBOOK.md`
- `frontend/app/insights/**`
- `frontend/components/insights/**`
- `frontend/lib/insights/**`
- `frontend/tests/visual/post-sync-insights.spec.ts`
- `frontend/types/post_sync_insights_v2.ts`
- `scripts/export_post_sync_insights_v2_contracts.py`

## Allowlist P24 — Observability, Metrics e Evaluations

- `backend/contracts/observability_v2/**`
- `backend/database/migration_v25_0.py`
- `backend/models/observability_v2.py`
- `backend/routers/observability_v2.py`
- `backend/services/observability_v2/**`
- `backend/tests/test_observability_v2_*.py`
- `docs/adrs/0027-governed-operational-observability-and-regression-evaluations.md`
- `docs/contracts/OBSERVABILITY_METRICS_EVALUATIONS_V2.md`
- `docs/contracts/observability_v2/**`
- `docs/operation/OBSERVABILITY_METRICS_EVALUATIONS_RUNBOOK.md`
- `frontend/app/admin/evaluations/page.tsx`
- `frontend/app/admin/observability/page.tsx`
- `frontend/components/observability/**`
- `frontend/lib/observability/**`
- `frontend/tests/visual/observability.spec.ts`
- `frontend/types/observability_v2.ts`
- `scripts/export_observability_v2_contracts.py`

## Allowlist P25 — Scale, Queues e Performance

- `backend/contracts/work_queue_v2/**`
- `backend/database/migration_v26_0.py`
- `backend/models/work_queue_v2.py`
- `backend/routers/work_queue_v2.py`
- `backend/schemas/work_queue_v2.py`
- `backend/services/work_queue_v2/**`
- `backend/tests/test_work_queue_v2_*.py`
- `docs/adrs/0028-governed-postgresql-work-queue-and-performance-harness.md`
- `docs/contracts/SCALE_QUEUES_PERFORMANCE_V2.md`
- `docs/contracts/work_queue_v2/**`
- `docs/operation/SCALE_QUEUES_PERFORMANCE_RUNBOOK.md`
- `scripts/export_work_queue_v2_contracts.py`
- `scripts/run_performance_certification.py`

## Allowlist P26 — Security, Migration e Rollout

- `backend/config.py`
- `backend/main.py`
- `backend/contracts/security_rollout_v2/**`
- `backend/routers/ai_orchestration.py`
- `backend/routers/query.py`
- `backend/routers/safe_analytical_postgresql.py`
- `backend/routers/validation_provenance.py`
- `backend/services/new_query_orchestrator.py`
- `backend/services/postgresql_clone_service.py`
- `backend/services/query_response_governance.py`
- `backend/services/security_rollout_v2/**`
- `backend/tests/test_security_rollout_v2_*.py`
- `docs/adrs/0029-governed-security-readiness-migration-compatibility-and-rollout-gates.md`
- `docs/contracts/SECURITY_MIGRATION_ROLLOUT_V2.md`
- `docs/contracts/security_rollout_v2/**`
- `docs/operation/PRODUCTION_ROLLOUT_PLAN_V2.md`
- `docs/operation/ROLLBACK_AND_INCIDENT_RUNBOOK_V2.md`
- `docs/operation/SECURITY_MIGRATION_ROLLOUT_RUNBOOK.md`
- `docs/security/SECURITY_READINESS_CHECKLIST_V2.md`
- `docs/security/THREAT_MODEL_V2.md`
- `docs/ai/README.md`
- `docs/analytical-database/README.md`
- `docs/api-reference.md`
- `docs/architecture.md`
- `docs/architecture/DEPRECATION_LEDGER.md`
- `docs/architecture/TECHNICAL_DEBT_REGISTER.md`
- `docs/backend/README.md`
- `docs/maintenance.md`
- `docs/security.md`
- `frontend/playwright.config.ts`
- `frontend/tests/visual/dashboard-ai-assistance.spec.ts`
- `frontend/tests/visual/dashboard-v2.spec.ts`
- `scripts/export_security_rollout_v2_contracts.py`

## Allowlist de certificação

- `docs/audit/PROMPT_23_POST_SYNC_INSIGHTS_REPORT.md`
- `docs/audit/PROMPT_24_OBSERVABILITY_METRICS_EVALUATIONS_REPORT.md`
- `docs/audit/PROMPT_25_SCALE_QUEUES_PERFORMANCE_REPORT.md`
- `docs/audit/PROMPT_26_SECURITY_MIGRATION_ROLLOUT_REPORT.md`
- `docs/audit/TEST_BASELINE.md`
- `docs/audit/PHASE_23_26_CHECKPOINT_MANIFEST.md`

## Migrations obrigatórias

- v24: `migration_v24_0.py`, Prompt 23, Post-Sync Insights.
- v25: `migration_v25_0.py`, Prompt 24, Observability/Evaluations.
- v26: `migration_v26_0.py`, Prompt 25, Work Queue/Performance.
- v27: ausente e proibida neste checkpoint.

As migrations v24–v26 foram certificadas antes do Prompt 26, não foram alteradas
por ele e são necessárias aos models, repositories e testes incluídos.

## Exclusões explícitas

### Protected — 13

- `.continue/mcpServers/new-mcp-server.yaml`
- `LUMINA_AI_LINKEDIN_LAUNCH_WHITEPAPER.md`
- `LUMINA_AI_SYSTEM_SPECIFICATION_FOR_AI.md`
- `LUMINA_AI_ULTIMATE_ENTERPRISE_SPECIFICATION.md`
- `docs/LUMINA_AI_LINKEDIN_LAUNCH_WHITEPAPER.md`
- `docs/LUMINA_AI_SYSTEM_SPECIFICATION_FOR_AI.md`
- `docs/LUMINA_AI_ULTIMATE_ENTERPRISE_SPECIFICATION.md`
- `iniciar_luminaai_servidor.bat`
- `instalar_luminaai_servidor.bat`
- `monitor_luminaai_servidor.bat`
- `parar_luminaai_servidor.bat`
- `scripts/deploy_helper.ps1`
- `scripts/setup_env_keys.py`

`backend/services/blueprints.json` também é protegido, mas está limpo e portanto
não integra as 288 entradas do worktree.

### Local runtime — 6

- `runtime-logs/backend-network.err.log`
- `runtime-logs/backend-network.out.log`
- `runtime-logs/frontend-network.err.log`
- `runtime-logs/frontend-network.out.log`
- `start-luminaai.ps1`
- `stop-luminaai.ps1`

### Temporary/out-of-scope — 10

- `scratch/check_openapi_combined.py`
- `scratch/check_openapi_hashes.py`
- `scratch/run_multilevel_performance.py`
- `scratch/test_backup_restore_v26.py`
- `scratch/test_concurrency_critical_suite.py`
- `scratch/test_fairness_abc.py`
- `scratch/test_migration_v26_full_suite.py`
- `backend/services/data_platform/business_layer.py` — remoção isolada de BOM.
- `backend/services/data_platform/insight_layer.py` — remoção isolada de BOM.
- `backend/tests/test_query_planner.py` — remoção isolada de BOM.

## Gates do manifesto

- Unknown: 0.
- Protected autorizado para staging: 0.
- Runtime/local autorizado para staging: 0.
- Temporary autorizado para staging: 0.
- `.env`, segredo, dump, backup, cache, log e artifact de IDE autorizados: 0.
- `backend/services/blueprints.json` autorizado: não.
- Dependências e lockfiles autorizados: 0 alterações.
- Método de staging: comandos `git add -- <allowlist>` explícitos, em grupos pequenos.
