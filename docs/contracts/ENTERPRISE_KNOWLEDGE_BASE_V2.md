# Enterprise Knowledge Base V2

## Contract

- Version: `lumina.enterprise-knowledge/1.0`
- Authority: published, effective, tenant-scoped enterprise semantics
- Numerical authority: `MetricRegistry`
- Query authority: physical catalog, allowlists and deterministic executors
- Storage: PostgreSQL analytical/corporate database
- Runtime defaults: `LEGACY_ONLY`

The knowledge base stores definitions and governed semantic references. It
does not store datasets, SQL, binds, credentials, executable formulas,
conversation state, user preferences, feedback or chain of thought.

## Asset Types

| Type | Purpose |
| --- | --- |
| `BUSINESS_TERM` | Governed business definition and aliases |
| `METRIC` | Semantic description bound to an official metric |
| `KPI` | Governed KPI semantics bound to an official metric |
| `DIMENSION` | Governed analytical dimension |
| `ENTITY` | Governed business entity |
| `BUSINESS_RULE` | Descriptive non-executable rule |
| `ALIAS_SET` | Versioned aliases for one canonical target |
| `CALENDAR_POLICY` | Calendar and fiscal policy |
| `DATA_QUALITY_POLICY` | Non-executable quality criteria |
| `SEMANTIC_RELATION` | Allowlisted relationship between assets |

Every content type has a dedicated Pydantic model. The public content union is
discriminated by `kind`; unknown fields are rejected.

## Stable Asset

`EnterpriseKnowledgeAssetV2` is the durable identity:

- tenant and stable UUID;
- canonical key, type and domain;
- owner, steward and accountable area;
- general status;
- current published version pointer;
- lock version and timestamps.

Canonical key uniqueness is `(tenant_id, asset_type, canonical_key)`. The same
key may exist in different tenants.

## Immutable Version

`EnterpriseKnowledgeVersionV2` contains:

- monotonically assigned version number;
- lifecycle;
- typed content;
- SHA-256 checksum of canonical JSON;
- author and previous version;
- effective interval;
- lock version and timestamps.

Published or approved content cannot be edited. The service enforces this rule
and migration v13 installs a PostgreSQL trigger that rejects changes to
content, checksum, version identity, author or source after approval.

## Lifecycle

Allowed transitions:

```text
DRAFT -> IN_REVIEW
IN_REVIEW -> APPROVED
IN_REVIEW -> REJECTED
APPROVED -> PUBLISHED
PUBLISHED -> DEPRECATED
DEPRECATED -> ARCHIVED (asset archive after no active publication)
PUBLISHED/DEPRECATED -> new DRAFT (revision or rollback)
```

Rollback copies historical content into a new draft. It never reactivates or
mutates the historical row.

## Separation Of Duties

| Role | Effective permissions |
| --- | --- |
| `CONSULTA` | Published read and lexical search |
| `GESTOR` | Read, create, edit, submit, review, approve/reject, export |
| `ADMIN` | All governed permissions, including publish and rollback |

The author cannot review their own version. An approval is bound to the
version checksum; stale approval or publication fails. Emergency override is
off and no silent bypass exists.

## Metric Binding

`EnterpriseKnowledgeMetricBinding` validates metric and KPI knowledge against
the official `MetricRegistry`:

- canonical metric ID;
- authoritative source;
- official formula fingerprint;
- binding status and effective lifecycle.

Status values are `VALID`, `DESCRIPTION_ONLY`, `CONFLICT`,
`MISSING_REGISTRY_ENTRY`, `DEPRECATED` and `BLOCKED`. Conflict, missing
registry entry and blocked content prevent publication. The binding never
changes an official formula and never calculates a value.

The official fingerprint is SHA-256 over the registry key, source, formula,
default filters and grain. This proves semantic content references the same
numeric authority without storing executable formula text as a knowledge
asset.

## Aliases And Search

