# Operations Runbook

This runbook describes the repository's actual cloud target architecture: FastAPI
in **Azure Container Apps (ACA)** paired with the static frontend in `web/`
(deployed on Cloudflare Pages). It is not a Cloud Run guide. Automated CD
deployment (`US-029`) and automatic rollback after a failed deployment smoke test
are not yet implemented in `develop`. Review
[US implementation status](implementation/US-IMPLEMENTATION-STATUS.md) before
operating cloud resources.

---

## 1. Before operating a cloud resource

1. Confirm the Azure subscription, resource group, Container App name, URL, and
   the environment (staging or production) with the service owner.
2. Authenticate with an approved Azure identity:

   ```powershell
   az login
   az account show --output table
   ```

3. Use a unique immutable image tag and record the Git SHA. Do not copy
   credentials, subscription IDs, or tenant IDs into source control.
4. Do not run deployment, traffic, or resource deletion commands unless the
   environment and impact have been explicitly confirmed.

Example variables below are placeholders:

```powershell
$ResourceGroup = "<resource-group>"
$AppName = "<container-app>"
$ApiUrl = "https://<container-app-fqdn>"
```

---

## 2. Backend is unavailable or unhealthy

Start with read-only checks:

```powershell
az containerapp show --name $AppName --resource-group $ResourceGroup --output json
az containerapp revision list --name $AppName --resource-group $ResourceGroup --output table
az containerapp logs show --name $AppName --resource-group $ResourceGroup --tail 100
curl.exe --include "$ApiUrl/health"
curl.exe --include "$ApiUrl/version"
```

- `/health` should return HTTP 200 and `model_loaded: true`.
- `/version` should return the expected `git_sha`; `unknown` is not proof that
  the intended image is running.
- Inspect startup/model-loading errors and revision provisioning state before
  restarting or changing traffic.
- If the app is not ready, preserve the current revision and logs for
  diagnosis. Do not delete the app or resource group as a troubleshooting step.
- The container also defines a Docker `HEALTHCHECK`. A passing container check
  does not replace checking the public endpoint.

For local isolation, run the API or Docker container using the commands in
[README.md](../README.md). If local succeeds and the cloud endpoint does not,
investigate ACA ingress, image pull, resource limits, and revision state.

---

## 3. Khởi động nguội chậm (Cold start is slow)

1. Record the request time, endpoint, response status, and revision SHA.
2. Check ACA logs and replica/revision state. Note that `docs/infrastructure/HO-SO-BAN-GIAO-HA-TANG.md`
   describes `minReplicas = 1` on staging, which avoids scale-to-zero cold starts;
   verify live replica configuration in Azure rather than assuming from docs.
3. Distinguish a cold start from a slow request. Do not report a cold-start
   measurement unless the required preflight evidence proves the environment
   was cold.
4. The `scripts/benchmark_cold_start.py` harness requires an operator-provided
   preflight command and URL. Follow its contract in
   [`docs/api/US-013.md`](api/US-013.md); do not change replica counts or scale
   production to zero without owner approval.

---

## 4. Pipeline CI báo đỏ (CI pull request fails)

The pull-request CI workflow (`.github/workflows/ci.yml`, US-026) is active on
`develop` and runs Ruff, Black `--check`, the full `pytest` suite (including
Playwright browser tests), and a `linux/amd64` Docker build without pushing.

Reproduce the CI checks locally:

```powershell
ruff check src tests scripts
black --check src tests scripts
pytest tests -v
```

*(On Windows setups where `.venv\Scripts\python.exe` hits the `_ctypes`/`cv2`
DLL issue, run `pytest` and `black` via `"D:\program\python\python.exe"`, as
documented in [docs/process/WORKFLOW.md](process/WORKFLOW.md)).*

For Docker build failures:

1. Verify Docker Engine is running and Git LFS pulled `train/vsl_cnn_pose_keras.h5`.
2. Ensure `--platform=linux/amd64` and `requirements-runtime.txt` packages do
   not introduce missing OS/compiler dependencies into the slim runtime stage.
3. CI build duration and image-size metrics are emitted to `$GITHUB_STEP_SUMMARY`
   only when the `docker-build` job completes.

---

## 5. Smoke test thất bại & Hoàn tác thủ công (Smoke test failure & ACA rollback)

`scripts/smoke_test.py` (US-017) and `scripts/rollback.py` (US-031) are
available on `develop`, though automatic CD wiring (`US-029`) is not yet
implemented.

### 5.1. Chạy Smoke Test

Supply an image file containing a usable hand and face, the exact expected Git
SHA of the target revision, and that revision's URL:

```powershell
python scripts/smoke_test.py `
  --url $ApiUrl `
  --expected-sha "<expected-git-sha>" `
  --image "<path-to-valid-image>"
