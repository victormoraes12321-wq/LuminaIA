# LuminaAI V2 RC3 packaging remediation

## Scope and source authority

This remediation starts exclusively from immutable tag `lumina-v2-rc2`, SHA
`85657fd36196ca4a84883c48970222e8a6b38331`. It addresses only
`PR-BUG-0001` (runtime image content) and `PR-BUG-0002` (container runtime
hardening). Application behavior, migrations, analytical corpus, dependencies
and lockfiles are outside the change.

## Reproduced baseline

The RC2 backend build context had no `.dockerignore`. Its single-stage
Dockerfile used `COPY . .`, making that instruction the first divergent stage:
236 test files, 16 report files, 61 backup files and two safe environment
templates entered `/app` in the final image. The measured context transfer was
105.23 MB. Both application images had effective UID/GID 0.

The frontend also had no context policy and copied the whole context into its
builder. Its final stage did not retain the repository tests, but still ran as
root.

## Structural remediation

- Backend and frontend contexts use allowlist-first `.dockerignore` policies.
- The backend Dockerfile uses an isolated dependency builder and explicit
  runtime `COPY` instructions. Of `backend/testing/`, only the package marker
  and `database_guard.py` are retained because official migration modules
  import that fail-closed guard. Test database bootstrap, network mocks,
  deterministic AI mocks, golden payload helpers and the pytest suite remain
  excluded.
- The frontend builder receives only application/build inputs and performs
  `npm ci`. The final stage receives only package manifests, pruned production
  dependencies, `.next` and public assets.
- Both runtime stages use stable UID/GID 10001 and exec-form process commands.
- Compose sets `privileged: false`, drops every Linux capability, enables
  `no-new-privileges`, and uses read-only root filesystems with bounded tmpfs
  mounts for legitimate ephemeral writes.
- Backend logs use stdout/stderr. Legacy conversation/debug paths are ephemeral
  tmpfs; important state remains in governed stores. Frontend cache is also an
  ephemeral tmpfs.

## Authority reconciliation

The schema value
`fff4376d81318e8735176ef1e83bee4675c9551347420ff498ba46939101730b`
is a `DIFFERENT_EXPORTER`: it is the Prompt 26 contracts/schema export hash,
not the canonical PostgreSQL schema-manifest hash. The RC2 database authority
remains
`b642bd10dd11d7f37508dda02c74855ae614a309533805959fb89d2a46d6be51`.

The corpus value
`f1ba92669b861c7ab30a50d57a81f4a4aa6b3ef9ce62ad88c53dce9a8879e4e5`
is a `HISTORICAL_BASELINE` repeated by a stale RC1 report. RC2 intentionally
changed the corpus during analytical-integrity remediation. The governed
`lumina.rc-acceptance-corpora/1.0` manifest and exporter both resolve to
`41b4649c72f7b75976ec0dabab06c5f3bea7e204de7a6b7aab1fec44c9793511`.
Thus reconciliation has zero `UNKNOWN` values.

Other immutable authorities remain:

- migration manifest: `bd7f87edcb23abcad102423d04d4c64a2c44b12aa7edb311772a2ff9379f577e`;
- blueprint Git/LF: `2F2C79E87D0B1564B3BA04F40B0ABA0B05430B411EDAFDD6064028A7E2403744`;
- OpenAPI DEFAULT: 190 paths, 216 operations,
  `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b`;
- OpenAPI COMBINED: 256 paths, 289 operations,
  `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c`.

## Verification evidence

- Backend full clean-build context transfer fell from 105.23 MB to 6.52 MB
  (an earlier 39.00 kB observation was an incremental BuildKit transfer, not
  the full context). Its image size
  fell from 211,201,524 to 98,829,545 bytes. The final `/app` contains 602
  files and zero files under tests, reports, backups, Git metadata, local
  environment files or Python cache directories.
- Frontend final `/app` contains 23,204 files and zero tests, reports,
  backups, Git metadata, local environment files or source cache artifacts.
  The baseline and remediated image sizes are 203,739,982 and 203,744,679
  bytes; minimality is established by content, not an arbitrary size gate.
- Both images run as numeric UID/GID 10001. With read-only rootfs,
  `cap_drop: ALL`, `no-new-privileges` and only the declared tmpfs paths, the
  backend passed startup, `/health`, `/health/deep`, allowed-write and
  forbidden-write assertions. Graceful shutdown completed with exit code 0
  in 1.466 seconds.
- Fresh backend dependency install and `pip check` passed. Fresh frontend
  `npm ci`, lint, TypeScript, build and container page smoke passed. No host
  virtualenv, `node_modules` or compiled artifact entered either build.
- The complete backend regression passed 2,149 tests with zero failures,
  errors, skips, xfails or XPASS. The directed packaging/analytical/
  governance/Prompt 26 matrix passed 94 tests, the numerical corpus and
  determinism matrix passed 62 tests, and full Playwright passed 432 tests.
- Docker Scout SBOMs were generated outside the repository for both images.
  Full candidate scans report backend 2 CRITICAL, 15 HIGH, 17 MEDIUM, 53 LOW
  and 8 UNSPECIFIED; frontend 2 CRITICAL, 33 HIGH, 18 MEDIUM and 4 LOW.
  The CRITICAL/HIGH counts are identical to their RC2 baseline images, so the
  remediation introduced zero new CRITICAL or HIGH findings. These existing
  base/dependency findings remain separate follow-up work.

## Operational boundary

This remediation does not resolve production-like infrastructure findings,
does not authorize production or certify RC3 as a release, and does not create
the `lumina-v2-rc3` tag. A successful candidate must still pass RC3 full
certification before checkpoint/tagging.
