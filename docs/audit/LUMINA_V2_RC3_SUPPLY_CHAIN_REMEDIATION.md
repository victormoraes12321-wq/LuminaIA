# LuminaAI V2 RC3 supply-chain remediation

## Scope and immutable baseline

This remediation starts exactly from rejected candidate
`9451606b63c5ca0c1dbe62e7a360692bd9407bb7` on the isolated branch
`codex/lumina-v2-rc3-supply-chain-remediation`. The immutable RC2 tag remains
at `85657fd36196ca4a84883c48970222e8a6b38331`. The pre-existing dirty primary
checkout was not modified.

The change is limited to Docker base-image authority, the direct Python
dependency declaration, a packaging regression test and this audit record.
There are no application, analytical, tenant, RBAC, dashboard, feature
governance, migration, schema, corpus, frontend dependency or lockfile changes.

## Dependency and base-image decision

`cryptography` is a direct dependency declared in
`backend/requirements.txt`. Runtime consumers use its Fernet API in tenant
connection configuration, governed connection credential decryption and
conversation-content protection. JWT signing/verification uses PyJWT and
password hashing uses bcrypt; no project certificate parser or direct OpenSSL
binding was found.

The scanner's original blocking authority was
`GHSA-537c-gmf6-5ccf`, fixed in `48.0.1`. A trial rebuild at `48.0.1`
removed that advisory but introduced new High `CVE-2026-69247`, fixed in
`50.0.0`. Therefore `50.0.0` is the smallest tested compatible version
that satisfies the original gate without adding a new Critical/High. It is
compatible with Python 3.12 and resolved with the existing `cffi 2.1.1`.

Frontend OpenSSL `3.5.6-r0` came from the official
`node:20-alpine` base, not from application dependencies. The rebuilt base
digest still contained `3.5.6-r0`, while the same Alpine 3.23 repository
offered the exact patched packages `libcrypto3=3.5.7-r0` and
`libssl3=3.5.7-r0`. The Dockerfile consequently keeps Node 20 and the same
Alpine family, pins the base digest, and installs only those two exact package
versions. It does not run a broad `apk upgrade`.

The formerly mutable backend base is now pinned to the exact fresh-build
`python:3.12-slim` digest
`sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65`.
The frontend base is pinned to
`node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293`.

## Comparable SBOM and vulnerability results

Docker Scout `v1.23.1` generated SPDX SBOMs and SARIF scans for fresh
no-cache builds before and after the change.

| Image | Old C | Old H | New C | New H | C/H delta | SPDX components excluding image root | New SPDX SHA-256 |
|---|---:|---:|---:|---:|---:|---:|---|
| backend | 2 | 15 | 2 | 12 | -3 | 210 | `fcba6394fe296e4c2134014672234ad0d236f38963d6dcce5a80377cd89919f5` |
| frontend | 2 | 33 | 1 | 25 | -9 | 437 | `3b6f1f41d729a53a0080ee473c142015c8ab6756cb8e7d06f6ebd488971356e7` |
| total | 4 | 48 | 3 | 37 | -12 | 647 | n/a |

All ten original `FIX_AVAILABLE_NOT_APPLIED` blockers are absent after the
rebuild. Two additional non-blocking, not-reachable `cryptography` findings
are also absent. There are zero new Critical/High IDs, zero unclassified
Critical/High findings and zero formal risk acceptances. The remaining 40
Critical/High results retain the previous triage: five base-image findings
without a fix, 34 present-not-reachable findings and one false positive.
No remaining Critical/High has a demonstrated exploitable application runtime
path.

## Finding-by-finding reconciliation