```

The script checks `/health`, `/version`, and `/predict`; any failed check exits
non-zero. If it fails:

1. Keep the output and identify which endpoint failed.
2. Check the same endpoint and revision logs directly.
3. Verify the supplied SHA belongs to the image and the image is valid.
4. Do not declare the deployment healthy or shift traffic until verified.
5. If an operator chooses manual rollback, follow the guarded procedure below.

### 5.2. Quy trình Rollback thủ công trên Azure Container Apps

`scripts/rollback.py` targets **Azure Container Apps** (not Cloud Run). It
requires Azure CLI (`az`), approved permissions, ACA `Multiple` revision mode,
at least two active revisions, and exactly one revision receiving 100% of
traffic. *(Note: `scripts/rollback.sh` is a legacy Cloud Run artifact retained
only to satisfy existing file-existence checks in `tests/test_ops_contract.py`;
do not use it against Azure.)*

First inspect the proposed target in read-only dry-run mode:

```powershell
python scripts/rollback.py --resource-group $ResourceGroup --app-name $AppName
```

Confirm the current and target revisions with the service owner. If approved,
apply with explicit confirmations:

```powershell
python scripts/rollback.py `
  --resource-group $ResourceGroup `
  --app-name $AppName `
  --expected-current-revision "<current-revision>" `
  --target-revision "<previous-revision>" `
  --expected-sha "<previous-revision-git-sha>" `
  --url $ApiUrl `
  --apply
```

The script verifies traffic weights, `/health`, and `/version`. If post-change
verification fails, stop and inspect ACA state manually. Do not describe a
rollback as rehearsed until an approved cloud rehearsal has completed and its
evidence is recorded.

---

## 6. CORS failure in a browser

The backend CORS middleware (US-025) is implemented in `src/vsl/service.py`,
and the static frontend in `web/` is deployed on Cloudflare Pages (`US-024`).
However, if the live ACA revision has not yet been updated with
`VSL_ALLOWED_ORIGINS`, browser requests will fail CORS checks.

1. Confirm the exact deployed frontend origin (e.g., `https://sign-language-classification.pages.dev`).
2. Set `VSL_ALLOWED_ORIGINS` to the exact origin(s), comma-separated, including
   scheme and optional port, with no path or trailing slash. Wildcards (`*`) are
   rejected by the service startup parser.
3. For an ACA app running a revision built from `develop` (with US-025 merged),
   configure the environment only after reviewing the target:

   ```powershell
   $FrontendOrigin = "https://sign-language-classification.pages.dev"
   az containerapp update --name $AppName --resource-group $ResourceGroup `
     --set-env-vars "VSL_ALLOWED_ORIGINS=$FrontendOrigin"
   ```

4. Verify preflight (`OPTIONS /predict`) and `GET /health` return
   `Access-Control-Allow-Origin` for the configured origin while unlisted origins
   do not receive that header. Do not use CORS as a substitute for authentication.

---

## 7. Vượt ngân sách / Chi phí vượt dự kiến (Cloud cost exceeds expectations)

1. Review Azure Cost Management / Cost Analysis (and Sponsorship balance if
   applicable) for the correct subscription and billing period.
2. Check ACA replica counts (`minReplicas`/`maxReplicas`), CPU/memory, ACR
   image retention (`infra/registry.tf` configures a daily `acr purge` task
   keeping 3 tags), Log Analytics ingestion/retention, and other resources.
3. Do not lower minimum replicas, scale to zero, or delete resources solely to
   reduce cost without assessing availability and obtaining owner approval.
4. Set an appropriate budget/alert in Azure for the billing account. This
   repository does not automatically configure cost alerts.

---

## 8. Environment variables and credentials

| Variable / credential | Use | Availability |
|---|---|---|
| `VSL_MODEL_PATH` | Override the model path | Current backend; defaults to `train/vsl_cnn_pose_keras.h5` |
| `VSL_DATA_DIR` | Override the landmark dataset path | Current backend; defaults to `data/anphabet` |
| `VSL_MODEL_VERSION` | Override model version metadata | Current backend; defaults to `v1.0` |
| `GIT_SHA` | Identify source revision from `/version` | Docker build metadata; use an immutable commit SHA |
| `BUILD_TIME` | Build timestamp from `/version` | Docker build metadata; ISO-8601 UTC recommended |
| `VSL_ALLOWED_ORIGINS` | Exact CORS origin allowlist | Current backend (`US-025`); empty by default (default-deny) |
| Azure CLI / OIDC identity | Read/manage ACA and ACR via Terraform/Actions | Operator-managed or GitHub OIDC (`US-019`); never commit secrets |

There are no GitHub cloud secrets needed by the `US-026` pull-request CI because
it does not push or deploy. Do not commit service-principal secrets or ACR
passwords; use GitHub Actions OIDC (`US-019`, `.github/workflows/azure-oidc-smoke.yml`)
when provisioning deployment workflows.
