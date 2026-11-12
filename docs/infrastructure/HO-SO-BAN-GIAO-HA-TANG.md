# Hồ Sơ Bàn Giao Kỹ Thuật Hạ Tầng Môi Trường Staging

> **Dự án:** Sign-Language-Classification-v1.0 (Nhận diện Bảng chữ cái Ngôn ngữ Ký hiệu tiếng Việt)  
>
> **Trạng thái môi trường:** Sẵn sàng hoạt động (Standard ACA + App Service trên Microsoft Azure)
>
> **Cập nhật lần cuối:** 2026-11-11

---

## 1. Tổng Quan

Tài liệu này tổng hợp toàn bộ thông số kỹ thuật, cấu hình mạng, hợp đồng API và các biến môi trường/secrets của môi trường Staging Cloud trên Microsoft Azure. Tài liệu phục vụ việc tích hợp và thực thi độc lập các User Story tiếp theo trong backlog (từ US-013 đến US-034).

---

## 2. Thông Số Kỹ Thuật Hạ Tầng Staging

| Thành phần | Giá trị cấu hình | Ghi chú |
|---|---|---|
| Nền tảng Cloud | Microsoft Azure (Gói Azure for Students) | Hạn mức tài trợ 100 USD credit |
| Khu vực máy chủ (Region) | `eastasia` (Hong Kong) | Độ trễ mạng về Việt Nam khoảng 25ms - 35ms |
| Nhóm tài nguyên (Resource Group) | `rg-vsl-staging` | Chứa toàn bộ tài nguyên staging |
| Subscription ID | `373b1f03-330f-4302-a9e9-aa1fe793bf2e` | Định danh gói đăng ký Azure |
| Tenant ID | `07bbe8bf-0c35-4e0d-bc8a-da3413925cc0` | Định danh tổ chức Azure Active Directory |
| Kho lưu trữ Image (ACR) | `vslacr3795.azurecr.io` | Azure Container Registry (gói Basic) |
| Môi trường Container (Env) | `cae-vsl-staging-std` | Azure Container Apps Standard (`WorkloadProfiles`, Consumption) |
| Không gian nhật ký (Log Workspace) | `workspace-rgvslstaging8EBp` | Log Analytics Workspace (`9171bce8-f5c8-4fdb-842b-af7c35a59234`) |
| Tên ứng dụng Backend | `vsl-api` | Dịch vụ FastAPI phục vụ suy luận (`Multiple` revision mode, `id-vsl-api-pull` `AcrPull`) |
| Cấu hình tài nguyên | 1.0 vCPU, 2.0 GiB RAM, Cổng 8080 | `minReplicas = 0`, `maxReplicas = 3`, `terminationGracePeriodSeconds = 60`, HTTP probes `/health:8080`, `VSL_MODEL_PATH=/app/train/vsl_cnn_pose_keras.h5`, `VSL_ALLOWED_ORIGINS=https://sign-language-classification.pages.dev` (quản lý qua Terraform `infra/container_app.tf`, đã nghiệm thu `US-020`) |

---

## 3. Hợp Đồng Kết Nối Dịch Vụ

### 3.1. Địa chỉ dịch vụ công khai
- Base URL chính thức (Container Apps Standard): `https://vsl-api.happyforest-6510ce4b.eastasia.azurecontainerapps.io`
- Tên miền Web App dự phòng / endpoint hiện tại của `web/config.js`: `https://vsl-vietnam.azurewebsites.net`
- Giao diện tài liệu Swagger UI: `https://vsl-api.happyforest-6510ce4b.eastasia.azurecontainerapps.io/docs`

### 3.2. Đặc tả các Endpoints
1. **Kiểm tra sức khỏe hệ thống (`GET /health`):**
   - Phục vụ: Kiểm tra độ sẵn sàng mô hình (Smoke Test, Cold Start Benchmark).
   - Mã phản hồi: `HTTP 200 OK`
   - Cấu trúc dữ liệu:
     ```json
     {"status":"ok","model_loaded":true,"model_version":"v1.0"}
     ```

2. **Kiểm tra thông tin phiên bản (`GET /version`):**
   - Phục vụ: Truy vết mã commit Git SHA và thời gian build image.
   - Mã phản hồi: `HTTP 200 OK`
   - Cấu trúc dữ liệu tham chiếu (tag `9a1c3aa847e19ef4a85d6bec9d36afc3d5c5e76f`):
     ```json
     {"model_version":"v1.0","git_sha":"9a1c3aa847e19ef4a85d6bec9d36afc3d5c5e76f","build_time":"2026-11-10T15:22:13Z"}
     ```