| Image | Old finding | Severity | Old classification | Old package/version | Fixed authority | New package/version | Present after | New classification | Fix status |
|---|---|---|---|---|---|---|---|---|---|
| backend | CVE-2026-12087 | CRITICAL | BASE_IMAGE_NO_FIX_AVAILABLE | debian/perl/5.40.1-6 | not fixed | debian/perl/5.40.1-6 | yes | BASE_IMAGE_NO_FIX_AVAILABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-13221 | CRITICAL | BASE_IMAGE_NO_FIX_AVAILABLE | debian/perl/5.40.1-6 | not fixed | debian/perl/5.40.1-6 | yes | BASE_IMAGE_NO_FIX_AVAILABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-26007 | HIGH | PRESENT_NOT_REACHABLE | cryptography/43.0.3 | 46.0.5 | cryptography/50.0.0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| backend | CVE-2026-69249 | HIGH | PRESENT_NOT_REACHABLE | cryptography/43.0.3 | 49.0.0 | cryptography/50.0.0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| backend | GHSA-537c-gmf6-5ccf | HIGH | FIX_AVAILABLE_NOT_APPLIED | cryptography/43.0.3 | 48.0.1 | cryptography/50.0.0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| backend | CVE-2026-66032 | HIGH | BASE_IMAGE_NO_FIX_AVAILABLE | debian/libssh2/1.11.1-1%2Bdeb13u1 | not fixed | debian/libssh2/1.11.1-1%2Bdeb13u1 | yes | BASE_IMAGE_NO_FIX_AVAILABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-48959 | HIGH | BASE_IMAGE_NO_FIX_AVAILABLE | debian/perl/5.40.1-6 | not fixed | debian/perl/5.40.1-6 | yes | BASE_IMAGE_NO_FIX_AVAILABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-48962 | HIGH | BASE_IMAGE_NO_FIX_AVAILABLE | debian/perl/5.40.1-6 | not fixed | debian/perl/5.40.1-6 | yes | BASE_IMAGE_NO_FIX_AVAILABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2025-45768 | HIGH | FALSE_POSITIVE | pyjwt/2.10.1 | not fixed | pyjwt/2.10.1 | yes | FALSE_POSITIVE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-32597 | HIGH | PRESENT_NOT_REACHABLE | pyjwt/2.10.1 | 2.12.0 | pyjwt/2.10.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-48526 | HIGH | PRESENT_NOT_REACHABLE | pyjwt/2.10.1 | 2.13.0 | pyjwt/2.10.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-24486 | HIGH | PRESENT_NOT_REACHABLE | python-multipart/0.0.20 | 0.0.22 | python-multipart/0.0.20 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-42561 | HIGH | PRESENT_NOT_REACHABLE | python-multipart/0.0.20 | 0.0.27 | python-multipart/0.0.20 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-53539 | HIGH | PRESENT_NOT_REACHABLE | python-multipart/0.0.20 | 0.0.30 | python-multipart/0.0.20 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2025-62727 | HIGH | PRESENT_NOT_REACHABLE | starlette/0.41.3 | 0.49.1 | starlette/0.41.3 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-48818 | HIGH | PRESENT_NOT_REACHABLE | starlette/0.41.3 | 1.1.0 | starlette/0.41.3 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| backend | CVE-2026-54283 | HIGH | PRESENT_NOT_REACHABLE | starlette/0.41.3 | 1.3.1 | starlette/0.41.3 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-34182 | CRITICAL | FIX_AVAILABLE_NOT_APPLIED | alpine/openssl/3.5.6-r0 | 3.5.7-r0 | alpine/openssl/3.5.7-r0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| frontend | CVE-2026-59873 | CRITICAL | PRESENT_NOT_REACHABLE | tar/6.2.1 | 7.5.19 | tar/6.2.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-34180 | HIGH | FIX_AVAILABLE_NOT_APPLIED | alpine/openssl/3.5.6-r0 | 3.5.7-r0 | alpine/openssl/3.5.7-r0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| frontend | CVE-2026-34181 | HIGH | FIX_AVAILABLE_NOT_APPLIED | alpine/openssl/3.5.6-r0 | 3.5.7-r0 | alpine/openssl/3.5.7-r0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| frontend | CVE-2026-34183 | HIGH | FIX_AVAILABLE_NOT_APPLIED | alpine/openssl/3.5.6-r0 | 3.5.7-r0 | alpine/openssl/3.5.7-r0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| frontend | CVE-2026-42764 | HIGH | FIX_AVAILABLE_NOT_APPLIED | alpine/openssl/3.5.6-r0 | 3.5.7-r0 | alpine/openssl/3.5.7-r0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| frontend | CVE-2026-45445 | HIGH | FIX_AVAILABLE_NOT_APPLIED | alpine/openssl/3.5.6-r0 | 3.5.7-r0 | alpine/openssl/3.5.7-r0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| frontend | CVE-2026-45447 | HIGH | FIX_AVAILABLE_NOT_APPLIED | alpine/openssl/3.5.6-r0 | 3.5.7-r0 | alpine/openssl/3.5.7-r0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| frontend | CVE-2026-7383 | HIGH | FIX_AVAILABLE_NOT_APPLIED | alpine/openssl/3.5.6-r0 | 3.5.7-r0 | alpine/openssl/3.5.7-r0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| frontend | CVE-2026-9076 | HIGH | FIX_AVAILABLE_NOT_APPLIED | alpine/openssl/3.5.6-r0 | 3.5.7-r0 | alpine/openssl/3.5.7-r0 | no | NOT_PRESENT_AFTER_REBUILD | REMEDIATED |
| frontend | CVE-2026-13149 | HIGH | PRESENT_NOT_REACHABLE | brace-expansion/2.0.1 | 2.1.2 | brace-expansion/2.0.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-14257 | HIGH | PRESENT_NOT_REACHABLE | brace-expansion/2.0.1 | 5.0.8 | brace-expansion/2.0.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-69152 | HIGH | PRESENT_NOT_REACHABLE | brace-expansion/2.0.1 | 2.1.4 | brace-expansion/2.0.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2024-21538 | HIGH | PRESENT_NOT_REACHABLE | cross-spawn/7.0.3 | 7.0.5 | cross-spawn/7.0.3 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2025-64756 | HIGH | PRESENT_NOT_REACHABLE | glob/10.4.2 | 11.1.0 | glob/10.4.2 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-69192 | HIGH | PRESENT_NOT_REACHABLE | ip-address/9.0.5 | 10.3.1 | ip-address/9.0.5 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-26996 | HIGH | PRESENT_NOT_REACHABLE | minimatch/9.0.5 | 10.2.1 | minimatch/9.0.5 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-27903 | HIGH | PRESENT_NOT_REACHABLE | minimatch/9.0.5 | 9.0.7 | minimatch/9.0.5 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-27904 | HIGH | PRESENT_NOT_REACHABLE | minimatch/9.0.5 | 9.0.7 | minimatch/9.0.5 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-67213 | HIGH | PRESENT_NOT_REACHABLE | nanoid/3.3.12 | 3.3.17 | nanoid/3.3.12 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-67214 | HIGH | PRESENT_NOT_REACHABLE | nanoid/3.3.12 | 3.3.16 | nanoid/3.3.12 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-64641 | HIGH | PRESENT_NOT_REACHABLE | next/16.2.10 | 16.2.11 | next/16.2.10 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-64642 | HIGH | PRESENT_NOT_REACHABLE | next/16.2.10 | 16.2.11 | next/16.2.10 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-64645 | HIGH | PRESENT_NOT_REACHABLE | next/16.2.10 | 16.2.11 | next/16.2.10 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-64649 | HIGH | PRESENT_NOT_REACHABLE | next/16.2.10 | 16.2.11 | next/16.2.10 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-73646 | HIGH | PRESENT_NOT_REACHABLE | postcss/8.5.15 | 8.5.18 | postcss/8.5.15 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | GHSA-f88m-g3jw-g9cj | HIGH | PRESENT_NOT_REACHABLE | sharp/0.34.5 | 0.35.0 | sharp/0.34.5 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-48815 | HIGH | PRESENT_NOT_REACHABLE | sigstore/2.3.1 | 4.1.1 | sigstore/2.3.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-23745 | HIGH | PRESENT_NOT_REACHABLE | tar/6.2.1 | 7.5.3 | tar/6.2.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-23950 | HIGH | PRESENT_NOT_REACHABLE | tar/6.2.1 | 7.5.4 | tar/6.2.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-24842 | HIGH | PRESENT_NOT_REACHABLE | tar/6.2.1 | 7.5.7 | tar/6.2.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-26960 | HIGH | PRESENT_NOT_REACHABLE | tar/6.2.1 | 7.5.8 | tar/6.2.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-29786 | HIGH | PRESENT_NOT_REACHABLE | tar/6.2.1 | 7.5.10 | tar/6.2.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-31802 | HIGH | PRESENT_NOT_REACHABLE | tar/6.2.1 | 7.5.11 | tar/6.2.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |
| frontend | CVE-2026-59874 | HIGH | PRESENT_NOT_REACHABLE | tar/6.2.1 | 7.5.18 | tar/6.2.1 | yes | PRESENT_NOT_REACHABLE | UNCHANGED_NON_BLOCKING |

