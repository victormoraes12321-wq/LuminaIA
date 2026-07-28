# ADR 0011: PostgreSQL Conversation Source Of Truth

- Status: Accepted, rollout inactive
- Date: 2026-07-28

## Context

The legacy graph is process-local RAM plus JSON keyed by a client session
string. It cannot guarantee replica consistency, transactional versions,
tenant/user ownership, retention or restart recovery.

## Decision

Adopt `lumina.conversation-state/1.0` in PostgreSQL with owner-scoped sessions,
append-only nodes/events, versioned snapshots, idempotency and optimistic
compare-and-swap. Encrypt permitted content with Fernet and persist only
minimal analytical references.

Rollout is one enum. Production remains `LEGACY_ONLY` in Prompt 08. In
PostgreSQL-authoritative modes, client history and local JSON are compatibility
inputs only.

## Consequences

Multiple replicas can resume state without shared RAM and concurrent completion
is explicit. Migration, key management, retention and monitoring are required.
Native RLS remains unconfirmed, so repository scoping and constraints are
mandatory. Advanced semantic inheritance remains a Prompt 09 concern.
