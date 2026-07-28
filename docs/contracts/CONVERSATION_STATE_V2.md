# Conversation State V2

## Contract

- Version: `lumina.conversation-state/1.0`.
- Authority when enabled: tenant and user scoped PostgreSQL.
- Production default in Prompt 08: `LEGACY_ONLY`.
- Oracle, OpenAI, analytical SQL and datasets are outside this module.

The strict internal contracts live in
`backend/contracts/conversation_state_v2/`. The active snapshot reuses the
analytical V2 metric, dimension, filter, time, comparison and visualization
references.

## State And Persistence

`ConversationStateV2` records context epoch/version, active analytical
references, subject, readiness, fingerprints, node references, field origins
and context markers. It never stores datasets, SQL, binds, credentials,
provider payloads or chain of thought.

Migration `v12.0` creates:

- `conversation_sessions`: owner, status, version/CAS, head and TTL;
- `conversation_nodes`: append-only graph nodes and idempotency;
- `conversation_state_snapshots`: typed materialized state;
- `conversation_events`: content-free audit events;
- `conversation_legacy_imports`: explicit import ledger.

Constraints enforce owner linkage, same-session parent/head, unique sequence
and client-message IDs, snapshot versions and valid statuses. Native
PostgreSQL RLS is not claimed; every repository operation requires tenant and
user.

## Transactions And Integrity

Turn start and completion are separate short transactions. No database lock is
held while the analytical pipeline runs. Completion checks the base context
version, appends the response, performs compare-and-swap, creates a snapshot
and moves the head. Out-of-order completion returns a typed conflict.

Checksums use SHA-256 over canonical JSON with sorted keys and without volatile
`updated_at`. They detect corruption and are not an authentication control.

Allowed raw text is encrypted with the installed Fernet provider. The key
stays in secure configuration and only its version is stored. Missing keys
fail closed. Secret-like content, executable SQL and policy-disabled content
are redacted while retaining a fingerprint.

## Public API

`QueryRequest` adds optional `client_message_id` and
`expected_context_version`. `QueryResponse` adds session, query/response node,
parent, context version/epoch, status, replay and warning metadata.

Owner-scoped endpoints:

- `POST /api/v1/conversations`
- `GET /api/v1/conversations`
- `GET /api/v1/conversations/{session_id}`
- `GET /api/v1/conversations/{session_id}/nodes`
- `POST .../reset`
- `POST .../archive`
- `POST .../reopen`
- `DELETE /api/v1/conversations/{session_id}`

Lists use bounded keyset pagination. Public responses never expose ciphertext,
SQL, snapshots or internal technical payloads.

## Rollout

`CONVERSATION_STATE_MODE` supports `LEGACY_ONLY`, `SHADOW_WRITE`,
`DUAL_WRITE_LEGACY_READ`, `POSTGRES_READ_WRITE` and `POSTGRES_ONLY`.

`CONVERSATION_RETENTION_JOB_ENABLED=false` and
`CONVERSATION_LEGACY_IMPORT_ENABLED=false` keep scheduled deletion and real
legacy import disabled by default. Import dry-run remains available for
validation; applying an import requires the explicit governed flag.

When PostgreSQL is authoritative, the orchestrator receives the structured
snapshot, ignores client history as authority and uses a stateless graph
adapter. Advanced semantic inheritance remains owned by Prompt 09.
