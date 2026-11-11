# Requested User Stories — Implementation and Handoff Status

**Updated:** 2026-11-11
**Scope:** US-038, US-026, US-017, US-025, US-031, and US-035 (plus related frontend/infra merges on `develop`).
**Current baseline:** `develop` / `origin/develop` at `8461a16` (PR `#42`), with staging Azure rollout (`cae-vsl-staging-std`, `vsl-api`, `vsl-vietnam`) verified live on 2026-11-11.

## Summary

| Story | Status | Merge / evidence on `develop` | Remaining operational / verification gap |
|---|---|---|---|
| US-038 — Reproducible, optimized Docker build | **Merged into `develop` (PR `#31`)** | `0aa3604` (`feature/US-038`), baseline/CI fixes in PR `#34`, and `acr-publish.yml` (`42843489497`) | Local Docker Engine was unavailable; hosted GitHub Actions `acr-publish.yml` (`42843489497`) built, verified, and pushed `linux/amd64` (`9a1c3aa847e19ef4a85d6bec9d36afc3d5c5e76f`). |
| US-026 — Pull-request CI | **Merged into `develop` (PR `#30`)** | `b2f23e9` (`feature/US-026`), updated in PR `#34` & PR `#36` | Workflow does not push or deploy (`push: false`). Hosted Actions run results are verified on GitHub Actions, not locally for Docker/Playwright driver under sandbox. |
| US-017 — Deployment smoke test | **Merged into `develop` (PR `#29`)** | `4af6c03` (`feature/US-017`), `scripts/smoke_test.py` | Unit tests use HTTP stubs; `/health`, `/version`, and CORS/`POST /predict` (`no_hand`) passed live on 2026-11-11, while `smoke_test.py --image` with a real hand+face sample image and CD wiring (`US-029`) remain pending. |
| US-011 — Keras H5 to ONNX export & parity check | **Implemented on `feature/US-011` (awaiting Gate D)** | `scripts/export_onnx.py` (`TSK-017`, `TSK-018`), `tests/test_onnx_parity.py`, `docs/api/US-011.md`, `requirements-dev.txt`, `.gitignore` | `AC-011-01` verified on `CPUExecutionProvider` (`max_abs_diff=1.583e-06`, `23/23` `argmax`, ONNX `96,119,874` vs H5 `137,042,364` bytes). Per `Q1`/`Q2`, runtime container (`Dockerfile`, `requirements-runtime.txt`, `src/vsl/service.py`) stays on Keras H5 and binary `.onnx` files are gitignored; pending Gate D sign-off and PR merge to `develop`. |
| US-025 — CORS and network errors | **Live on staging & merged (PR `#28`)** | `5e96efb` (`feature/US-025`), `src/vsl/service.py` + `tests/test_cors.py` | `VSL_ALLOWED_ORIGINS=https://sign-language-classification.pages.dev` is live on both App Service `vsl-vietnam` and Standard Container App `vsl-api` (`9a1c3aa847e19ef4a85d6bec9d36afc3d5c5e76f`); preflight `200`, `POST /predict` `200`, and disallowed-origin `400` were verified on 2026-11-11. |
| US-031 — ACA traffic rollback | **Merged into `develop` (PR `#27`)** | `61f5e7f` (`feature/US-031`), `scripts/rollback.py` | `vsl-api` on `cae-vsl-staging-std` is now provisioned in `Multiple` revision mode (`vsl-api--lhkogbo`); live rollback rehearsal with a second active revision and automatic CD wiring (`US-029`) remain pending. |
| US-033 — Azure Billing Budget & Entra ID MFA | **Verified on staging (`feature/US-033`)** | `infra/budget.tf` (`vsl-monthly-cost-guardrail-staging`), `docs/RUNBOOK.md` (Section 7), `docs/api/US-033.md`, `tests/test_us033_cost_guardrails.py` | Subscription budget (`$5/month`, `20%` = `$1` and `100%` = `$5` `Actual` alerts to `Owner`) and Entra ID `Security defaults: Enabled` verified on Azure Portal (`373b1f03-330f-4302-a9e9-aa1fe793bf2e`); optional extra `budget_alert_emails` can be passed if additional recipients beyond `Owner` are desired. |
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
- Requires `--url`, `--expected-sha`, and `--image`; verifies `/health` (`model_loaded=true`), `/version` (`git_sha` match), and `/predict` response schema.

### US-011
- Added `scripts/export_onnx.py` (`TSK-017` / `TSK-018`), `tests/test_onnx_parity.py`, `docs/api/US-011.md`, `tf2onnx==1.17.0` / `onnx==1.22.0` / `onnxruntime==1.31.1` in `requirements-dev.txt` (pure ASCII), and `*.onnx` / `models/*.onnx` ignore rules in `.gitignore`.
- Exports `train/vsl_cnn_pose_keras.h5` via temporary `SavedModel` (`opset 15`) and verifies `CPUExecutionProvider` numerical parity on the canonical 23-class `BR-006` Caffe-preprocessed batch (`max_abs_diff = 1.583e-06 < 1e-4`, `23/23` `argmax`; H5 `137,042,364` bytes -> ONNX `96,119,874` bytes, ratio `0.7014`; warmed-up local batch median `1329.4 ms` Keras vs `639.15 ms` ORT; `load_ms` `1099.6 ms` vs `333.81 ms`), keeping runtime Docker/FastAPI on TensorFlow/Keras (`Q1`) and `.onnx` out of Git (`Q2`).

