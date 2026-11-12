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
2. Check ACA logs and replica/revision state. Note that `vsl-api` on staging
   now runs `minReplicas = 0`, `maxReplicas = 3` (managed in `infra/container_app.tf`
   under `US-020`, `startup_probe` on `/health:8080`), so idle periods scale to
   zero and trigger cold starts on the first wake-up request; always verify live
   replica configuration in Azure rather than assuming from docs.
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

## 7. Vượt ngân sách / Chi phí vượt dự kiến (Cloud cost guardrails, MFA & alert response)

### 7.1. Azure Billing Budget (`$1` / `$5`) và Sponsorship Balance

- Mục tiêu chi phí `0 VNĐ` (`BR-016` Free Tier Guardrails) trên gói **Azure for Students** (`100 USD` credit).
- Module `infra/budget.tf` khai báo tài nguyên `azurerm_consumption_budget_subscription.monthly` với hạn mức tháng `$5 USD` (`time_grain = "Monthly"`):
  - Ngưỡng `20%` (`$1 USD`, `Actual`, `GreaterThanOrEqualTo`): cảnh báo sớm đầu tiên.
  - Ngưỡng `100%` (`$5 USD`, `Actual`, `GreaterThanOrEqualTo`): ngưỡng khẩn cấp.
  - Người nhận mặc định là vai trò `Owner` của subscription, có thể bổ sung email nhóm qua `TF_VAR_budget_alert_emails` (tuyệt đối không commit email cá nhân vào Git).
- Vì `infra/provider.tf` dùng `resource_provider_registrations = "none"`, hãy kiểm tra đăng ký provider `Microsoft.Consumption` trước khi `terraform apply`:
  ```powershell
  az provider register --namespace Microsoft.Consumption
  terraform -chdir=infra plan -var-file="environments/staging.tfvars"
  ```
- **Lưu ý đặc thù gói Sponsorship / Azure for Students:** Budget chỉ gửi cảnh báo (không tự tắt dịch vụ) và dữ liệu Azure Cost Management có độ trễ cập nhật vài giờ. Ngoài Azure Cost Management trong Azure Portal, luôn đối chiếu số dư credit thực tế tại `https://www.microsoftazuresponsorships.com` (mục **Balance**). Nếu gói tài trợ chặn API `Microsoft.Consumption/budgets` khi `apply`, đặt `-var="enable_billing_budget=false"` và thiết lập cảnh báo tương đương trên Azure Portal / Sponsorships Portal.

### 7.2. Bắt buộc bật MFA trên Microsoft Entra ID

- MFA áp dụng cho **danh tính người dùng tương tác** truy cập Azure Portal / Azure CLI (khác với pipeline CI/CD GitHub Actions đã dùng OIDC không mật khẩu tĩnh theo `US-019`).
- Chủ dự án / Global Administrator kiểm tra tại **Microsoft Entra ID → Properties → Manage Security defaults** (bật **Security defaults** nếu dùng gói miễn phí) hoặc **Conditional Access** yêu cầu MFA cho toàn bộ thành viên có quyền trên subscription `rg-vsl-staging` / `vslstate2026`.
- Với tài khoản khách (External/Guest accounts) được mời vào tenant, yêu cầu chủ tài khoản bật xác thực hai lớp (Microsoft Authenticator / passkey / FIDO2) và kiểm tra trạng thái trong **Entra ID → Users → Per-user MFA / Sign-in logs** trước khi cấp quyền IAM.
- Không lưu mật khẩu, Client Secret hay mã khôi phục MFA trong repository hoặc chat.

### 7.3. Dịch vụ và cấu hình Azure bị cấm / được phép có điều kiện (`BR-016`)

Không tạo hoặc bật các dịch vụ/cấu hình trong nhóm **Bị cấm** nếu chưa có ngoại lệ bằng văn bản từ chủ dự án:

