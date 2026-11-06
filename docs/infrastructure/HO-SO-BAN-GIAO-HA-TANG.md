# Hồ Sơ Bàn Giao Kỹ Thuật Hạ Tầng Môi Trường Staging

> **Dự án:** Sign-Language-Classification-v1.0 (Nhận diện Bảng chữ cái Ngôn ngữ Ký hiệu tiếng Việt)  
> **Trạng thái môi trường:** Sẵn sàng hoạt động (Hoạt động 24/24 trên Microsoft Azure)  
> **Cập nhật lần cuối:** 2026-11-06  

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
| Môi trường Container (Env) | `cae-vsl-staging` | Azure Container Apps Managed Environment |
| Không gian nhật ký (Log Workspace) | `workspace-rgvslstaging8lF4` | Log Analytics Workspace thu thập telemetry và log |
| Tên ứng dụng Backend | `vsl-api` | Dịch vụ FastAPI phục vụ suy luận |
| Cấu hình tài nguyên | 1.0 vCPU, 2.0 GiB RAM, Cổng 8080 | Cấu hình hoạt động liên tục (`minReplicas = 1`) |

---

## 3. Hợp Đồng Kết Nối Dịch Vụ

### 3.1. Địa chỉ dịch vụ công khai
- Base URL chính thức:  
  `https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io`
- Tên miền Web App dự phòng:  
  `https://vsl-vietnam.azurewebsites.net`
- Giao diện tài liệu Swagger UI:  
  `https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io/docs`

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
   - Cấu trúc dữ liệu:
     ```json
     {"model_version":"v1.0","git_sha":"unknown","build_time":"2026-11-05T17:09:06Z"}
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

## 4. Cấu Hình Secrets Tự Động Hóa CI/CD

Để pipeline GitHub Actions tự động đóng gói và cập nhật bản dựng mới lên Azure Container Apps:

### 4.1. Lệnh tạo Service Principal trên Azure
Tạo tài khoản tự động hóa có quyền truy cập phạm vi nhóm tài nguyên:

```powershell
az ad sp create-for-rbac `
  --name "sp-vsl-github-actions" `
  --role contributor `
  --scopes /subscriptions/373b1f03-330f-4302-a9e9-aa1fe793bf2e/resourceGroups/rg-vsl-staging `
  --json-auth
```

### 4.2. Danh sách Secrets cấu hình trên GitHub Actions
Cấu hình các biến sau vào mục Settings -> Secrets and variables -> Actions của kho lưu trữ GitHub:

| Tên Secret | Ý nghĩa | Giá trị mẫu |
|---|---|---|
| `AZURE_CREDENTIALS` | Toàn bộ chuỗi JSON trả về từ lệnh tạo Service Principal | `{"clientId": "...", "clientSecret": "...", ...}` |
| `REGISTRY_SERVER` | Địa chỉ máy chủ kho lưu trữ ACR | `vslacr3795.azurecr.io` |
| `REGISTRY_USERNAME` | Tên người dùng kho ACR | `vslacr3795` |
| `REGISTRY_PASSWORD` | Mật khẩu truy cập kho ACR | Lấy từ lệnh: `az acr credential show --name vslacr3795` |
| `AZURE_RESOURCE_GROUP` | Tên nhóm tài nguyên | `rg-vsl-staging` |
| `AZURE_APP_NAME` | Tên ứng dụng Container App | `vsl-api` |

---

## 5. Ma Trận Hỗ Trợ Theo User Story

| Mã US | Yêu cầu kỹ thuật | Thành phần hạ tầng cung cấp tương ứng |
|---|---|---|
| US-013 | Đo 5 lần thời gian khởi động nguội thực tế | Sử dụng script `scripts/benchmark_cold_start.py` gọi tới endpoint `https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io/health`. |
| US-017 | Smoke test tự động sau triển khai | Thực hiện HTTP request kiểm tra endpoint `GET /health` với điều kiện `model_loaded == true`. |
| US-024 | Triển khai Frontend lên Cloudflare Pages | Cấu hình biến môi trường gọi API: `VITE_API_URL=https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io`. |
| US-026 | Pipeline CI kiểm thử và build image | Chạy trên runner của GitHub Actions sử dụng Dockerfile chuẩn Linux. |
| US-029 | CD tự động triển khai revision mới | Sử dụng GitHub Action `azure/container-apps-deploy-action@v1` kết hợp bộ Secrets tại Mục 4. |
| US-034 | Cảnh báo Cloud Logging lỗi 5xx | Truy vấn log qua `workspace-rgvslstaging8lF4` hoặc cấu hình Alert rule trên Azure Monitor. |

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
