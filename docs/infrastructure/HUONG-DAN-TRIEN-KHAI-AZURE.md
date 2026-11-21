# Hướng Dẫn Triển Khai Dịch Vụ Lên Microsoft Azure Container Apps

Tài liệu hướng dẫn quy trình đóng gói và triển khai dịch vụ nhận diện ngôn ngữ ký hiệu (`vsl-api`) lên nền tảng Microsoft Azure Container Apps.

> **Trạng thái vận hành:** Đây là hướng dẫn triển khai thủ công, không phải workflow CI/CD.
> Các resource, URL, quota, revision mode và cấu hình replica trong tài liệu chưa được
> xác minh trực tiếp trong phiên cập nhật US-035. Kiểm tra lại Azure trước khi chạy lệnh;
> không giả định staging hoặc production đang khỏe. Không commit ACR password, service
> principal secret hay token; ưu tiên danh tính được quản lý và quyền tối thiểu.
> Dùng [runbook](../RUNBOOK.md) để smoke test, xử lý lỗi và rollback an toàn.

---

## 1. Kiến Trúc Triển Khai

```
Môi trường phát triển                          Hạ tầng Microsoft Azure (Hong Kong - East Asia)
+--------------------+                       +---------------------------------------+
| Docker Desktop     |                       | Azure Container Registry (ACR)        |
| Image: vsl-api     | ==(docker push)===>   | Kho lưu trữ Docker Image nội bộ       |
+--------------------+                       +---------------------------------------+
                                                                 ||
                                                                 || (Kéo image)
                                                                 \/
                                             +---------------------------------------+
                                             | Azure Container Apps (ACA)            |
                                             | - Hoạt động liên tục trên nền tảng    |
                                             | - Cấu hình: 1.0 vCPU, 2.0 GiB RAM     |
                                             | - Cổng phục vụ nội bộ: 8080 (FastAPI) |
                                             | - Cấp phát chứng chỉ HTTPS tự động    |
                                             +---------------------------------------+
                                                                 ||
                                                                 \/
                                             +---------------------------------------+
                                             | Endpoint công khai                    |
                                             | https://vsl-api.<unique>.eastasia.azurecontainerapps.io |
                                             +---------------------------------------+
```

### Đặc tính kỹ thuật:
- **Tài nguyên:** 1.0 vCPU và 2.0 GiB RAM đáp ứng yêu cầu nạp mô hình ResNet50 (~137MB) và runtime TensorFlow vào bộ nhớ.
- **Tính sẵn sàng:** Cấu hình `--min-replicas 1` duy trì dịch vụ hoạt động liên tục 24/24, không phát sinh thời gian khởi động nguội khi có request.
- **Độ trễ mạng:** Máy chủ đặt tại khu vực Đông Á (`eastasia` - Hong Kong) đảm bảo thời gian phản hồi mạng về Việt Nam khoảng 25ms - 35ms.

---

## 2. Điều Kiện Tiên Quyết

1. Tài khoản Azure for Students đã kích hoạt (hạn mức 100 USD credit khả dụng).
2. Docker Desktop đang chạy và đã build sẵn image `vsl-api:latest`.
   *(Lệnh build kiểm tra: `docker build -t vsl-api .` tại thư mục gốc dự án)*.
3. Azure CLI (`az`) đã cài đặt trên hệ thống:
   ```powershell
   winget install Microsoft.AzureCLI --source winget --accept-package-agreements --accept-source-agreements
   ```

---

## 3. Quy Trình Triển Khai

Thực hiện lần lượt các bước sau trong PowerShell:

### Bước 1: Xác thực tài khoản
```powershell
az login
```
Kiểm tra subscription mặc định:
```powershell
az account show --output table
```

---

### Bước 2: Khởi tạo Nhóm tài nguyên (Resource Group)
Tạo nhóm tài nguyên tập trung tại khu vực `eastasia`:

```powershell
$RESOURCE_GROUP = "rg-vsl-staging"
$LOCATION = "eastasia"

az group create --name $RESOURCE_GROUP --location $LOCATION
```

---

### Bước 3: Đăng ký dịch vụ và Tạo Kho lưu trữ Container (ACR)

Tài khoản mới cần đăng ký resource provider `Microsoft.ContainerRegistry`:
```powershell
az provider register --namespace Microsoft.ContainerRegistry
```

Tạo kho ACR và đẩy image:
```powershell
# 1. Sinh tên kho ACR duy nhất
$ACR_NAME = "vslacr" + (Get-Random -Minimum 1000 -Maximum 9999)
Write-Host "Ten kho ACR: $ACR_NAME"

# 2. Tạo kho ACR với gói Basic
az acr create `
  --resource-group $RESOURCE_GROUP `
  --name $ACR_NAME `
  --sku Basic `
  --admin-enabled true `
  --location $LOCATION

# 3. Đăng nhập Docker vào kho ACR
az acr login --name $ACR_NAME

# 4. Gắn tag image
docker tag vsl-api:latest "$ACR_NAME.azurecr.io/vsl-api:latest"

# 5. Đẩy image lên kho ACR
docker push "$ACR_NAME.azurecr.io/vsl-api:latest"
```

---

### Bước 4: Đăng ký dịch vụ Container Apps và Tạo Môi trường thực thi

Đăng ký các resource provider cần thiết:
```powershell
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

