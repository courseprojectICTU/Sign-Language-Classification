# Operations Runbook

This runbook describes the repository's actual target architecture: FastAPI in
Azure Container Apps (ACA). It is not a Cloud Run guide. There is no frontend
source, no deployment workflow in `develop`, and no automatic rollback after a
failed deployment smoke test. Review
[US implementation status](implementation/US-IMPLEMENTATION-STATUS.md) before
following branch-only instructions.

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
- The service also has a Docker health check. A passing container check does
  not replace checking the public endpoint.

For local isolation, run the API or Docker container using the commands in
[README.md](../README.md). If local succeeds and the cloud endpoint does not,
investigate ACA ingress, image pull, resource limits, and revision state.

## 3. Cold start is slow

1. Record the request time, endpoint, response status, and revision SHA.
2. Check ACA logs and replica/revision state. The infrastructure handoff
   describes a staging `minReplicas` setting, but that live setting must be
   verified in Azure; documentation is not runtime evidence.
3. Distinguish a cold start from a slow request. Do not report a cold-start
   measurement unless the required preflight evidence proves the environment
   was cold.
4. The `scripts/benchmark_cold_start.py` harness requires an operator-provided
   preflight command and URL. Follow its contract in
   [`docs/api/US-013.md`](api/US-013.md); do not change replica counts or scale
   production to zero without approval.

## 4. CI pull request fails

The CI workflow is on `feature/US-026` and becomes active only after that PR is
merged. It runs Ruff, Black, selected NumPy-only tests, and a Docker build for
`linux/amd64` without pushing an image.

After US-026 is available in the checkout, reproduce its checks:

```powershell
ruff check src tests scripts
black --check src tests scripts
python -m pytest -v tests/test_ci_workflow.py tests/test_config.py tests/test_dockerfile.py tests/test_heatmap.py tests/test_heatmap_contract.py tests/test_labels.py tests/test_requirements.py
```

For Docker build failures, verify Docker Engine is running, the Git LFS model
was downloaded, and `docker buildx` can access the repository context. CI build
duration/image-size metrics are emitted only when the workflow reaches its
metrics step. The workflow does not push an image or deploy an app.

## 5. Smoke test fails

The standalone script is on `feature/US-017`; it is not part of `develop` until
that PR is merged. Once available, supply an image file containing a usable
hand and face, the exact SHA expected from the target revision, and that
revision's URL:

```powershell
python scripts/smoke_test.py `
  --url $ApiUrl `
  --expected-sha "<expected-git-sha>" `
  --image "<path-to-valid-image>"
```

The script checks `/health`, `/version`, and `/predict`; a failed check exits
non-zero. If it fails:

1. Keep the output and identify which endpoint failed.
2. Check the same endpoint and revision logs directly.
3. Check that the supplied SHA belongs to the image and the image is valid.
4. Do not call the deployment successful or automatically roll back: there is
   no deployment workflow wired to this smoke test in the requested branches.
5. If an operator chooses manual rollback, use the guarded procedure below
   after confirming the target and current revision.

No verified sample image or live production smoke-test evidence is stored in
this repository.

## 6. CORS failure in a browser

The CORS implementation is on `feature/US-025`. Until it is merged and deployed,
the current backend must not be assumed to have that middleware.

After it is available:

1. Obtain the actual deployed frontend origin from its owner. The repository
   has no frontend code and does not establish a Cloudflare Pages hostname.
2. Set `VSL_ALLOWED_ORIGINS` to the exact origin, including scheme and
   optional port, with no path or trailing slash. Wildcards are rejected.
3. For an ACA app, configure the environment only after reviewing the target:

   ```powershell
   $FrontendOrigin = "https://<verified-frontend-host>"
   az containerapp update --name $AppName --resource-group $ResourceGroup `
     --set-env-vars "VSL_ALLOWED_ORIGINS=$FrontendOrigin"
   ```

4. Check the browser preflight request (`OPTIONS`) and response
   `Access-Control-Allow-Origin`. An unlisted origin should not receive that
   header. Do not use CORS as a substitute for authentication or authorization.

There is no JavaScript client in this repository to distinguish network
failures, cold starts, and API business errors; frontend error UX remains
unimplemented.

## 7. Manual ACA rollback

The rollback script is on `feature/US-031` and is not integrated into a
deployment pipeline. It is not Cloud Run tooling. It requires the Azure CLI,
approved Azure permissions, ACA `Multiple` revision mode, at least two active
revisions, and exactly one revision receiving 100% of traffic.

First inspect the proposed target without changing traffic:

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

The script reads traffic back and verifies `/health` and `/version`. If
post-change verification fails, traffic may already have changed; stop and
inspect ACA state manually. The script intentionally does not switch traffic
back to the unhealthy revision. Do not describe a rollback as rehearsed until
an approved cloud rehearsal has actually completed and its evidence is
recorded. Automatic rollback after smoke-test failure requires the separate,
currently absent US-029 deployment integration.

## 8. Cloud cost exceeds expectations

1. Review Azure Cost Management / Cost Analysis for the correct subscription
   and billing period; verify access before relying on CLI usage output.
2. Check ACA replica counts, CPU/memory, registry, log ingestion/retention, and
   other resources in the environment. Compare actual configuration with the
   approved service budget.
3. Do not lower minimum replicas, scale to zero, or delete resources solely to
   reduce cost without assessing availability and obtaining owner approval.
4. Set an appropriate budget/alert in Azure for the billing account. This
   repository does not configure or verify cost alerts.

## 9. Environment variables and credentials

| Variable / credential | Use | Availability |
|---|---|---|
| `VSL_MODEL_PATH` | Override the model path | Current backend; defaults to repository `train/vsl_cnn_pose_keras.h5` |
| `VSL_DATA_DIR` | Override the landmark dataset path | Current backend; defaults to repository `data/anphabet` |
| `VSL_MODEL_VERSION` | Override model version metadata | Current backend; defaults to `v1.0` |
| `GIT_SHA` | Identify source revision from `/version` | Docker build metadata; use an immutable commit SHA |
| `BUILD_TIME` | Build timestamp from `/version` | Docker build metadata; ISO-8601 UTC recommended |
| `VSL_ALLOWED_ORIGINS` | Exact CORS origin allowlist | US-025 branch only until merged |
| Azure CLI identity | Read ACA state; write traffic only for approved rollback | Operator-managed; never commit credentials |

There are no GitHub cloud secrets needed by the US-026 pull-request CI because
it does not push or deploy. Do not add a service-principal secret until an
approved deployment workflow actually requires one.
