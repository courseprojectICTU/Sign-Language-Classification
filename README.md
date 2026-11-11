# Vietnamese Sign Language Classification

Dự án phân loại **23 ký tự bảng chữ cái ngôn ngữ ký hiệu tiếng Việt** (`a, b, c, d, đ, e, g, h, i, k, l, m, n, o, p, q, r, s, t, u, v, x, y`) từ ảnh và webcam. Pipeline sử dụng MediaPipe trích xuất **93 tọa độ landmark** (21 điểm bàn tay + 10 điểm khuôn mặt), dựng **heatmap `224x224x3`**, và suy luận bằng mô hình CNN **ResNet50** (Keras).

---

## Architecture and current delivery status

- **Backend (`src/vsl/`):** FastAPI service tại `src/vsl/service.py`, lắng nghe cổng `8080`, cung cấp `GET /health`, `GET /version`, và `POST /predict`, cùng CORS allowlist tường minh qua `VSL_ALLOWED_ORIGINS` (`US-025`).
- **Model pipeline:** 93 hand/face coordinates → `create_heatmap` (`src/vsl/heatmap.py`) → ResNet50 Caffe preprocessing → softmax 23 lớp (`src/vsl/labels.py`). File trọng số được lưu bằng Git LFS tại `train/vsl_cnn_pose_keras.h5` (~137 MB). Bộ dữ liệu landmark gồm 23 thư mục tại `data/anphabet/` (tổng **1.609 file CSV**; 70 mẫu/ký tự, riêng `đ` có 69 mẫu).
- **Frontend (`web/`):** Giao diện web tĩnh (`web/index.html`, `web/app.js`, `web/styles.css`, `web/config.js`, `web/labels.json`), cho phép tải ảnh hoặc chụp từ camera và gọi `POST /predict` (`US-022`). Đã triển khai thử lên Cloudflare Pages (`https://sign-language-classification.pages.dev`, `US-024`), hiện chờ cập nhật `VSL_ALLOWED_ORIGINS` trên Azure Container Apps để trình duyệt gọi API không bị chặn CORS.
- **Container & CI:** `Dockerfile` multi-stage `linux/amd64` ghim digest `python:3.12.7-slim-bookworm`, dùng `requirements-runtime.txt` và non-root `appuser` (`US-038`). Workflow PR CI (`.github/workflows/ci.yml`, `US-026`) chạy Ruff, Black, full `pytest`, và Docker build (không push).
- **Cloud & IaC (`infra/`):** Đích triển khai đám mây là **Microsoft Azure Container Apps (ACA)** (không phải Cloud Run). Thư mục `infra/` khai báo Terraform `azurerm` + Azure Blob remote state (`US-018`) và ACR/IAM/GitHub OIDC (`US-019`). Workflow CD tự động (`US-029`) chưa có trên `develop`.
- **Operations CLI (`scripts/`):** Đã có `scripts/smoke_test.py` (`US-017`), `scripts/rollback.py` (`US-031`, dry-run mặc định cho ACA), `scripts/benchmark_cold_start.py` (`US-013`), và `scripts/generate_web_labels.py` (`US-022`). Lưu ý các kiểm thử cloud trực tiếp (live smoke test, live rollback rehearsal, `terraform apply` hoàn chỉnh cho OIDC) vẫn cần xác minh trên môi trường Azure thực tế.

---

## Repository map

| Path | Purpose |
|---|---|
| `src/vsl/` | Shared labels, config, landmarks contract, heatmap, and FastAPI service |
| `web/` | Static web frontend (`index.html`, `app.js`, `styles.css`, `config.js`, `labels.json`) |
| `tests/` | Unit, API-contract, Playwright web acceptance, Terraform, and regression tests |
| `scripts/` | Cold-start benchmark, web label generator, smoke test, and guarded ACA rollback CLIs |
| `infra/` | Terraform AzureRM, Azure Blob state bootstrap, ACR cleanup, and GitHub OIDC IaC |
| `.github/workflows/` | PR lint/test/Docker build (`ci.yml`) and manual Azure OIDC smoke check (`azure-oidc-smoke.yml`) |
| `data/anphabet/` | Landmark CSV dataset (23 characters, 1,609 CSV files) |
| `train/` | Training notebook (`train_cnn_pose_keras.ipynb`) and Git-LFS model (`vsl_cnn_pose_keras.h5`) |
| `process_images/` | Data collection notebook (`capture_and_process_images.ipynb`) |
| `docs/` | Architecture ADRs, API/CLI contracts (`docs/api/`), Azure guides, status, and `RUNBOOK.md` |

