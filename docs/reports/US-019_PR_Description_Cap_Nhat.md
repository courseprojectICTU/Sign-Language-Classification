# [US-019] Azure Container Registry, IAM và GitHub OIDC

## 1. Mục đích

PR triển khai **US-019 – Pipeline xác thực với Azure mà không cần khóa tĩnh**
thuộc **EPC-05**, đáp ứng **BR-015 / AC-019-01 / AC-019-02**. Thay đổi adopt
ACR staging hiện có vào Terraform, cấu hình ACR cleanup, danh tính triển khai
GitHub OIDC cùng các role scope giới hạn, và cập nhật hướng dẫn CI/CD để không
dùng credential tĩnh.

**Phạm vi:** cấu hình và kiểm thử ở mức repository; staging resource mới chưa
được provision hoàn chỉnh. **Production chưa được cấu hình hoặc nghiệm thu.**
Workflow OIDC có thể chạy thủ công nhưng chưa có kết quả đăng nhập Azure thực tế.

## 2. Thay đổi trong Pull Request

So sánh local `feature/US-019` với `origin/develop`: **41 commit, 29 file thay
đổi**. Nhánh hiện gồm cả US-018 (phụ thuộc Terraform Azure Blob state) do US-018
chưa nằm trong `develop`; cần tính đến phạm vi gộp khi mở PR.

| Nhóm | File | Nội dung |
|---|---|---|
| Thiết kế/tài liệu | `docs/api/US-018.md`, `docs/api/US-019.md`, `AGENTS.md` | Hợp đồng US-018/019, phạm vi và trạng thái triển khai |
| Terraform Azure state | `infra/versions.tf`, `infra/provider.tf`, `infra/backend.tf`, `infra/variables.tf`, `infra/environments/*.tfvars` | AzureRM/AzureAD providers, Blob backend và cấu hình staging/production |
| Terraform bootstrap | `infra/bootstrap-azure/` | Tạo Storage Account và private Blob container làm remote state |
| ACR và identity | `infra/registry.tf`, `infra/identity.tf`, `infra/outputs.tf` | Khai báo ACR, cleanup task, deployment identity, FIC, RBAC và các identifier outputs |
| GitHub Actions | `.github/workflows/azure-oidc-smoke.yml` | Workflow `workflow_dispatch` kiểm tra đăng nhập Azure bằng OIDC |
| Hướng dẫn | `infra/README.md`, `infra/bootstrap-azure/README.md`, `docs/infrastructure/HO-SO-BAN-GIAO-HA-TANG.md`, `docs/planning/*.md` | Hướng dẫn Terraform và thay tài liệu CI credential tĩnh bằng OIDC |
| An toàn repo | `infra/.gitignore`, `infra/.terraform.lock.hcl`, `infra/bootstrap-azure/.terraform.lock.hcl` | Bỏ qua state/plan cục bộ và khóa phiên bản provider |
| Test | `tests/test_us018_terraform.py`, `tests/test_us019_azure_terraform.py`, `tests/test_us019_secret_policy.py` | Kiểm tra cấu hình, role scope và chính sách không dùng khóa tĩnh |

## 3. Cấu hình và bảo mật

- **Môi trường đã cấu hình:** Azure staging, Resource Group `rg-vsl-staging`,
  region `eastasia`.
- **ACR hiện có:** `vslacr3795` (SKU Basic), được import vào Terraform remote
  state để tránh tạo trùng; cấu hình có `prevent_destroy`.
- **Cleanup:** ACR Task dùng `acr purge` theo lịch hằng ngày, lọc repository
  `vsl-api` và giữ tối đa 3 tag đủ điều kiện sau mỗi lần chạy. Đây không phải
  giới hạn tức thời giữa các lần purge; hành vi cleanup cần được kiểm tra trước
  khi bật trên môi trường có dữ liệu quan trọng.
- **Danh tính GitHub:** Azure application / Service Principal và Federated
  Identity Credential dự kiến tin cậy subject của nhánh `develop`, issuer
  `https://token.actions.githubusercontent.com` và audience
  `api://AzureADTokenExchange`.
- **RBAC:** `AcrPush` chỉ ở scope ACR; `Container Apps Contributor` chỉ ở scope
  Container App `vsl-api`; managed identity cleanup chỉ nhận `AcrDelete` ở
  scope ACR. Không cấp `Owner` hoặc `Contributor` ở subscription/Resource Group.
- **GitHub Actions:** đọc Client ID, Tenant ID và Subscription ID từ GitHub
  Actions Variables; dùng `azure/login@v2` với `id-token: write`, không tham
  chiếu GitHub Secrets hay in access token.
- **ACR admin:** cấu hình Terraform hiện vẫn đặt `admin_enabled = true`; workflow
  OIDC không dùng thông tin admin này. Không thay đổi cấu hình pull image hiện
  có của Container App; việc vô hiệu hóa admin/runtime credential cần được xem
  xét riêng để tránh gián đoạn dịch vụ.
- Không commit Terraform state, plan, Azure token, client secret, service-account
  key JSON hoặc ACR credential.

### Trạng thái Azure staging và điều kiện chặn

