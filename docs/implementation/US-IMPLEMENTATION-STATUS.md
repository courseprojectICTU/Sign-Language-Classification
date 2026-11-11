# Requested User Stories — Implementation and Handoff Status

**Updated:** 2026-11-11
**Scope:** US-038, US-026, US-017, US-025, US-029, US-031, and US-035 (plus related frontend/infra merges on `develop`).
**Current baseline:** `develop` / `origin/develop` at `8461a16` (PR `#42`); US-029 changes are still isolated on `feature/US-029`.

## Summary

| Story | Status | Merge / evidence on `develop` | Remaining operational / verification gap |
|---|---|---|---|
| US-038 — Reproducible, optimized Docker build | **Merged into `develop` (PR `#31`)** | `0aa3604` (`feature/US-038`), plus baseline/CI fixes in PR `#34` | Local Docker Engine was unavailable; hosted GitHub Actions `docker-build` duration/image-size metrics require observing a completed Actions run. |
| US-026 — Pull-request CI | **Merged into `develop` (PR `#30`)** | `b2f23e9` (`feature/US-026`), updated in PR `#34` & PR `#36` | Workflow does not push or deploy (`push: false`). Hosted Actions run results are verified on GitHub Actions, not locally for Docker/Playwright driver under sandbox. |
| US-017 — Deployment smoke test | **Merged into `develop` (PR `#29`)** | `4af6c03` (`feature/US-017`), `scripts/smoke_test.py` | Unit tests use HTTP stubs; no verified sample image or revision-specific Azure smoke-test run is stored. Automatic CD wiring awaits `US-029`. |
| US-025 — CORS and network errors | **Merged into `develop` (PR `#28`)** | `5e96efb` (`feature/US-025`), `src/vsl/service.py` + `tests/test_cors.py` | Backend CORS allowlist (`VSL_ALLOWED_ORIGINS`) is in `develop`, and frontend error UX was later merged via `US-022` (`web/app.js`), but the live Azure Container App revision has not yet been updated with `VSL_ALLOWED_ORIGINS`. |
| US-031 — ACA traffic rollback | **Merged into `develop` (PR `#27`)** | `61f5e7f` (`feature/US-031`), `scripts/rollback.py` | Dry-run-first guarded CLI passes unit tests; live Azure CLI revision inspection, `Multiple` revision mode verification, and production rollback rehearsal have not occurred. Automatic rollback awaits `US-029`. |
| US-035 — README and runbook | **Merged into `develop` (PR `#24`)** | `3250e29` (`feature/US-035`), unified with post-merge updates | `README.md`, `docs/RUNBOOK.md`, and this status ledger were updated after subsequent merges (`#22`–`#36`) to remove conflict markers and reflect `develop` accurately. |

*(Additional merged stories on `develop` since `780b7aa`: `US-022` static frontend in PR `#23`, `US-018`/`US-019` Azure Terraform & OIDC in PR `#22`, `US-012` model lifecycle in PR `#32`, `US-024` Cloudflare Pages verification in PR `#33`, and bugfix PRs `#34` & `#36`.)*

## Implemented details on `develop`

### US-038
- Two-stage `Dockerfile` (`builder` and `runtime`) pinned to `python:3.12.7-slim-bookworm` SHA-256 digest with `--platform=linux/amd64`, BuildKit pip cache, non-root `appuser` (UID `10001`), `HEALTHCHECK`, and minimal `requirements-runtime.txt`.
- `.github/workflows/ci.yml` passes `GIT_SHA` and `BUILD_TIME` build-args, uses `type=gha` BuildKit cache, and reports image size & duration to `$GITHUB_STEP_SUMMARY`.

### US-026
- Added `.github/workflows/ci.yml`, `pyproject.toml`, Ruff/Black dev pins in `requirements-dev.txt`, and `tests/test_ci_workflow.py`.
- Workflow runs on PRs to `develop`/`main` and pushes to `develop`: installs `requirements-dev.txt`, `requirements.txt`, and Playwright (`chromium`, `firefox`), runs `ruff check src tests scripts`, `black --check src tests scripts`, `pytest tests -v`, and builds (without pushing) the `linux/amd64` Docker image.

### US-017
- Added `scripts/smoke_test.py`, `tests/test_smoke_test.py`, and `docs/api/US-017.md`.
- Requires `--url` and `--expected-sha`; verifies `/health` (`model_loaded=true`) and `/version` (`git_sha` match). Optional `--image` additionally verifies `/predict`.

### US-025
- Added strict origin parsing (`_configured_cors_origins`) and `CORSMiddleware` in `src/vsl/service.py`, plus `tests/test_cors.py` and `tests/test_cors_version.py`.
- `VSL_ALLOWED_ORIGINS` accepts exact comma-separated HTTP(S) origins and rejects wildcards (`*`), paths, queries, fragments, or credentials; `allow_credentials=False`.
- Static frontend error handling is implemented in `web/app.js` (`US-022`); live browser-to-ACA verification (`US-024`) remains blocked until a revision built from `develop` is deployed with `VSL_ALLOWED_ORIGINS=https://sign-language-classification.pages.dev`.

### US-031
- Added `scripts/rollback.py`, `tests/test_rollback.py`, and `docs/api/US-031.md`.
- Targets Azure Container Apps (`az containerapp`), defaults to read-only dry-run, and refuses unsupported revision mode, split/ambiguous traffic, or stale operator confirmations. `--apply` requires explicit current/target revision names, expected Git SHA, and service URL, then routes 100% traffic to the target and verifies `/health` and `/version`.
- Note: legacy `scripts/rollback.sh` (Cloud Run) remains on disk solely to satisfy `tests/test_ops_contract.py::test_ac_031_01_rollback_scripts_exist` until that test is updated.

### US-035
- `README.md`, `HUONG-DAN-CHAY.md`, `docs/RUNBOOK.md`, `docs/README.md`, and this file document the Azure Container Apps + Cloudflare Pages architecture, local setup, CI checks, cold-start triage, CORS configuration, guarded ACA rollback, and cloud cost checks.

## Remaining environment & delivery gaps

- **CD Automation (`US-029`):** Workflow implementation is on `feature/US-029` and is not merged or live-verified. Before first use, apply the main-branch OIDC federation through reviewed Terraform, verify GitHub Actions variables and the actual ACR name, and run a supervised staging deployment.
- **Azure OIDC Terraform Apply (`US-019`):** Staging ACR `vslacr3795` was imported into Terraform state, while apply awaits Entra permissions and `Microsoft.ManagedIdentity` provider registration (`AGENTS.md`). Note also a registry naming discrepancy to verify on Azure: `infra/environments/staging.tfvars` and `HO-SO-BAN-GIAO-HA-TANG.md` reference `vslacr3795`, whereas `docs/api/US-024.md` recorded live `vsl-api` pulling `vslacr4751.azurecr.io/vsl-api:latest`.
- **Cloudflare Pages E2E (`US-024`):** `AC-024-01` fails until `vsl-api` runs a CORS-enabled image with `VSL_ALLOWED_ORIGINS`; `AC-024-02` is unverified while ACA keeps `minReplicas=1`.
- **Live ACA Rollback Rehearsal (`US-031`):** Not yet executed on Azure.
