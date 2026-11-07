# Requested User Stories — Implementation and Handoff Status

**Updated:** 2026-11-07
**Scope:** Only US-038, US-026, US-017, US-025, US-031, and US-035.
**Base:** `develop` / `origin/develop` at `780b7aac41cee50627093fb21afd552b30b90f80`.

## Summary

| Story | Status | Branch / evidence | Remaining limitation |
|---|---|---|---|
| US-038 — Reproducible, optimized Docker build | **Blocked / not implemented here** | `feature/US-038` already exists remotely at `c92a193` | That branch contains a mixed changeset for several stories and unrelated changes. It was not overwritten. Current Dockerfile remains single-stage, digest-unpinned, and without the requested platform/cache configuration. |
| US-026 — Pull-request CI | **Implemented on separate branch** | `feature/US-026`, `6ad9e9dfd38d915dc4fc99d36dd5540ffa2e765d` | Docker Engine was unavailable locally, and a GitHub Actions run was not verified. Workflow does not push or deploy. |
| US-017 — Deployment smoke test | **Script and tests implemented; live check incomplete** | `feature/US-017`, `bf929b842e132e8c3bca3344c6ade65e2df5c9dc` | No verified sample image or revision-specific deployment URL was available. No staging/production smoke test is claimed. |
| US-025 — CORS and network errors | **Backend CORS implemented; frontend portion unavailable** | `feature/US-025`, `562736c0f4e2ab43dd29dd9f417b6d88e1116ea2` | Repository contains no frontend, and no deployed Cloudflare Pages origin was verified. JavaScript network/cold-start/business-error UX is not implemented. |
| US-031 — ACA traffic rollback | **Guarded manual tool implemented; rehearsal/integration blocked** | `feature/US-031`, `fed99c758d8f76577a941c818f84b45ab4869d74` | Azure CLI was unavailable; production revision count/mode and permissions were not verified. No traffic was changed. Automatic rollback requires US-029, which is outside this scope and absent. |
| US-035 — README and runbook | **Documentation updated on this branch** | `feature/US-035`, based on `780b7aa` | Documentation describes the ACA architecture and explicitly distinguishes branch-only features from deployed behavior. No docs test suite exists. |

These are separate branches from `develop`; none of the feature branches was
merged into another branch or into `main`. Features remain unavailable from
`develop` until their PRs are reviewed and merged.

## Branch changes and implementation details

### US-038

- No files changed for this story in this work.
- The pre-existing remote branch `feature/US-038` was left untouched because it
  contains combined/in-scope and unrelated changes. Do not force-push or assume
  its contents are a clean implementation of US-038.
- To continue: the repository owner must review/reconcile that branch and
  authorize a safe branch/PR path. Then test a multi-stage build against the
  real model and runtime, including BuildKit/GHA cache, `linux/amd64`, digest
  pinning, build duration, and image size.

### US-026

- Added `.github/workflows/ci.yml`, Ruff/Black configuration and dependencies,
  and workflow contract tests on `feature/US-026`.
- PR checks include Ruff, Black `--check`, selected NumPy-only/contract tests,
  and a no-push `linux/amd64` Docker build using `type=gha` cache. The workflow
  reports Docker build duration and image size after a successful build.
- Baseline Python files were formatted/import-sorted to satisfy whole-tree
  linting. See the branch diff for the complete list.
- Evidence: Ruff and Black passed; the selected CI-compatible suite passed
  (36 tests). A local Docker build was not possible because Docker Engine was
  not running. A completed hosted Actions run has not been observed.

### US-017

- Added `scripts/smoke_test.py`, `tests/test_smoke_test.py`, and
  `docs/api/US-017.md` on `feature/US-017`.
- Requires `--url`, `--expected-sha`, and `--image`; checks `/health` readiness,
  `/version` SHA, and `/predict` response; failures return a non-zero exit code.
- Evidence: 8 unit tests passed and the CLI help command ran. Tests use mocks;
  they do not prove a deployed service works. No verified image or unique
  revision URL was available, so no deployed smoke test ran.

### US-025

- Added strict FastAPI CORS origin parsing/middleware, `tests/test_cors.py`,
  and `docs/api/US-025.md` on `feature/US-025`.
- `VSL_ALLOWED_ORIGINS` is an exact comma-separated origin allowlist; wildcard
  origins are rejected. The middleware supports the API methods and preflight
  without enabling credentials.
- Evidence: 7 CORS tests and 2 health tests passed. A Starlette
  `TestClient`/httpx deprecation warning was observed.
- No frontend code is present. The ADR decision to use Cloudflare Pages does
  not establish a deployed hostname; the operator must supply and verify the
  exact origin before configuring it.

### US-031

- Added `scripts/rollback.py`, `tests/test_rollback.py`, and
  `docs/api/US-031.md` on `feature/US-031`.
- The script targets Azure Container Apps, defaults to read-only dry-run, and
  refuses unsupported revision mode, ambiguous/split traffic, stale operator
  confirmations, and ambiguous revision timestamps. `--apply` requires
  explicit current/target revision, expected Git SHA, and service URL, then
  sets target/current weights to 100/0 and checks traffic, `/health`, and
  `/version`.
