# Vietnamese Sign Language Classification

This repository classifies 23 Vietnamese sign-language alphabet characters from
images. The Python service extracts hand and face landmarks with MediaPipe,
converts them to a heatmap, and runs a ResNet50-based Keras model.

## Architecture and current delivery status

- **Backend:** FastAPI in `src/vsl/service.py`; the Docker container listens on
  port `8080`. The API provides `GET /health`, `GET /version`, and `POST
  /predict`.
- **Model pipeline:** 93 hand/face coordinates → `create_heatmap` → ResNet50
  inference. The model file is stored with Git LFS at
  `train/vsl_cnn_pose_keras.h5`.
- **Cloud target:** project infrastructure documents describe Azure Container
  Apps (ACA), not Cloud Run. The repository has no frontend source and no
  deployment automation in `develop`.
- **Feature branches:** CI (US-026), smoke test (US-017), CORS (US-025), and
  guarded ACA rollback (US-031) are separate PR branches. Their behavior is
  not part of `develop` until those PRs are reviewed and merged. The existing
  `feature/US-038` branch was not changed because it already contains a mixed
  changeset; multi-stage image optimization is therefore not available here.
- The infrastructure handoff document reports a staging environment, but its
  current health, revision state, URL, and permissions were not verified as
  part of this documentation update. Do not treat examples below as proof of a
  successful deployment.

## Repository map

| Path | Purpose |
|---|---|
| `src/vsl/` | Shared labels, configuration, landmarks, heatmap, and FastAPI service |
| `tests/` | Unit, API-contract, and regression tests |
| `scripts/` | Benchmark and operational CLIs; branch-only scripts are identified below |
| `data/anphabet/` | Landmark CSV training data |
| `train/` | Training notebook and Git-LFS model |
| `process_images/` | Data collection notebook |
| `docs/architecture/` | Architecture decisions |
| `docs/api/` | Per-story API and CLI contracts |
| `docs/infrastructure/` | Azure deployment and handoff material |
| `docs/RUNBOOK.md` | Operational troubleshooting and recovery |
| `docs/implementation/US-IMPLEMENTATION-STATUS.md` | Requested-story progress, evidence, and branch dependencies |

## Run locally

Use Python 3.12. Clone the model from Git LFS before starting the API:

```powershell
git lfs install
git lfs pull
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m uvicorn src.vsl.service:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to try the API.
`GET /health` reports model readiness; use the Swagger UI to submit an image to
`POST /predict`. The repository does not include a verified sample image.

For webcam inference, see [HUONG-DAN-CHAY.md](HUONG-DAN-CHAY.md) and
[`run_realtime.py`](run_realtime.py).

## Tests and lint

Run the complete test suite:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests -v
```

The NumPy-only heatmap and repository contract tests can be run separately:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -v tests/test_heatmap.py tests/test_heatmap_contract.py
```

The PR workflow and Ruff/Black configuration are on `feature/US-026`; they are
not yet present on `develop`. After US-026 is merged and its dev dependencies
are installed, run:

```powershell
ruff check src tests scripts
black --check src tests scripts
```

That workflow runs on pull requests, executes selected tests, and builds—but
does not push—the Docker image. See
[`docs/implementation/US-IMPLEMENTATION-STATUS.md`](docs/implementation/US-IMPLEMENTATION-STATUS.md)
for the branch and verification status.

## Build and run Docker locally

The current Dockerfile is single-stage and is not pinned by digest. US-038
optimization has not been applied to this branch.

```powershell
$sha = (git rev-parse HEAD).Trim()
docker build --build-arg "GIT_SHA=$sha" --tag vsl-api:local .
docker run --detach --publish 8080:8080 --name vsl-api-local vsl-api:local
curl.exe --fail http://localhost:8080/health
curl.exe --fail http://localhost:8080/version
docker logs vsl-api-local
docker stop vsl-api-local
docker rm vsl-api-local
```

Docker must be running. Do not publish an image from the pull-request CI
workflow; publishing/deployment is not currently automated.

## Deploy and operate

The documented cloud target is **Azure Container Apps**, not Cloud Run.
Deployment is not automated in `develop`. Review
[`docs/infrastructure/HUONG-DAN-TRIEN-KHAI-AZURE.md`](docs/infrastructure/HUONG-DAN-TRIEN-KHAI-AZURE.md)
and [`docs/RUNBOOK.md`](docs/RUNBOOK.md) before changing a cloud resource.
Use a unique immutable image tag and verify `/health` and `/version` after
deployment. Do not copy credentials or subscription identifiers into source
control.

The following variables are supported by the current application or Docker
build:

| Name | Purpose | Default/notes |
|---|---|---|
| `VSL_MODEL_PATH` | Model file path | `train/vsl_cnn_pose_keras.h5` under the repository root |
| `VSL_DATA_DIR` | Landmark data directory | `data/anphabet` under the repository root |
| `VSL_MODEL_VERSION` | Model version returned by the API | `v1.0` |
| `GIT_SHA` | Source revision returned by `/version` | Docker build argument; `unknown` if unavailable |
| `BUILD_TIME` | Build time returned by `/version` | Docker build argument; service startup time if unset/invalid |
| `VSL_ALLOWED_ORIGINS` | Exact browser origins allowed by CORS | Implemented on `feature/US-025`; no default allowlist, no wildcard |

No application secret is required for local inference. Azure authentication
must use the operator's approved Azure identity. The current CI branch does not
push to a registry and requires no cloud credentials. The CORS origin is
configuration, not a secret; only configure a verified frontend origin.

## Smoke test, CORS, and rollback availability

These are **branch-only** until their PRs merge:

- **Smoke test (US-017):** `feature/US-017` provides
  `scripts/smoke_test.py`, which checks `/health`, the expected `/version`
  SHA, and `/predict` using a caller-supplied valid image. It has not been run
  against a deployed revision in this task. Usage and prerequisites are in the
  [US-017 contract](https://github.com/courseprojectICTU/Sign-Language-Classification/blob/feature/US-017/docs/api/US-017.md)
  on that branch.
- **CORS (US-025):** `feature/US-025` provides an exact-origin
  `VSL_ALLOWED_ORIGINS` allowlist and preflight support. There is no frontend
  source or verified Cloudflare Pages hostname in this repository. Do not
  invent an origin.
- **Rollback (US-031):** `feature/US-031` provides a dry-run-first Azure
  Container Apps script. No production rollback rehearsal or automatic
  rollback integration has been performed. See
  [the US-031 contract](https://github.com/courseprojectICTU/Sign-Language-Classification/blob/feature/US-031/docs/api/US-031.md)
  on that branch and
  [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

## Operations and troubleshooting

Use [the runbook](docs/RUNBOOK.md) for CI failures, cold starts, unavailable
backend, CORS, smoke-test failures, rollback safeguards, and cloud-cost checks.
Do not claim production health, smoke-test success, or rollback readiness
without current runtime evidence.