| Nhóm | Dịch vụ / cấu hình | Quy tắc áp dụng |
|---|---|---|
| **Bị cấm** | VM có GPU (`NC`/`NV`/`ND`), Azure Machine Learning compute cluster chạy liên tục | Tiêu tốn credit rất nhanh ngay cả khi chạy thời gian ngắn. |
| **Bị cấm** | AKS (Azure Kubernetes Service), App Service Plan Premium/Isolated, VM chạy 24/7 | Tính phí compute nền liên tục theo giờ. |
| **Bị cấm** | Azure SQL Database HA/vCore lớn, Cosmos DB provisioned throughput, Azure Cache for Redis chạy thường trực | Chi phí cố định hàng tháng vượt ngân sách demo. |
| **Bị cấm** | Application Gateway, Azure Front Door, Azure Load Balancer Standard trả phí theo giờ, NAT Gateway | Phát sinh phí cố định theo giờ và lưu lượng ngoài hạn mức demo. |
| **Bị cấm** | Container Apps đặt `minReplicas > 0` hoặc App Service Always On không được phê duyệt | Trái nguyên tắc scale-to-zero của `BR-016` *(staging `vsl-api` đã được chuyển về `minReplicas = 0` và xác nhận scale về `0` instance khi idle theo `US-020`; App Service `vsl-vietnam` giữ làm endpoint dự phòng hiện tại trong `web/config.js`)*. |
| **Có điều kiện** | Azure Container Apps (`WorkloadProfiles` Consumption, `cae-vsl-staging-std`), `1.0 vCPU`, `2.0 GiB RAM` | Đặt `minReplicas = 0` (trừ khi chủ dự án duyệt đo kiểm), giới hạn `maxReplicas <= 3`. |
| **Có điều kiện** | Azure Container Registry (`vslacr3795`, SKU `Basic`) | Bật dọn tag cũ (giữ tối đa 3 tag `vsl-api` mới nhất theo `infra/registry.tf` hoặc dọn thủ công nếu gói Students chặn ACR Task). |
| **Có điều kiện** | Log Analytics Workspace (`workspace-rgvslstaging8EBp`) & Storage Account (`vslstate2026`) | Giữ mức thu thập/retention mặc định tối thiểu, không bật diagnostic dump dư thừa. |
| **Miễn phí** | Cloudflare Pages (`https://sign-language-classification.pages.dev`) & GitHub Actions | Nằm trong hạn mức miễn phí hàng tháng. |

### 7.4. Quy trình xử lý khi nhận cảnh báo chi phí `$1` (20%) hoặc chạm `$5` (100%)

1. **Khi chạm `$1` (`20%`):** Người nhận thông báo báo ngay cho chủ dự án; không chờ đến `$5`. Mở **Azure Cost Management → Cost analysis** (nhóm theo *Service name* / *Meter*) và đối chiếu số dư trên `https://www.microsoftazuresponsorships.com`.
2. Tạm dừng triển khai/thay đổi hạ tầng mới. Kiểm tra các tài nguyên đang hoạt động trong `rg-vsl-staging` và toàn subscription: `minReplicas` / `maxReplicas` của `vsl-api`, trạng thái App Service `vsl-vietnam`, Environment cũ (`cae-vsl-staging`), dung lượng ACR `vslacr3795`, mức ingest Log Analytics và kiểm tra xem có tài nguyên ngoài danh sách cho phép hay không.
3. Không hạ `minReplicas`, scale về 0 hoặc xóa resource đang phục vụ khi chưa đánh giá tác động và có xác nhận của chủ dự án. Không xóa tài nguyên chứa state (`vslstate2026`).
4. **Khi chạm `$5` (`100%`) hoặc chi phí tăng bất thường:** Coi là sự cố (*incident*), ngừng mọi pipeline deploy, cô lập/tắt tài nguyên ngoài allow-list sau khi chủ dự án duyệt và ghi nhận nguyên nhân + hành động khắc phục vào nhật ký vận hành.

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
