# Knowledge Governance Runbook

## Preconditions

1. Confirm a tested backup and approved maintenance window.
2. Confirm `ENTERPRISE_KNOWLEDGE_MODE=LEGACY_ONLY`.
3. Confirm the target is the tenant-scoped PostgreSQL database, never Oracle.
4. Run the complete isolated test baseline.
5. Review migration v13 and its verification output.

## Migration Rollout

Do not use `create_all` as the production migration mechanism.

```powershell
cd backend
.\venv\Scripts\python.exe database\migration_v13_0.py up
.\venv\Scripts\python.exe database\migration_v13_0.py verify
```

The command is operational and must only be run after approval. Prompt 10 ran
it only against PostgreSQL at `127.0.0.1:55432/luminaai_test`.

## Flag Rollout

1. `LEGACY_ONLY`: migration present, all V2 behavior inactive.
2. `SHADOW_READ`: compare published semantic candidates structurally.
3. `V2_READ`: expose published/effective knowledge to runtime and glossary.
4. Enable `ENTERPRISE_KNOWLEDGE_FRONTEND_ENABLED`.
5. `V2_READ_WRITE`: enable human workflow for an initial tenant.
6. Enable import/export/cache separately only after metrics and audit review.

Never enable `ENTERPRISE_KNOWLEDGE_EMERGENCY_OVERRIDE` as a normal rollout
step.

## Publishing

1. Author creates or edits a draft.
2. Author submits with the current lock version.
3. A distinct reviewer approves the exact checksum.
4. An ADMIN publishes with the current lock version.
5. Verify the current pointer, publication event, aliases and cache
   invalidation.
6. For metric/KPI assets, verify `MetricRegistry` binding is `VALID` or the
   approved descriptive status.

## Rollback

Application rollback:

1. Select a prior `PUBLISHED` or `DEPRECATED` version.
2. Create a new rollback draft.
3. Repeat review and publication.
4. Confirm the historical versions remain unchanged.

Operational rollback:

1. Set `ENTERPRISE_KNOWLEDGE_MODE=LEGACY_ONLY`.
2. Hide the frontend V2.
3. Preserve v13 data for investigation.

Schema down is prohibited in production. It exists only for the guarded
disposable test database:

```powershell
python database\migration_v13_0.py down --confirm-test-only
```

## Incident Checks

- Draft visible to CONSULTA: immediately return to `LEGACY_ONLY`, inspect role
  and lifecycle filters.
- Formula conflict: keep publication blocked; compare fingerprint with
  `MetricRegistry`.
- Alias ambiguity: preserve all equal candidates and request clarification.
- Version conflict: reload the latest draft and reapply the intended edit.
- Cross-tenant symptom: disable V2 reads and inspect composite FKs and tenant
  predicates.
- Search cache anomaly: disable cache and invalidate the affected tenant.

## Monitoring

Track structural counters only:

- assets, drafts, pending reviews, approvals, rejections and publications;
- rollbacks, version conflicts, access denied and binding conflicts;
- alias ambiguity, search latency/candidate count and cache invalidations;
- imports, exports, mode and contract version.

Do not log question text, definitions, review comments, datasets, SQL, binds,
credentials or business values.

## Retention

Published history and audit events are append-only business governance
records. Retention or purge policy is not introduced by Prompt 10. Any future
policy requires legal approval, a separate migration and tested rollback.
