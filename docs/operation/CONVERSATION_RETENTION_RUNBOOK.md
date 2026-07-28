# Conversation Retention Runbook

## Safety And Defaults

Retention operates only on PostgreSQL conversation tables. It never opens
Oracle or calls OpenAI. Automatic scheduling is disabled by default through
`CONVERSATION_RETENTION_JOB_ENABLED=false`; Prompt 08 delivers the callable
service without activating a production job.

Legacy import is separately controlled by
`CONVERSATION_LEGACY_IMPORT_ENABLED=false`. Do not enable it as part of a
retention rollout.

- active TTL: 24 hours;
- archive threshold: 30 days;
- soft-delete threshold: 180 days;
- purge threshold: 365 days;
- purge batch: 100;
- maximum nodes: 10,000;
- maximum protected content: 12,000 bytes.

Threshold order is validated at startup. Until a governed tenant policy
provider exists, platform defaults are authoritative.

## Daily Procedure

1. Confirm migration v12 and schema verification.
2. Confirm environment and rollout mode.
3. Run `ConversationStateService.run_retention(dry_run=True)`.
4. Investigate unexpected candidate volume.
5. Apply one bounded batch only after approval.
6. Monitor duration, lock waits, failures and remaining candidates.

Purge uses deterministic ordering, short transactions and `SKIP LOCKED`.
Active sessions are never purge candidates. Expired sessions reject new turns.
Foreign-key cascades remove nodes, snapshots, events and ciphertext at purge.

## Incidents

- Checksum mismatch: stop mutation, preserve rows and inspect prior snapshots.
- Abandoned turn: preserve the last valid snapshot; never inherit partial state.
- Head or parent mismatch: treat as an integrity incident, not an auto-repair.
- Retention failure: rollback the batch and leave scheduling disabled.

## Rollback

Operational rollback is `CONVERSATION_STATE_MODE=LEGACY_ONLY`; retain v12 data
for diagnosis. Never use destructive down migration operationally.
`migration_v12_0.py down --confirm-test-only` is guarded for disposable test
databases.