- Evidence:
  - `& ".\.venv\Scripts\python.exe" -m pytest -v tests/test_rollback.py` —
    **8 passed**.
  - `& ".\.venv\Scripts\ruff.exe" check scripts/rollback.py tests/test_rollback.py`
    — **passed**.
  - `& ".\.venv\Scripts\black.exe" --check scripts/rollback.py tests/test_rollback.py`
    — **passed**.
  - `git diff --check` — **passed**.
- Azure CLI was not installed. No live Azure read, write, traffic change,
  production revision inspection, or rollback rehearsal occurred. The script
  cannot automatically integrate with a smoke-test deployment until US-029
  exists.

### US-035

- Updated `README.md` with architecture, repository map, local setup, tests,
  Docker, environment variables/secrets, and explicit feature availability.
- Updated `HUONG-DAN-CHAY.md` to correct stale Cloud Run/local-Python guidance;
  added a live-verification and credential-safety notice to the Azure
  deployment guide.
- Added `docs/RUNBOOK.md` for CI failure, cold start, smoke-test failure,
  unavailable backend, CORS, manual ACA rollback, and cloud-cost triage.
- Updated `docs/README.md` to index the runbook and implementation status.
- No frontend error handling, automatic deploy/rollback, production smoke test,
  cloud cost alert, or rollback rehearsal is represented as completed.
- This is a documentation-only change; no documentation test runner is
  configured.

## Environment and architectural decisions

- Actual backend target in repository infrastructure docs is **Azure Container
  Apps**, not Cloud Run. No Cloud Run configuration was found.
- No frontend source exists. Cloudflare Pages is an architecture decision, not
  evidence of an actual deployed origin.
- No CI workflow, image publishing, or deployment automation is present in
  `develop`. US-026 is PR CI only and does not publish/deploy.
- Do not add cloud credentials to Git. US-026 requires no cloud secret. Use an
  approved Azure identity for manual ACA operations.
- CORS remains default-deny until US-025 is merged/deployed and an exact
  frontend origin is supplied.
- The US-031 rollback tool is manual and safety-gated. Production readiness
  requires verified ACA state, operator approval, and an actual rehearsal.
- US-038 remains blocked by the existing mixed remote branch and must not be
  marked complete based on that branch's existence.

## Suggested PR/continuation order

1. Owner reviews and resolves the existing `feature/US-038` branch before
   approving a clean US-038 implementation.
2. Review/merge `feature/US-026` to establish PR CI; hosted workflow results
   still need verification.
3. Review/merge `feature/US-025` only after confirming the allowed frontend
   origin; review/merge `feature/US-017` before using its smoke-test script.
4. Review/merge `feature/US-031` for manual rollback tooling. A real rehearsal
   requires at least two active ACA revisions, Multiple mode, permissions, and
   explicit owner approval.
5. US-029 deployment integration is not included; do not claim automatic smoke
   test rollback until that dependency is implemented and tested.
6. Review/merge `feature/US-035` after verifying that operational details
   remain current. All PRs remain independent; do not merge one feature branch
   into another to obtain the listed behavior.

## Commands and outcomes recorded for this work

| Check | Result |
|---|---|
| US-017 smoke-test unit suite | 8 passed; no deployed target exercised |
| US-025 CORS/health tests | 9 passed; deprecation warning noted |
| US-026 Ruff, Black, selected tests | Passed; selected suite 36 tests |
| US-026 Docker build | Not run locally: Docker Engine unavailable; hosted run not verified |
| US-031 rollback tests | 8 passed |
| US-031 Ruff / Black / diff check | Passed |
| US-031 Azure rehearsal | Not run: Azure CLI/revision evidence/approval unavailable |
| US-035 documentation | Updated; no documentation test command configured |
| US-038 optimized build | Not implemented or measured |

## Git handoff

| Branch | Commit | Push |
|---|---|---|
| `feature/US-038` | Existing remote branch, observed at `c92a193`; not modified | Pre-existing; not pushed by this work |
| `feature/US-026` | `6ad9e9dfd38d915dc4fc99d36dd5540ffa2e765d` | Pushed |
| `feature/US-017` | `bf929b842e132e8c3bca3344c6ade65e2df5c9dc` | Pushed |
| `feature/US-025` | `562736c0f4e2ab43dd29dd9f417b6d88e1116ea2` | Pushed |
| `feature/US-031` | `fed99c758d8f76577a941c818f84b45ab4869d74` | Pushed |
| `feature/US-035` | Documentation changes are in progress; commit recorded in final Git handoff | Not pushed yet |

No changes were pushed to `main`. The PR links for pushed feature branches are
available by opening:

- `https://github.com/courseprojectICTU/Sign-Language-Classification/pull/new/feature/US-026`
- `https://github.com/courseprojectICTU/Sign-Language-Classification/pull/new/feature/US-017`
- `https://github.com/courseprojectICTU/Sign-Language-Classification/pull/new/feature/US-025`
- `https://github.com/courseprojectICTU/Sign-Language-Classification/pull/new/feature/US-031`