ACR staging đã được import vào remote state. Theo trạng thái được ghi nhận trong
`AGENTS.md`, chưa có resource US-019 nào được tạo: Terraform apply bị chặn do
Entra trả 403 khi tạo App Registration và subscription chưa đăng ký
`Microsoft.ManagedIdentity`. Cần Azure admin cấp quyền Entra phù hợp và đăng ký
resource provider trước khi tiếp tục apply. Không chạy lại apply khi chưa xử lý
các điều kiện này và chưa có phê duyệt thao tác ghi tài nguyên/state.

## 4. Lệnh kiểm thử và minh chứng

Chạy tại thư mục gốc repository bằng Python môi trường dự án.

### 4.1. Kiểm thử liên quan US-018/US-019

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests/test_us019_azure_terraform.py tests/test_us019_secret_policy.py tests/test_us018_terraform.py -q
```

**Kết quả:** `12 passed in 0.74s`.

### 4.2. Kiểm thử toàn bộ dự án

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests -q
```

**Kết quả:** `85 passed, 8 warnings in 45.91s`. Các cảnh báo là deprecation
warning từ thư viện và warning cấu trúc input Keras; không có test thất bại.

### 4.3. Kiểm tra diff

```powershell
git --no-pager diff --check origin/develop...HEAD
```

**Kết quả:** PASS, không có lỗi whitespace được báo cáo.

### 4.4. Kiểm tra Azure thực tế

Chưa nghiệm thu được đăng nhập OIDC hay provision các resource US-019 trên
Azure staging do các điều kiện quyền/provider nêu tại mục 3. Không coi test cấu
hình tĩnh là bằng chứng cho một lần đăng nhập Azure thành công. Production chưa
được plan/apply.

## 5. Acceptance Criteria

| AC | Nội dung | Minh chứng hiện có | Trạng thái |
|---|---|---|---|
| `AC-019-01` | GitHub Actions xác thực Azure thành công không cần service-account key trong repository | Terraform/workflow được kiểm tra bằng test; chưa chạy workflow OIDC thật vì identity chưa provision | Chưa nghiệm thu staging |
| `AC-019-02` | Không có service-account key JSON trong repository/history; pipeline chỉ dùng Azure identity | `tests/test_us019_secret_policy.py` rà soát working tree/history và policy; test thuộc full suite PASS | Đã kiểm tra trong repository; quản trị GitHub Secrets hiện hữu cần chủ repository tự rà soát |

## 6. Checklist nghiệm thu

- [x] Khai báo ACR hiện có để adopt vào Terraform, không tạo registry trùng.
- [x] Thêm ACR cleanup task có filter giới hạn và giữ 3 tag đủ điều kiện.
- [x] Khai báo GitHub OIDC FIC cho subject `develop`.
- [x] Giới hạn các role assignment theo ACR và Container App đích.
- [x] Thêm workflow smoke `workflow_dispatch`, không dùng GitHub Secrets.
- [x] Bổ sung kiểm thử Terraform, role scopes và chính sách credential tĩnh.
- [x] Cập nhật các hướng dẫn CI/CD liên quan.
- [x] Kiểm thử US-018/019: **12/12 PASS**.
- [x] Toàn bộ kiểm thử: **85/85 PASS** (có 8 warnings từ dependency/Keras).
- [ ] Azure admin cấp quyền Entra và đăng ký `Microsoft.ManagedIdentity`.
- [ ] Chủ dự án duyệt thao tác apply; provision identity/role/task trên staging.
- [ ] Chạy workflow OIDC thật từ `develop` và lưu bằng chứng run thành công.
- [ ] Chủ repository rà soát/xóa GitHub Secrets tĩnh cũ nếu không còn dùng.
- [ ] Production: chưa cấu hình, chưa triển khai, chưa nghiệm thu.

## 7. Giới hạn phạm vi

US-019 không thay đổi HTTP API `/health`, `/predict`, `/version`; không triển khai
revision mới của Container App; không đổi cấu hình pull image runtime; không
tạo pipeline CD hoàn chỉnh; và không cấu hình hoặc triển khai production. Thay
đổi runtime pull authentication cần phối hợp riêng để tránh làm gián đoạn staging.

## 8. Git và đề nghị review

- **Base:** `develop` (`origin/develop` tại thời điểm kiểm tra).
- **Compare:** `feature/US-019`.
- **Commit hiện tại:** `732e59c` — `docs(us-019): record staging apply blocker`.
- **Phạm vi diff local:** 41 commit, 29 file; bao gồm US-018 và US-019.
- **Tài liệu chính:** `docs/api/US-018.md`, `docs/api/US-019.md`,
  `infra/README.md`, `docs/infrastructure/HO-SO-BAN-GIAO-HA-TANG.md`.

Đề nghị reviewer xem riêng phạm vi US-018/US-019 khi so sánh với `develop`,
kiểm tra ACR import và lifecycle, cleanup filter, các role scope, OIDC subject,
và nội dung không dùng credential tĩnh. Có thể review cấu hình và mã nguồn ngay;
chỉ nên xác nhận nghiệm thu/merge sau khi chủ dự án duyệt hợp đồng và các bước
Azure staging bắt buộc được hoàn tất hoặc được chấp nhận rõ là điều kiện theo dõi.
