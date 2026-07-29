# ADR 0012: Deterministic Context Resolution Before Planning

- Status: Accepted, rollout inactive
- Date: 2026-07-28

## Context

PostgreSQL persistence from ADR 0011 reliably stores a conversation, but it
does not decide which analytical fields a follow-up should inherit, replace
or remove. The legacy solution concatenates text and lets `SemanticPatch`
mutate a prior plan, which loses plural periods, changes output shape
incorrectly and depends on process-local graph state.

## Decision

Adopt `lumina.context-resolution/1.0` as the single deterministic authority
between `QueryIntentV2` and planning. It resolves persisted structured state
into a new intent and a typed, idempotent patch. Temporal normalization,
comparison planning, numerical execution and presentation retain their
existing authorities.

The engine is pure and receives tenant, user, session, branch, version and
time through trusted context. PostgreSQL persistence applies the resolved
state only after successful turn completion and CAS. Branches load the
snapshot selected by their parent. Total reset advances the epoch atomically.

Legacy text inheritance and `SemanticPatch` remain only behind the legacy
rollout path; semantic patches are allowlist validated.

## Consequences

Short follow-ups can preserve metric and filters while replacing periods.
Comparisons recover ordered recent periods, and drill-down changes shape
without changing the requested metric. Explicit correction/removal wins over
inheritance, conflicts fail closed, and out-of-scope questions do not destroy
the active analysis.

The state JSON gains additive fields but no table migration. Rollout requires
PostgreSQL conversation authority and explicit flags. Production remains
`LEGACY_ONLY` until migration, operational monitoring and staged rollout are
approved.

## Rejected Alternatives

- Client history as authority: not owner-scoped or concurrency-safe.
- Concatenating hidden context into the question: loses origin and plurality.
- LLM-only inheritance: non-deterministic and not an authority for filters.
- A second context database: duplicates Prompt 08 transaction semantics.
- Direct patch persistence in the engine: would apply context after failed
  analytical execution.
