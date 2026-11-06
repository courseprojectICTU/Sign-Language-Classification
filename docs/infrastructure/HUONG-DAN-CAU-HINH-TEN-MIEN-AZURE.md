# Hướng Dẫn Cấu Hình Tên Miền vsl-vietnam.azurewebsites.net Trên Azure

Tài liệu hướng dẫn cấu hình triển khai dịch vụ nhận diện ngôn ngữ ký hiệu (`vsl-api`) sử dụng tên miền cố định thông qua Azure App Service:  
`https://vsl-vietnam.azurewebsites.net`

---

## 1. Mục Đích & So Sánh Định Dạng Tên Miền

Việc cấu hình tên miền `vsl-vietnam.azurewebsites.net` cung cấp địa chỉ truy cập ngắn gọn, cố định và hỗ trợ sẵn chứng chỉ bảo mật HTTPS do Microsoft quản lý.

| Tiêu chí | Đường dẫn Container Apps mặc định | Đường dẫn Azure App Service |
|---|---|---|
| Định dạng FQDN | `vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io` | `vsl-vietnam.azurewebsites.net` |
| Tính cố định | Phụ thuộc vào chuỗi định danh ngẫu nhiên của môi trường | Cố định theo tên dịch vụ đăng ký |
| Chứng chỉ HTTPS | Tự động cấp phát | Tự động cấp phát qua chứng chỉ mặc định của Azure |
| Cấu hình tài nguyên | 1.0 vCPU, 2.0 GiB RAM | 1.0 vCPU, 1.75 GiB RAM (Gói B1 Basic) |
| Chi phí | Nằm trong hạn mức Azure for Students | Nằm trong hạn mức Azure for Students |

---

## 2. Kiến Trúc Luồng Dữ Liệu

Dịch vụ tái sử dụng image đã đóng gói sẵn trong kho lưu trữ `vslacr3795`:

```
Kho lưu trữ ACR                            Dịch vụ Azure Web App for Containers
vslacr3795.azurecr.io                      vsl-vietnam.azurewebsites.net
Image: vsl-api:latest  --(Kéo image)-->    - Hoạt động 24/24 trên nền tảng Linux
                                           - Cổng phục vụ nội bộ: 8080
                                           - Trung tâm dữ liệu: eastasia (Hong Kong)
```

---

## 3. Các Bước Cấu Hình Bằng Azure CLI

Thực hiện lần lượt các lệnh sau trong PowerShell:

### Bước 1: Khởi tạo Gói máy chủ Linux (App Service Plan)
Tạo gói máy chủ Linux tại khu vực `eastasia` tuân thủ chính sách tài nguyên của tài khoản Azure for Students:

```powershell
$RESOURCE_GROUP = "rg-vsl-staging"
$LOCATION = "eastasia"
$PLAN_NAME = "asp-vsl"

az appservice plan create `
  --name $PLAN_NAME `
  --resource-group $RESOURCE_GROUP `
  --is-linux `
  --sku B1 `
  --location $LOCATION
```

---

### Bước 2: Khởi tạo Web App với Tên miền vsl-vietnam
Lấy thông tin xác thực từ kho ACR và khởi tạo dịch vụ Web App:

```powershell
$APP_NAME = "vsl-vietnam"
$ACR_NAME = "vslacr3795"

# Lấy mật khẩu xác thực kho ACR
$ACR_PASSWORD = (az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Khởi tạo Web App từ container image
az webapp create `
  --name $APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --plan $PLAN_NAME `
  --deployment-container-image-name "$ACR_NAME.azurecr.io/vsl-api:latest" `
  --docker-registry-server-user $ACR_NAME `
  --docker-registry-server-password $ACR_PASSWORD
```

---

### Bước 3: Cấu hình Cổng kết nối Container (Port 8080)
Cấu hình biến môi trường chuyển tiếp lưu lượng từ cổng 443 HTTPS vào cổng 8080 của container:

```powershell
az webapp config appsettings set `
  --resource-group $RESOURCE_GROUP `
  --name $APP_NAME `
  --settings WEBSITES_PORT=8080
```

---

### Bước 4: Kích hoạt Chế độ Duy trì Hoạt động (Always On)
Kích hoạt chế độ Always On để ngăn chặn dịch vụ chuyển sang trạng thái ngủ đông khi không có request:

```powershell
az webapp config set `
  --resource-group $RESOURCE_GROUP `
  --name $APP_NAME `
  --always-on true
```

---

## 4. Kiểm Tra Và Nghiệm Thu

Sau khi hoàn tất cấu hình, kiểm tra các điểm cuối dịch vụ:

### 4.1. Giao diện tài liệu Swagger UI
Truy cập qua trình duyệt:  
`https://vsl-vietnam.azurewebsites.net/docs`

### 4.2. Kiểm tra trạng thái mô hình (`/health`)
```powershell
curl https://vsl-vietnam.azurewebsites.net/health
```
Phản hồi chuẩn:
```json
{"status":"ok","model_loaded":true,"model_version":"v1.0"}
```

### 4.3. Kiểm tra thông tin phiên bản (`/version`)
```powershell
curl https://vsl-vietnam.azurewebsites.net/version
```

---

## 5. Vận Hành Và Quản Trị Hệ Thống

### 5.1. Xem log thời gian thực
```powershell
az webapp log tail --name vsl-vietnam --resource-group rg-vsl-staging
```

### 5.2. Khởi động lại dịch vụ
```powershell
az webapp restart --name vsl-vietnam --resource-group rg-vsl-staging
```

### 5.3. Danh mục Endpoints phục vụ tích hợp
- Base URL: `https://vsl-vietnam.azurewebsites.net`
- Tài liệu API: `https://vsl-vietnam.azurewebsites.net/docs`
- Kiểm tra sức khỏe: `https://vsl-vietnam.azurewebsites.net/health`
- Dự đoán suy luận: `https://vsl-vietnam.azurewebsites.net/predict`
