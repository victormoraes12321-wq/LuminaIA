# LuminaAI V2 RC2 Remediation Manifest

## Identity

- Base tag: `lumina-v2-rc1`
- Base SHA: `21cd3ba1895b6111d4a04e1b5ff7d9701cd85181`
- Branch: `codex/lumina-v2-rc2-remediation`
- Candidate identity: the commit containing this manifest
- Intended commit message: `fix: restore deployed analytical truth parity`
- RC2 tag: not created by this remediation task
- Push: not performed

## Authorized changes

- analytical V2 compatibility intent and entity-filter resolution;
- deterministic core routing and fact-state handling;
- tenant-scoped PostgreSQL analytical aggregation and cardinality;
- closed parity/failure/path contracts;
- 30-case HTTP parity and zero/provider regression tests;
- typed resolution-path metadata for the existing numerical corpus;
- RC2 remediation documentation.

## Explicit exclusions

- migrations and schema changes;
- dependency and lockfile changes;
- frontend behavior changes;
- `backend/services/blueprints.json` changes;
- RC1 tag changes;
- RC2 tag creation;
- production, real tenant, Oracle or real provider access;
- staging deployment, workers, load tests, canary or rollout.

## Reproducibility inputs

- repository-owned numerical corpus;
- repository-owned disposable PostgreSQL bootstrap and v1–v26 migrations;
- repository-owned safe backend test runner;
- provider and Oracle disabled/mock boundaries;
- `LEGACY_ONLY` conversation mode;
- authenticated synthetic users and server-derived tenant identity.

External HOMO evidence is read-only context and is not a test dependency.
