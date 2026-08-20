# RC2-01.1 — Reconciliation of `use_new_pipeline` authority

Status: **BLOCKED — RC2-GOV-001 / FEATURE_GATE_BYPASS found**.

The immutable candidate `bf7b116bd91fb0c6994da07ac9736941f4cd78a2` exposed
`QueryRequest.use_new_pipeline` in the public body and combined it with server
flags through OR. An authenticated caller could therefore select the new
orchestrator while `NEW_PIPELINE_ACTIVE=false` and
`ENABLE_DETERMINISTIC_PIPELINE=false`. The RC2 deterministic compatibility
adapter made that path return certified numerical results without an AI
provider, turning the pre-existing weak selector into an executable rollout
bypass.

The remediation keeps the field as a transitional V1/V2 compatibility
preference but makes the effective decision server-authoritative:

```text
effective_new_pipeline =
    not V2_GLOBAL_EMERGENCY_DISABLE
    AND (NEW_PIPELINE_ACTIVE OR ENABLE_DETERMINISTIC_PIPELINE)
    AND request_preference
```

Omitted or false preference selects the legacy baseline. A true preference can
select the governed analytical adapter only when the server explicitly allows
it and the global emergency disable is inactive. Headers, query strings,
question text and model output are not inputs to this decision.

Prompt 26's feature-specific kill-switch, migration, security-readiness,
tenant-cohort and capability gates govern its closed inventory of eight V2
commercial/operational features. That inventory does not contain the analytical
query pipeline. Those feature-specific gates are therefore not silently claimed
for this route; adding such a feature would be new architecture and is outside
RC2-01.1. The global V2 emergency disable is applicable and now dominates the
pipeline flags and request preference.

The deterministic adapter under `/api/v1/query/` does not by itself activate
Dashboard V2 publication, Dashboard AI, post-sync consumers, observability
APIs, Work Queue V2, rollout execution, canary assignment or workers. Those
surfaces retain their independent server-side modes, API flags, kill switches
and mounting/startup guards.

Future homologation must use:

- legacy baseline: both pipeline flags false; omit `use_new_pipeline` (or send
  false); provider-unavailable behavior remains the legacy contract;
- governed numerical staging gate: global emergency disable false, one pipeline
  server flag true, and body preference true;
- `AUDIT_ONLY`: Prompt-26 rollout evidence/policy for a feature in its closed
  inventory; it does not activate the analytical pipeline;
- `SHADOW`: the feature's own server-side shadow mode and API/execution flags;
  never a client routing field.

Because runtime code changed after `bf7b116...`, that SHA is not a final RC2
candidate. A new commit and full clean-tree certification are required, without
moving the immutable `lumina-v2-rc1` tag.

## Validation after the local remediation

- authority, HTTP deny/allow, forged-input, Prompt-26 precedence, migration,
  tenant, auth/RBAC, provider and numerical tests: `121 passed`;
- backend integral: `2110 passed`, zero failures, errors, skips, xfails or
  XPASS; two historical Pydantic deprecation warnings;
- OpenAPI DEFAULT reproduced twice by the integral and directed checks:
  `190 paths / 216 operations`, SHA-256
  `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b`;
- OpenAPI COMBINED reproduced twice: `256 paths / 289 operations`, SHA-256
  `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c`;
- migrations V1–V26 unchanged; V27 absent; dependencies and lockfiles
  unchanged; blueprint LF SHA-256
  `2F2C79E87D0B1564B3BA04F40B0ABA0B05430B411EDAFDD6064028A7E2403744`.
