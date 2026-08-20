# ADR 0013: Published And Versioned Enterprise Knowledge

- Status: Accepted
- Date: 2026-07-29
- Contract: `lumina.enterprise-knowledge/1.0`

## Context

Legacy business concepts mix mutable content, version status and numerical
formula concerns. Runtime aliases can become authoritative without a complete
human approval chain. The platform needs tenant-scoped enterprise semantics
without allowing text content to alter financial calculations or SQL.

## Decision

Adopt a parallel V2 enterprise knowledge authority with:

- stable assets and immutable content versions;
- explicit draft, review, approval, publication, deprecation and rollback;
- human separation of duties and checksum-bound decisions;
- PostgreSQL composite tenant constraints;
- published/effective-only lexical runtime;
- official `MetricRegistry` binding for metric/KPI assets;
- adapters for legacy, canonicalizer, intent and context boundaries;
- feature-gated rollout defaulting to `LEGACY_ONLY`.

The Knowledge Base is semantic authority only. Numeric formulas remain in the
metric registry and query execution remains in governed PostgreSQL
executors/catalogs.

## Consequences

Benefits:

- auditable definitions and aliases;
- no draft or rejected-content leakage;
- deterministic ambiguity;
- immutable version history and rollback without mutation;
- tenant and role isolation enforced in application and database.

Costs:

- migration v13 and operational rollout are required;
- publication requires distinct human steps;
- vector search, feedback automation and user profiles remain deferred;
- legacy and V2 paths coexist until rollout completes.

## Alternatives Rejected

- Evolving mutable legacy rows in place: unsafe compatibility and history.
- Storing executable SQL/formulas in knowledge assets: violates numeric and
  query authority.
- Automatic AI approval/publication: violates human governance.
- Embeddings in Prompt 10: deferred to Prompt 13.

## Rollback

Return the single runtime mode to `LEGACY_ONLY` and hide the V2 frontend.
Retain v13 records for audit. Schema down is restricted to disposable tests.