## Compatibility and regression evidence

- Fresh backend no-cache build: PASS; `pip check`: PASS; application imports:
  PASS; resolved `cryptography=50.0.0`, `cffi=2.1.1`.
- Directed runtime crypto/auth under non-root read-only rootfs: PASS for Fernet
  round-trip, valid/invalid/wrong keys, tampered ciphertext, conversation
  persistence, connection credentials, valid/tampered/expired JWT behavior.
- Fresh frontend no-cache build: `npm ci` and Next build PASS. Independent
  disposable install: lint 0 errors/13 historical warnings, TypeScript PASS,
  build PASS.
- Runtime containers: backend UID/GID 10001; frontend UID/GID 10001;
  `privileged=false`; `cap_drop=ALL`; no added capabilities;
  `no-new-privileges=true`; read-only rootfs and declared writable tmpfs
  policy PASS.
- Backend content: tests 0, reports 0, backups 0, Git metadata 0, environment
  files 0. Frontend prohibited source/test/report/Git/environment artifacts 0.
- Startup and health: backend `/health` PASS; backend `/health/deep` PASS
  with `ready_for_traffic=true`; frontend `/healthz` PASS.
- SIGTERM: backend exited 0 in 1.604s; frontend respected SIGTERM in 0.651s
  with conventional signal exit 143 and no grace-period timeout/SIGKILL.