---

## Run locally

Use Python 3.12 and ensure Git LFS has pulled the model file before running:

```powershell
git lfs install
git lfs pull
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m uvicorn src.vsl.service:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to try `/health`, `/version`, and `/predict`.

For webcam inference and Jupyter notebooks, see [HUONG-DAN-CHAY.md](HUONG-DAN-CHAY.md), [`run_realtime.py`](run_realtime.py), and [`run_realtime.cmd`](run_realtime.cmd).

---

## Tests and lint

Install dev dependencies and Playwright browsers:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
& ".\.venv\Scripts\python.exe" -m playwright install chromium firefox
```

Run lint, formatting, and the full test suite:

```powershell
& ".\.venv\Scripts\ruff.exe" check src tests scripts
& ".\.venv\Scripts\black.exe" --check src tests scripts
& ".\.venv\Scripts\python.exe" -m pytest tests -v
```

The NumPy-only heatmap and repository contract tests can be run quickly without TensorFlow:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -v tests/test_heatmap.py tests/test_heatmap_contract.py
```

*(Trên Windows, nếu `.venv\Scripts\python.exe` gặp lỗi nạp DLL `_ctypes`/`cv2`, dùng Python 3.12 gốc theo hướng dẫn trong [docs/process/WORKFLOW.md](docs/process/WORKFLOW.md)).*

---

## Build and run Docker locally

`Dockerfile` uses a two-stage `linux/amd64` build pinned to a `python:3.12.7-slim-bookworm` SHA-256 digest and installs runtime-only packages from `requirements-runtime.txt`:

```powershell
$sha = (git rev-parse HEAD).Trim()
docker build --platform linux/amd64 --build-arg "GIT_SHA=$sha" --tag vsl-api:local .
docker run --detach --publish 8080:8080 --name vsl-api-local vsl-api:local
curl.exe --fail http://localhost:8080/health
curl.exe --fail http://localhost:8080/version
docker logs vsl-api-local
docker stop vsl-api-local
docker rm vsl-api-local
```

---

## Environment variables

| Name | Purpose | Default / notes |
|---|---|---|
| `VSL_MODEL_PATH` | Model file path | `train/vsl_cnn_pose_keras.h5` under repo root |
| `VSL_DATA_DIR` | Landmark data directory | `data/anphabet` under repo root |
| `VSL_MODEL_VERSION` | Model version returned by API | `v1.0` |
| `GIT_SHA` | Source revision returned by `/version` | Docker build arg / git fallback (`unknown` if unavailable) |
| `BUILD_TIME` | Build timestamp returned by `/version` | Docker build arg / service startup UTC ISO 8601 |
| `VSL_ALLOWED_ORIGINS` | Exact comma-separated CORS origins | Empty by default (default-deny); wildcards rejected |

No application secret is required for local inference. Never commit cloud credentials, subscription secrets, or Terraform state files to Git.

---

## Deploy and operate

- **Cloud guide:** [docs/infrastructure/HUONG-DAN-TRIEN-KHAI-AZURE.md](docs/infrastructure/HUONG-DAN-TRIEN-KHAI-AZURE.md) and [docs/infrastructure/HO-SO-BAN-GIAO-HA-TANG.md](docs/infrastructure/HO-SO-BAN-GIAO-HA-TANG.md).
- **Terraform IaC:** [infra/README.md](infra/README.md).
- **Operations & troubleshooting:** [docs/RUNBOOK.md](docs/RUNBOOK.md) (CI failures, cold starts, smoke test, CORS, guarded ACA rollback, and cloud cost triage).
- **Post-deploy smoke test (`US-017`):**
  ```powershell
  python scripts/smoke_test.py --url "https://<revision-fqdn>" --expected-sha "<commit-sha>" --image "<path-to-valid-image>"
  ```
- **Guarded ACA rollback (`US-031`, dry-run by default):**
  ```powershell
  python scripts/rollback.py --resource-group "<resource-group>" --app-name "<container-app>"
  ```