Aliases are normalized with Unicode NFKD, accent removal, case folding,
punctuation removal and whitespace normalization. They are tenant-, locale-
and version-scoped.

Only aliases belonging to the current published and effective version enter
runtime search. Deterministic scores:

| Match | Score |
| --- | ---: |
| canonical exact | 1000 |
| alias exact | 950 |
| display exact | 900 |
| alias prefix | 850 |
| display prefix | 800 |
| token overlap | 400-700 |

Equal top scores are returned as explicit ambiguity. No arbitrary candidate is
selected. Cursor pagination is bound to the normalized query.

## Provenance

Published candidates expose minimal source references and immutable
provenance:

- asset ID;
- version ID;
- checksum;
- canonical key;
- source reference title, authority and type.

References accept only `https` or `urn` schemes and reject embedded
credentials. The service does not fetch referenced documents.

## Integration Boundaries

`EnterpriseKnowledgeRuntime` is the published-only adapter for canonicalizer,
intent and context consumers. `candidates_for_canonicalizer`,
`projection_for_intent` and `facts_for_context` provide bounded canonical IDs,
labels, domains and immutable provenance while preserving ambiguous
candidates. They never provide physical tables, columns, SQL, binds,
conversation state or tenant overrides.

`LegacyBusinessKnowledgeAdapter` converts explicit legacy records to V2
drafts only. It requires an existing owner and never creates approval or
publication.

Planner consumers may use semantic compatibility and canonical IDs. The
executor remains authoritative for allowlisted PostgreSQL queries and official
numeric formulas.

## Import And Export

Import:

- is disabled by default;
- requires authenticated tenant, author and owner;
- is dry-run by default;
- validates up to 500 typed items;
- uses checksum and idempotency;
- creates drafts only;
- never publishes automatically.

Dry-run creates no assets or import records. Export is disabled by default,
tenant-scoped, permission-checked and published-only. CSV cells beginning with
`=`, `+`, `-`, `@`, tab or carriage return are neutralized.

## Cache

The optional bounded cache stores resolution results only. The lookup index
includes tenant, locale, normalized query and effective-time scope; the stored
entry key includes the SHA-256 fingerprint of candidate publication checksums.
Values are copied on read/write, have short TTL and are invalidated after
publish, deprecate and rollback publication. Drafts never enter cache. Cache
telemetry exposes only hit, miss, entry and invalidation counters.

## Versioned API

The `/api/v2/enterprise-knowledge` surface provides published search,
published canonical lookup, metric/KPI definition lookup, an authorized review
queue, asset/version history, workflow actions, diff, audit, import and export.
Every operation derives tenant and user from authentication. The review queue
requires `knowledge:review`; `CONSULTA` cannot use it.

The administrative UI supports filters, draft editing with optimistic
concurrency, review, publication, revision, deprecation, rollback, ownership,
history, diff and audit. The read-only glossary opens only the current
published definition and public ownership/effective-period information.

## Rollout

| Mode | Behavior |
| --- | --- |
| `LEGACY_ONLY` | Existing behavior remains authoritative |
| `SHADOW_READ` | V2 compares structural results without affecting runtime |
| `V2_READ` | Runtime reads published V2 knowledge |
| `V2_READ_WRITE` | Full governed workflow is available |

Additional flags govern frontend visibility, import, export, cache and
emergency override. All are off by default.

## PostgreSQL

Migration `backend/database/migration_v13_0.py` creates eight additive tables,
composite tenant FKs, lifecycle/checksum/effective-period constraints, indexes
and the immutable-content trigger. Production does not apply it
automatically. Its down path is test-only and guarded by `TEST_DATABASE_URL`.

## Security

- Tenant comes from the authenticated user, never request payload.
- Every repository method requires tenant.
- `CONSULTA` cannot see drafts, rejections or review comments.
- Public IDs do not grant access.
- Content rejects active HTML, null bytes and control characters.
- No Oracle, OpenAI, external connector or operational database access exists.
- Audit metadata is structural and excludes content, SQL, binds and secrets.