# Tạo môi trường thực thi (Managed Environment)
az containerapp env create `
  --name cae-vsl-staging `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION
```

---

### Bước 5: Triển khai ứng dụng VSL-API

Khởi tạo ứng dụng Container App kết nối với kho lưu trữ ACR:

```powershell
# 1. Lấy mật khẩu xác thực kho ACR
$ACR_PASSWORD = (az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# 2. Khởi tạo dịch vụ Container App
az containerapp create `
  --name vsl-api `
  --resource-group $RESOURCE_GROUP `
  --environment cae-vsl-staging `
  --image "$ACR_NAME.azurecr.io/vsl-api:latest" `
  --registry-server "$ACR_NAME.azurecr.io" `
  --registry-username $ACR_NAME `
  --registry-password $ACR_PASSWORD `
  --target-port 8080 `
  --ingress external `
  --cpu 1.0 `
  --memory 2.0Gi `
  --min-replicas 1 `
  --max-replicas 2
```

---

## 4. Kiểm Tra Và Nghiệm Thu

### 4.1. Lấy FQDN dịch vụ
```powershell
az containerapp show `
  --name vsl-api `
  --resource-group $RESOURCE_GROUP `
  --query properties.configuration.ingress.fqdn `
  --output tsv
```

### 4.2. Kiểm tra sức khỏe dịch vụ (`/health`)
```powershell
curl https://<FQDN_CUA_DICH_VU>/health
```
Phản hồi chuẩn:
```json
{"status":"ok","model_loaded":true,"model_version":"v1.0"}
```

### 4.3. Kiểm tra thông tin phiên bản (`/version`)
```powershell
curl https://<FQDN_CUA_DICH_VU>/version
```
Phản hồi chuẩn:
```json
{
  "model_version": "v1.0",
  "git_sha": "unknown",
  "build_time": "2026-11-05T17:09:06Z"
}
```

### 4.4. Truy cập giao diện tài liệu Swagger UI
Truy cập qua trình duyệt:  
`https://<FQDN_CUA_DICH_VU>/docs`

Tham khảo cấu hình tên miền cố định ngắn gọn `vsl-vietnam.azurewebsites.net` tại tài liệu: [docs/infrastructure/HUONG-DAN-CAU-HINH-TEN-MIEN-AZURE.md](HUONG-DAN-CAU-HINH-TEN-MIEN-AZURE.md).

---

## 5. Quản Lý Và Vận Hành

### 5.1. Xem log thời gian thực
```powershell
az containerapp logs show `
  --name vsl-api `
  --resource-group $RESOURCE_GROUP `
  --follow
```

### 5.2. Khởi động lại dịch vụ
```powershell
az containerapp revision restart `
  --name vsl-api `
  --resource-group $RESOURCE_GROUP
```

### 5.3. Cập nhật bản dựng Image mới
```powershell
docker build -t vsl-api .
docker push "$ACR_NAME.azurecr.io/vsl-api:latest"
az containerapp update `
  --name vsl-api `
  --resource-group $RESOURCE_GROUP `
  --image "$ACR_NAME.azurecr.io/vsl-api:latest"
```

### 5.4. Kiểm tra chi phí và số dư tài trợ

1. **Kiểm tra tiêu thụ tài nguyên qua Azure CLI:**
   ```powershell
   az consumption usage list --top 10 --query "[].{DichVu:consumedService, SanPham:product, ChiPhi:pretaxCost}" -o table
   ```

2. **Kiểm tra số dư qua giao diện quản trị:**
   - Cổng tài trợ sinh viên: `https://www.microsoftazuresponsorships.com` (mục Balance).
   - Cổng Azure Portal: `https://portal.azure.com` -> Cost Management + Billing -> Cost Analysis.

---

## 6. Xử Lý Sự Cố Thường Gặp

| Sự cố | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `RequestDisallowedByAzure` / `sys.regionrestriction` | Subscription giới hạn khu vực triển khai tài nguyên | Sử dụng `$LOCATION = "eastasia"` (Hong Kong) thay vì `southeastasia` |
| `failed to connect to the docker API at npipe` | Docker Desktop chưa khởi động hoặc engine chưa sẵn sàng | Mở Docker Desktop và đợi trạng thái hiển thị Engine running |
| `The registry name is already in use` | Tên kho ACR đã tồn tại trên phạm vi toàn cầu | Đổi giá trị biến `$ACR_NAME` sang chuỗi định danh khác |
| `unauthorized: authentication required` | Docker client chưa xác thực với kho ACR | Chạy lệnh `az acr login --name $ACR_NAME` trước khi `docker push` |
| `Namespace 'Microsoft.App' not registered` | Subscription chưa kích hoạt extension Container Apps | Chạy lệnh `az provider register --namespace Microsoft.App` |
| Container dừng bất thường (`OOMKilled`) | Thiếu bộ nhớ RAM khi nạp mô hình TensorFlow | Chỉ định tham số `--memory 2.0Gi` khi tạo hoặc cập nhật container |

---

## 7. Xóa Bỏ Tài Nguyên (Cleanup)

Khi cần xóa toàn bộ môi trường để giải phóng tài nguyên:

```powershell
az group delete --name $RESOURCE_GROUP --yes --no-wait
az group list -o table
```
