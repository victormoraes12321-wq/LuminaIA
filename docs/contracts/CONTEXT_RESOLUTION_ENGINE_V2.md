# Context Resolution Engine V2

## Contract

- Version: `lumina.context-resolution/1.0`.
- Implementation: `backend/services/context_resolution/`.
- Input: current `QueryIntentV2`, original question, persisted
  `ConversationStateV2` and trusted `ContextResolutionContext`.
- Output: `ContextResolutionResult`.
- Production default: disabled.
- Authority when enabled: deterministic engine plus PostgreSQL conversation
  state scoped by authenticated tenant and user.

The engine is pure. It does not persist, execute SQL, access Oracle, call
OpenAI, read datasets or calculate business values.

## Resolution Flow

```text
authenticated request
  -> TemporalNormalizer
  -> QueryIntentV2 for the current turn
  -> ContextResolutionEngine
  -> resolved QueryIntentV2 + typed ContextPatchV2
  -> planner/executor
  -> ConversationStateService completion
  -> CAS + snapshot + structural event metadata
```

`_question_with_inherited_context` remains a legacy-only adapter. The V2 path
does not concatenate inherited values into the user question.

## Trusted Context

`ContextResolutionContext` carries tenant, user, session, current node,
parent, active head, epoch, version, expected version, bounded branch path,
role, locale, timezone, injected reference time, rollout mode, flags and
limits. It rejects unknown fields. It cannot contain credentials, SQL,
datasets or client-selected authority.

Tenant, user and permission always come from authentication. `parent_id` is
validated by `ConversationStateService`, and a selected branch reads the
snapshot whose head is that parent. A sibling branch never reads the latest
snapshot from another branch.

## Relationships

The typed relationship is one of:

- `NEW_TOPIC`
- `FOLLOW_UP`
- `REFINEMENT`
- `CORRECTION`
- `REMOVAL`
- `COMPARISON_EXTENSION`
- `DRILL_DOWN`
- `ROLL_UP`
- `CLARIFICATION_ANSWER`
- `BACKTRACK`
- `BRANCH_CONTINUATION`
- `RESET`
- `OUT_OF_SCOPE`
- `UNRESOLVED`

Classification considers the current intent, persisted subject, pending
clarification, explicit fields, parent/head relation and deterministic
language markers.

## Precedence

The governed precedence is:

1. security and permission;
2. explicit reset;
3. explicit removal;
4. explicit correction;
5. current explicit value;
6. deterministic temporal normalization;
7. validated canonical resolution;
8. pending clarification answer;
9. active branch context;
10. parent context;
11. active snapshot;
12. governed deterministic default;
13. validated LLM inference;
14. legacy adapter.

Explicit values cannot be overwritten by inherited values. Removed values do
not reappear in the same turn. Defaults and LLM inference cannot replace
explicit user input.

## Field Policies

`FIELD_POLICIES` is the single registry for metrics, dimensions, filters,
periods, comparison, visualizations, subject, ordering, limit and
clarification. Each field defines inheritance, replacement, removal,
topic-change, reset, age, branch, deduplication and conflict behavior.

Important behavior:

- a short follow-up inherits a compatible metric;
- an explicit metric replaces the inherited metric;
- an explicit period replaces the active period and is also added to bounded
  recent period history;
- "compare os dois meses" uses the two most recent distinct periods in order;
- drill-down preserves metric, filters, periods and comparison;
- a same-field explicit filter replaces the previous scalar filter;
- two incompatible explicit scalar values block execution and request
  clarification;
- negation is removal, never inclusion;
- a clear domain change does not inherit an incompatible metric;
- out-of-scope turns preserve the active analytical context;
- a total reset clears analytical context and advances the epoch at
  transactional completion.

## Patch

`ContextPatchV2` contains a deterministic ID, base epoch/version/node,
timestamp from injected context, version, checksum and idempotency
fingerprint. Its operations are a discriminated union:

- set, replace, append, remove and clear field;
- reset context;
- set or resolve pending clarification;
- set active subject;
- set or clear active comparison;
- set active head reference.

There is no free-form patch dictionary. Every operation records origin,
source node, reason code, confidence and value fingerprint. The service
persists the resolved state only after successful response completion. Failed
execution does not apply the patch.

## Persistence And Concurrency

The engine does not create a persistence layer. Prompt 08 remains the sole
authority:

- turn start validates owner, parent, expected version and idempotency;
- branch state is loaded from the parent snapshot;
- no lock is held during interpretation or analytical execution;
- completion validates the base version;
- CAS validates epoch and version;
- response, state snapshot, active head and structural events commit together;
- a losing concurrent completion receives `CONTEXT_VERSION_CONFLICT`;
- retries reuse `client_message_id`.

New state fields are additive JSONB fields with defaults. No PostgreSQL schema
or migration change is required.

## Public Response

`QueryResponse` may contain:

- `context_relationship`;
- `public_context_summary`;
- `context_version` and `context_epoch`;
- existing typed conflict response on HTTP 409.

The public summary contains labels for active metrics, periods, inherited
filters, dimensions, comparison, replaced fields, removed fields, reset and
clarification. It does not expose node IDs, SQL, binds, datasets or internal
reasoning. Structural resolver telemetry is available only to `ADMIN`.

## Rollout

Flags:

- `CONTEXT_RESOLUTION_V2_ENABLED=false`
- `CONTEXT_RESOLUTION_V2_SHADOW_MODE=false`
- `CONTEXT_RESOLUTION_V2_FRONTEND_ENABLED=false`
- `CONTEXT_RESOLUTION_MAXIMUM_DEPTH=20`
- `CONTEXT_RESOLUTION_MAXIMUM_INHERITED_FIELDS=50`

The feature only authors state when V2 is enabled and PostgreSQL is an
authoritative conversation mode. Shadow mode computes structural metadata but
does not change execution. Production remains `LEGACY_ONLY`.

## Compatibility

- `lumina.analytics/2.0` remains the analytical contract.
- `lumina.temporal.pt-BR/1.0` remains temporal authority.
- `lumina.comparison-planner/1.0` remains comparison planning authority.
- `lumina.comparison-executor/1.0` remains numeric comparison authority.
- `lumina.comparison-presentation/1.0` remains presentation-only.
- `lumina.conversation-state/1.0` remains persistence authority.
- Legacy `SemanticPatch` is validated against operation and field allowlists
  before it can mutate a legacy plan.

## Test Coverage

Dedicated coverage includes strict contracts, four-turn continuity,
precedence, correction, negation, conflict, comparison extension, drill-down,
topic change, reset, deterministic checksum, idempotency, long conversations,
branch snapshots, epoch/CAS integration and a golden transition catalog.
Frontend coverage verifies the four-turn summary, hidden technical metadata,
session/version/parent continuity, retry, reset, conflict, expiration and
logout on the isolated Playwright port.