### US-025
- Added strict origin parsing (`_configured_cors_origins`) and `CORSMiddleware` in `src/vsl/service.py`, plus `tests/test_cors.py` and `tests/test_cors_version.py`.
- `VSL_ALLOWED_ORIGINS` accepts exact comma-separated HTTP(S) origins and rejects wildcards (`*`), paths, queries, fragments, or credentials; `allow_credentials=False`.
- Static frontend error handling is implemented in `web/app.js` (`US-022`), and `VSL_ALLOWED_ORIGINS=https://sign-language-classification.pages.dev` is live on both App Service `vsl-vietnam` and Standard Container App `vsl-api` (`9a1c3aa847e19ef4a85d6bec9d36afc3d5c5e76f`).

### US-031
- Added `scripts/rollback.py`, `tests/test_rollback.py`, and `docs/api/US-031.md`.
- Targets Azure Container Apps (`az containerapp`), defaults to read-only dry-run, and refuses unsupported revision mode, split/ambiguous traffic, or stale operator confirmations. `--apply` requires explicit current/target revision names, expected Git SHA, and service URL, then routes 100% traffic to the target and verifies `/health` and `/version`.
- Note: legacy `scripts/rollback.sh` (Cloud Run) remains on disk solely to satisfy `tests/test_ops_contract.py::test_ac_031_01_rollback_scripts_exist` until that test is updated.

### US-035
- `README.md`, `HUONG-DAN-CHAY.md`, `docs/RUNBOOK.md`, `docs/README.md`, and this file document the Azure Container Apps + Cloudflare Pages architecture, local setup, CI checks, cold-start triage, CORS configuration, guarded ACA rollback, and cloud cost checks.

### US-033
- Added `infra/budget.tf` declaring `azurerm_consumption_budget_subscription.monthly` (`$5 USD/month`, `Actual` notifications at `20%` = `$1` and `100%` = `$5`, `Owner` role + configurable `budget_alert_emails`, gated by `enable_billing_budget`), along with `docs/api/US-033.md`, `tests/test_us033_cost_guardrails.py`, and Azure-aligned cost/MFA/prohibited-services guidance consolidated in Section 7 of `docs/RUNBOOK.md`. Removed the earlier GCP `infra/billing-budget/` and `docs/runbook/` files and restored strict no-GCP enforcement in `tests/test_us018_terraform.py`.

## Remaining environment & delivery gaps

- **Azure Cost Budget & Entra ID MFA (`US-033`):** `azurerm_consumption_budget_subscription.monthly[0]` (`vsl-monthly-cost-guardrail-staging`, `$5/month`, `20%`/`100%` `Actual` to `Owner`) and Entra ID `Security defaults: Enabled` are verified live on staging (`373b1f03-330f-4302-a9e9-aa1fe793bf2e`); pending PR merge to `develop` (plus optional `budget_alert_emails` if additional recipients beyond `Owner` are needed).

- **CD Automation (`US-029`):** Not yet present in `develop`; image publishing and ACA deployment remain manual (manual OIDC ACR publish workflow `.github/workflows/acr-publish.yml` is merged on `develop`).
- **Azure OIDC & Staging Infra (`US-019`):** `Microsoft.ManagedIdentity` is registered and staging Terraform is applied against `vslstate2026` (`vsl-github-actions-staging` has `AcrPush` on `vslacr3795` and `Container Apps Contributor` on recreated `vsl-api`); GitHub OIDC smoke test and ACR publish (`42843489497`) passed. Only `azurerm_container_registry_task.cleanup` remains blocked by Azure for Students (`TasksOperationsNotAllowed`).
- **Cloudflare Pages E2E (`US-024`):** `vslacr3795.azurecr.io/vsl-api:9a1c3aa847e19ef4a85d6bec9d36afc3d5c5e76f` with `VSL_ALLOWED_ORIGINS=https://sign-language-classification.pages.dev` is live on both App Service `vsl-vietnam` (`web/config.js`) and Standard Container App `vsl-api` (`cae-vsl-staging-std`), passing `/health`, `/version`, CORS preflight, and `POST /predict` (`no_hand`) checks; remaining gaps are a live real-photo (`hand+face`) E2E verification and `AC-024-02` scale-to-zero measurement while `minReplicas=1`.
- **Live ACA Rollback Rehearsal (`US-031`):** Not yet executed on Azure (`vsl-api` on `cae-vsl-staging-std` is now provisioned in `Multiple` revision mode).