- AST: 859 Python files parsed, 0 errors.
- Backend full official safe runner: 2,150 passed, 0 failed/errors/skipped/
  xfailed/XPASS, two historical Pydantic warnings.
- Directed packaging/auth/tenant/RC2 analytical/Prompt 26 security matrix:
  98 passed.
- Full Playwright: 432 passed, 0 failed, 0 skipped, four viewports.
- Official analytical HTTP gate: 30/30; NUM-014 = 155.00; current numerical
  corpus 60/60; fabricated zeros 0; metric and temporal mismatches 0.
- RC2 governance, login/invalid credentials/JWT/logout, RBAC and tenant
  isolation remain green through the full and directed suites.
- A Linux-container-only attempt was not used as suite evidence because one
  negative test derives a non-UTC input from the machine timezone while the
  container timezone is UTC. A containerized Playwright cold compile likewise
  exceeded its 60-second per-test bound. Both official Windows harnesses passed
  completely; image behavior was independently tested in the final images.

## Immutable authorities

- Migration files/models diff from the starting candidate: 0; migration v27:
  absent.
- Migration canonical hash:
  `bd7f87edcb23abcad102423d04d4c64a2c44b12aa7edb311772a2ff9379f577e`.
- PostgreSQL schema canonical hash:
  `b642bd10dd11d7f37508dda02c74855ae614a309533805959fb89d2a46d6be51`.
- RC acceptance corpus:
  `41b4649c72f7b75976ec0dabab06c5f3bea7e204de7a6b7aab1fec44c9793511`.
- Blueprint Git/LF hash:
  `2F2C79E87D0B1564B3BA04F40B0ABA0B05430B411EDAFDD6064028A7E2403744`.
- OpenAPI DEFAULT: 190 paths, 216 operations,
  `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b`.
- OpenAPI COMBINED: 256 paths, 289 operations,
  `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c`.

## Operational boundary and decision

Production, production databases, production secrets, real tenants, Oracle,
real AI providers, production migrations, rollout, canary, tag and push were
not touched. PR-INFRA/GOV/OPS remain open for PR-01.

Pre-commit decision: `RC3 SUPPLY CHAIN REMEDIATION - CERTIFIED`.
After the single commit, the exact SHA must still pass the mandatory clean
archive rebuild, rescan, hardening and functional smoke before it can be handed
off as `NEW RC3 CLEAN CANDIDATE - READY`. This task does not itself declare
RC3 fully certified or create the `lumina-v2-rc3` tag.