3. **Nhận diện ký hiệu tay từ ảnh webcam (`POST /predict`):**
   - Phục vụ: Tiếp nhận ảnh webcam từ giao diện người dùng.
   - Phương thức: `POST`
   - Content-Type: `multipart/form-data`
   - Trường dữ liệu: `file` (ảnh JPG hoặc PNG).
   - Tham số query: `flip=true` (mặc định lật ảnh theo gương).
   - Mã phản hồi: `HTTP 200 OK`
   - Cấu trúc dữ liệu:
     ```json
     {
       "letter": "a",
       "confidence": 0.9982,
       "status": "ok",
       "landmarks_detected": 93
     }
     ```

---

## 4. Cấu Hình GitHub Actions bằng Azure OIDC

CI/CD phải đăng nhập Azure bằng GitHub OpenID Connect (OIDC), không tạo hoặc
lưu `clientSecret`, service-account key JSON hay ACR username/password.

Terraform US-019 tạo Azure application, Service Principal, Federated Identity
Credential và role assignments tối thiểu. FIC tin cậy:

| Thuộc tính | Giá trị |
|---|---|
| Issuer | `https://token.actions.githubusercontent.com` |
| Audience | `api://AzureADTokenExchange` |
| Subject | `repo:courseprojectICTU@343123217/Sign-Language-Classification@1421059989:ref:refs/heads/develop` |

Sau khi Terraform provision xong và chủ dự án duyệt thao tác áp dụng, lấy ba
identifier không nhạy cảm bằng `terraform output -raw github_oidc_client_id`,
`terraform output -raw github_oidc_tenant_id` và
`terraform output -raw github_oidc_subscription_id`. Lưu chúng dưới dạng GitHub
Actions Variables `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` và
`AZURE_SUBSCRIPTION_ID`, không phải GitHub Secrets. Chạy workflow
`.github/workflows/azure-oidc-smoke.yml` thủ công từ nhánh `develop` để xác minh
đăng nhập.

Sau khi OIDC được xác minh, chủ dự án cần xóa thủ công các GitHub Secrets cũ
`AZURE_CREDENTIALS`, `REGISTRY_USERNAME` và `REGISTRY_PASSWORD` nếu còn tồn tại
và không còn được workflow khác sử dụng. Không gửi giá trị của chúng trong chat
hoặc commit vào repository.

---

## 5. Ma Trận Hỗ Trợ Theo User Story

| Mã US | Yêu cầu kỹ thuật | Thành phần hạ tầng cung cấp tương ứng |
|---|---|---|
| US-013 | Đo 5 lần thời gian khởi động nguội thực tế | Sử dụng script `scripts/benchmark_cold_start.py` gọi tới endpoint `https://vsl-api.happyforest-6510ce4b.eastasia.azurecontainerapps.io/health`. |
| US-017 | Smoke test tự động sau triển khai | Thực hiện HTTP request kiểm tra endpoint `GET /health` với điều kiện `model_loaded == true`. |
| US-024 | Triển khai Frontend lên Cloudflare Pages | Cấu hình API qua `web/config.js` (`https://vsl-vietnam.azurewebsites.net`) hoặc biến môi trường tới `https://vsl-api.happyforest-6510ce4b.eastasia.azurecontainerapps.io`. |
| US-026 | Pipeline CI kiểm thử và build image | Chạy trên runner của GitHub Actions sử dụng Dockerfile chuẩn Linux. |
| US-029 | CD tự động triển khai revision mới | Sử dụng GitHub Action `azure/container-apps-deploy-action@v1` với Azure OIDC (Mục 4); push image bằng quyền `AcrPush`, không dùng ACR admin credentials. |
| US-034 | Cảnh báo Cloud Logging lỗi 5xx | Truy vấn log qua `workspace-rgvslstaging8EBp` hoặc cấu hình Alert rule trên Azure Monitor. |

---

## 6. Lệnh Vận Hành Và Kiểm Tra Hệ Thống

- Xem log ứng dụng theo thời gian thực:
  ```powershell
  az containerapp logs show --name vsl-api --resource-group rg-vsl-staging --follow
  ```

- Khởi động lại revision của dịch vụ:
  ```powershell
  az containerapp revision restart --name vsl-api --resource-group rg-vsl-staging
  ```

- Kiểm tra mức tiêu thụ tài nguyên và số dư tài trợ:
  Truy cập cổng quản lý: `https://www.microsoftazuresponsorships.com` (mục Balance).
