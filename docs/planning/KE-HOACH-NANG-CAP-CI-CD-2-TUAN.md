# KẾ HOẠCH NÂNG CẤP: WEB HÓA + CI/CD (2 TUẦN)

> Tài liệu kỹ thuật: Hệ thống nhận diện ngôn ngữ ký hiệu tiếng Việt - Kiến trúc Backend Azure Container Apps và Frontend Cloudflare Pages.
> Toàn bộ dữ kiện hiện trạng đã được kiểm chứng trực tiếp từ repository và hạ tầng đã triển khai thực tế.

---

## 0. LỊCH SỬ QUYẾT ĐỊNH VÀ ĐIỀU CHỈNH HẠ TẦNG

Ngăn xếp công nghệ chính thức: Azure Container Apps (Backend API) và Cloudflare Pages (Frontend Web tĩnh), vận hành trên gói tài trợ Azure for Students hạn mức 100 USD credit (chi phí 0 VNĐ).

Các quyết định kỹ thuật đã chốt:

| Số | Quyết định kỹ thuật | Trạng thái |
|---|---|---|
| 1 | MVP: Tải hoặc chụp 1 ảnh để nhận kết quả phân loại ký tự (không dùng streaming liên tục) | Đã chốt |
| 2 | Ngân sách: 0 VNĐ (sử dụng gói Azure for Students 100 USD credit và Cloudflare Pages miễn phí) | Đã chốt |
| 3 | Backend: Microsoft Azure Container Apps (thay thế kế hoạch ban đầu là Google Cloud Run) | Đã chốt |
| 4 | Frontend: Cloudflare Pages (xem docs/architecture/ADR-001-frontend-hosting.md) | Đã chốt |
| 5 | Triển khai Frontend tự động bằng GitHub Actions kết hợp wrangler | Đã chốt |

Lý do điều chỉnh từ Google Cloud sang Microsoft Azure:
1. Google Cloud yêu cầu đặt cọc xác minh thanh toán 800.000 VNĐ tại Việt Nam, gây rào cản chi phí cho nhóm phát triển.
2. Microsoft Azure cung cấp gói Azure for Students miễn phí 100 USD credit hàng năm, không yêu cầu thẻ tín dụng ngân hàng.
3. Azure Container Apps cung cấp đầy đủ các tính năng tương đương: Serverless Container, hỗ trợ scale linh hoạt, quản lý phiên bản (Revision), phân tách lưu lượng (Traffic Splitting) và tích hợp sẵn HTTPS.
4. Chạy MediaPipe Python trực tiếp tại máy chủ backend giúp loại bỏ hoàn toàn rủi ro sai lệch toạ độ landmark giữa JavaScript trình duyệt và Python máy chủ.
5. Hợp đồng API đơn giản: Trình duyệt chỉ cần gửi tệp tin ảnh, toàn bộ quy trình trích xuất landmark 93 cột, tạo heatmap và suy luận mô hình được xử lý đồng nhất trên máy chủ.

---

## 1. TÓM TẮT ĐIỀU HÀNH

Mã nguồn ban đầu của dự án bao gồm 3 Jupyter Notebook, chưa có dịch vụ backend độc lập, chưa có bộ kiểm thử tự động, chưa có Dockerfile và chưa có luồng CI/CD.

| Yêu cầu ban đầu | Hiện trạng thực tế | Hướng xử lý |
|---|---|---|
| Triển khai backend lên website | Chưa có dịch vụ backend dạng module | Xây dựng dịch vụ FastAPI độc lập tại package src/vsl |
| Thiết lập CI/CD lên đám mây | Chưa có artifact và container chuẩn hóa | Đóng gói Dockerfile Linux và tự động hóa với GitHub Actions |
| Tập trung quy trình CI/CD | Cần artifact ổn định trước khi tự động hóa | Tuần 1 hoàn thiện artifact và kiểm thử; Tuần 2 tự động hóa CI/CD |

Logic nhận diện gốc mở trực tiếp webcam trên máy cục bộ qua cv2.VideoCapture(0) và hiển thị trên màn hình máy tính. Do đó, hệ thống bắt buộc phải tách biệt thành:
- Frontend (Giao diện người dùng trên trình duyệt): Chụp hoặc chọn ảnh từ camera thiết bị người dùng và gửi qua HTTP POST.
- Backend (Dịch vụ API trên Azure Container Apps): Nhận ảnh, chạy MediaPipe trích xuất 93 landmark, sinh heatmap 224x224x3, nạp vào mô hình ResNet50 và trả về kết quả dự đoán.

---

## 2. RÀNG BUỘC CHI PHÍ VÀ QUẢN TRỊ TRÊN MICROSOFT AZURE

Dự án áp dụng chính sách chi phí 0 VNĐ dựa trên gói tài khoản Azure for Students (100 USD credit).

### 2.1. Danh mục dịch vụ và phân bổ tài nguyên

| Dịch vụ đám mây | Cấu hình và hạn mức | Vai trò trong hệ thống |
|---|---|---|
| Azure Container Apps | 1.0 vCPU, 2.0 GiB RAM, HTTP Ingress cổng 8080 | Máy chủ chạy dịch vụ nhận diện FastAPI |
| Azure Container Registry | Basic SKU, lưu trữ image Docker | Lưu trữ image container (vslacr3795.azurecr.io) |
| Log Analytics Workspace | Hạn mức dữ liệu thu thập mặc định | Thu thập toàn bộ log và giám sát container |
| Azure Cost Management | Quản lý hạn mức chi tiêu 100 USD credit | Theo dõi số dư ngân sách tài trợ |
| Cloudflare Pages | Miễn phí, 500 build mỗi tháng | Máy chủ lưu trữ và phân phối giao diện web tĩnh |
| GitHub Actions | 2.000 phút chạy miễn phí mỗi tháng | Tự động hóa kiểm thử, đóng gói và triển khai |

### 2.2. Các thành phần dịch vụ tránh phát sinh chi phí

| Dịch vụ | Rủi ro chi phí | Hướng xử lý |
|---|---|---|
| Application Gateway / Azure Front Door | Chi phí cố định hàng tháng cao | Không sử dụng. Azure Container Apps đã tích hợp sẵn Ingress HTTPS |
| Azure Firewall / NAT Gateway | Chi phí cố định cao | Không sử dụng. Container giao tiếp trực tiếp qua Ingress công khai |
| Azure SQL / Cosmos DB | Không nằm trong phạm vi MVP | Không sử dụng cơ sở dữ liệu có phí |
| Container kích thước quá lớn (> 2 vCPU, 4 GiB) | Làm tiêu hao nhanh hạn mức credit | Ghim cấu hình chuẩn: 1.0 vCPU và 2.0 GiB RAM |

### 2.3. Quy định triển khai trên Azure for Students

Theo chính sách của gói Azure for Students, một số khu vực địa lý bị giới hạn. Dự án đã chuẩn hóa triển khai tại vùng eastasia (Hong Kong):
- Nhóm tài nguyên (Resource Group): rg-vsl-staging (vùng eastasia).
- Kho lưu trữ Container (ACR): vslacr3795 (vùng eastasia).
- Môi trường Container Apps (ACA Environment): Managed Environment tại eastasia.
- Dịch vụ đang hoạt động: vsl-api.

---

## 3. HIỆN TRẠNG KỸ THUẬT ĐÃ KIỂM CHỨNG

### 3.1. Cấu trúc và kích thước

| Hạng mục | Giá trị thực tế |
|---|---|
| Mô hình nhận diện (train/vsl_cnn_pose_keras.h5) | 137.042.364 bytes (khoảng 130.7 MB), quản lý bởi Git LFS |
| Dữ liệu landmark thô | 1.609 file CSV phân bổ trong 23 thư mục chữ cái (mỗi chữ cái 70 mẫu, riêng chữ đ có 69 mẫu) |
| Hợp đồng landmark | 93 cột toạ độ chuẩn hoá (63 toạ độ bàn tay xen kẽ + 30 toạ độ khuôn mặt) |
| Module mã nguồn độc lập | Đã tách thành công package src/vsl/ (config, labels, heatmap, landmarks, service) |
| Dịch vụ API | Đã hoàn thiện FastAPI với 3 endpoint: GET /health, GET /version, POST /predict |
| Bộ kiểm thử tự động | Đầy đủ unit tests và integration tests trong thư mục tests/ |
| Đóng gói container | Đã có Dockerfile Linux độc lập và .dockerignore chuẩn hoá |

### 3.2. Môi trường thực thi chuẩn

- Phiên bản Python chuẩn: Python 3.12 (khả dụng tại máy phát triển và đồng nhất trong container).
- Thư viện phụ thuộc: tensorflow==2.19.1, keras==3.15.1, mediapipe==0.10.21, numpy==1.26.4, opencv-python-headless==4.11.0.86, fastapi, uvicorn.
- Container Linux: python:3.12-slim, cài đặt đầy đủ libgl1 và libglib2.0-0.

---

## 4. VẤN ĐỀ VÀ KẾ HOẠCH XỬ LÝ KỸ THUẬT

### 4.1. Các vấn đề cốt lõi (Đã xử lý trong Tuần 1)

1. Tách mã nguồn suy luận khỏi Jupyter Notebook: Đã hoàn thành, tập trung toàn bộ logic vào package src/vsl.
2. Xóa bỏ hoàn toàn đường dẫn tuyệt đối hard-code Windows: Đã xử lý triệt để qua module src/vsl/config.py và biến môi trường VSL_MODEL_PATH, VSL_DATA_DIR.
3. Đồng nhất định nghĩa nhãn và bảng chữ cái: Đã cố định tại src/vsl/labels.py với 23 ký tự bất biến (tuple).
4. Đồng nhất hàm tạo heatmap: Đã tập trung tại src/vsl/heatmap.py làm nguồn chân lý duy nhất.
5. Cung cấp phản hồi rõ ràng khi thiếu dữ liệu nhận diện: Endpoint POST /predict trả về status: ok, no_hand, no_face thay vì giữ im lặng.
6. Đóng gói container Linux: Dockerfile chuẩn hoá với opencv-python-headless, khởi động dịch vụ trên cổng 8080.

### 4.2. Các vấn đề phục vụ CI/CD tự động (Tuần 2)

1. Tạo quy trình CI tự động: Tự động chạy ruff, kiểm tra định dạng và thực thi toàn bộ test suite trên mỗi Pull Request.
2. Tạo quy trình CD tự động: Khi Pull Request được hợp nhất vào develop hoặc main, tự động đóng gói image Docker, đẩy lên Azure Container Registry và cập nhật Azure Container Apps.
3. Quản lý bí mật xác thực: Sử dụng Service Principal hoặc GitHub OIDC tích hợp vào GitHub Secrets, không hard-code thông tin nhạy cảm.
4. Cơ chế chuyển đổi phiên bản và rollback: Khai thác tính năng Revision của Azure Container Apps để kiểm tra phiên bản mới trước khi chuyển toàn bộ lưu lượng truy cập.
5. Tự động triển khai giao diện web: Thiết lập workflow triển khai giao diện tĩnh lên Cloudflare Pages.

---

## 5. KIẾN TRÚC MỤC TIÊU HỆ THỐNG

### 5.1. Sơ đồ kiến trúc tổng thể

```
┌────────────────────────────────────────────────────────┐
│               GIAO DIỆN NGƯỜI DÙNG                     │
│  - Trang web tĩnh lưu trữ trên Cloudflare Pages        │
│  - Chụp ảnh từ camera hoặc tải ảnh từ máy              │
│  - Hiển thị ký tự dự đoán và độ tin cậy                │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ HTTPS POST /predict (Multipart Image)
                            ▼
┌────────────────────────────────────────────────────────┐
│            MICROSOFT AZURE CONTAINER APPS              │
│  - Dịch vụ vsl-api (FastAPI, 1.0 vCPU, 2.0 GiB RAM)   │
│                                                        │
│  Quy trình xử lý nội bộ:                               │
│  1. Nhận tệp tin ảnh từ client                         │
│  2. Trích xuất landmark bằng MediaPipe Python          │
│  3. Kiểm tra điều kiện đủ 93 landmark (tay và mặt)    │
│  4. Tạo ảnh nhiệt 224x224x3 qua create_heatmap()       │
│  5. Tiền xử lý chuẩn ResNet50 (trừ mean BGR)           │
│  6. Suy luận mô hình CNN ResNet50                      │
│  7. Trả về kết quả JSON {status, letter, confidence}   │
└───────────────────────────┬────────────────────────────┘
                            │
         ┌──────────────────┴──────────────────┐
         ▼                                     ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│ Azure Container Registry│         │  Log Analytics Workspace│
│  (vslacr3795.azurecr.io)│         │  (Thu thập log và lỗi)  │
└─────────────────────────┘         └─────────────────────────┘
```

### 5.2. Hợp đồng giao tiếp API

Endpoint chính POST /predict:
- Header: Content-Type: multipart/form-data
- Body: file (dữ liệu ảnh định dạng JPEG hoặc PNG)

Các trường hợp phản hồi:
1. Nhận diện thành công (HTTP 200):
   ```json
   {
     "status": "ok",
     "letter": "a",
     "confidence": 0.998,
     "top_k": [
       {"letter": "a", "confidence": 0.998},
       {"letter": "s", "confidence": 0.001}
     ],
     "model_version": "v1.0.0"
   }
   ```
2. Không tìm thấy bàn tay (HTTP 200):
   ```json
   {
     "status": "no_hand",
     "letter": null,
     "confidence": null,
     "top_k": [],
     "model_version": "v1.0.0"
   }
   ```
3. Không tìm thấy khuôn mặt (HTTP 200):
   ```json
   {
     "status": "no_face",
     "letter": null,
     "confidence": null,
     "top_k": [],
     "model_version": "v1.0.0"
   }
   ```
4. Lỗi định dạng đầu vào hoặc kích thước ảnh không hợp lệ: Trả về HTTP 400 hoặc HTTP 415.

---

## 6. PHẠM VI DỰ ÁN TRONG 2 TUẦN

### 6.1. Hạng mục nằm trong phạm vi (Cam kết thực hiện)

1. Tách toàn bộ logic suy luận thành package Python src/vsl chuẩn hóa.
2. Xây dựng dịch vụ FastAPI hoàn chỉnh gồm các endpoint /health, /version, /predict.
3. Pipeline xử lý ảnh server-side đảm bảo tính nhất quán với mô hình đã huấn luyện.
4. Xây dựng giao diện web tối giản cho phép chụp ảnh và hiển thị kết quả phân loại.
5. Đóng gói container Linux qua Dockerfile tối ưu kích thước và thời gian build.
6. Xây dựng bộ kiểm thử tự động toàn diện: Unit tests, hợp đồng landmark, đối chiếu kết quả chuẩn và kiểm tra container.
7. Thiết lập luồng CI tự động kiểm tra mã nguồn trên mỗi Pull Request.
8. Thiết lập luồng CD tự động triển khai backend lên Azure Container Apps qua Azure Container Registry.
9. Thiết lập luồng triển khai giao diện web lên Cloudflare Pages.
10. Thiết lập cơ chế kiểm tra trạng thái sức khỏe (Health Check) và giám sát log qua Log Analytics.

### 6.2. Hạng mục ngoài phạm vi 2 tuần

1. Nhận diện luồng video streaming liên tục thời gian thực qua WebRTC hoặc WebSocket.
2. Hệ thống xác thực người dùng, phân quyền truy cập và quản lý tài khoản.
3. Huấn luyện lại toàn bộ mô hình trên tập dữ liệu mở rộng.
4. Mở rộng nhận diện câu, từ hoặc cử chỉ động phức tạp.
5. Triển khai kiến trúc đa vùng (Multi-region) hoặc hạ tầng Kubernetes tự quản trị.

---

## 7. CÁC MẢNG CÔNG VIỆC KỸ THUẬT

Hệ thống được chia thành 4 mảng kỹ thuật độc lập và phối hợp chặt chẽ:

| Mảng kỹ thuật | Trọng tâm công việc | Sản phẩm bàn giao chính |
|---|---|---|
| Backend & Machine Learning | Đóng gói logic suy luận, xây dựng FastAPI service, xử lý pipeline trích xuất landmark và sinh heatmap | Package src/vsl, bộ endpoint /health, /predict, /version |
| Giao diện Web (Frontend) | Xây dựng giao diện web tương tác camera, gửi request nhận diện và hiển thị kết quả | Thư mục web/, cấu hình Cloudflare Pages |
| Hạ tầng Đám mây (Cloud Infrastructure) | Quản trị tài nguyên Azure Container Apps, Azure Container Registry, cấu hình bảo mật và tối ưu chi phí | Hạ tầng Azure hoạt động tại vùng eastasia |
| Tự động hóa CI/CD & Đảm bảo chất lượng | Thiết lập GitHub Actions cho CI/CD, viết test tự động, kiểm tra hợp đồng dữ liệu và kịch bản rollback | Thư mục .github/workflows/, thư mục tests/ |

---

## 8. LỊCH TRÌNH THỰC HIỆN 10 NGÀY

### TUẦN 1: Chuẩn Hóa Mã Nguồn, Đóng Gói Container Và Triển Khai Staging

| Ngày | Backend & Machine Learning | Giao diện Web (Frontend) | Hạ tầng Đám mây | Tự động hóa CI/CD & Đảm bảo chất lượng | Cột mốc hoàn thành |
|---|---|---|---|---|---|
| D1 | Chốt hợp đồng API, tạo cấu trúc package src/vsl | Thiết kế khung giao diện web | Khởi tạo tài nguyên đám mây Azure | Thiết lập quy ước nhánh git và branch protection | Hợp đồng API được phê duyệt |
| D2 | Tách heatmap, nhãn và cấu hình đường dẫn tương đối | Hoàn thiện giao diện tải ảnh và chụp ảnh | Thiết lập Azure Container Registry | Viết unit tests cho heatmap, nhãn và config | Toàn bộ module lõi dùng chung hoàn thành |
| D3 | Hoàn thiện FastAPI /predict xử lý ảnh bằng MediaPipe | Tích hợp gọi API thử nghiệm nội bộ | Cấu hình tài nguyên Azure Container Apps | Viết test kiểm tra hợp đồng landmark 93 cột | Pipeline nhận diện hoạt động cục bộ |
| D4 | Tối ưu Dockerfile Linux và kiểm tra khởi động cổng 8080 | Hoàn thiện xử lý trạng thái no_hand và no_face | Cấu hình kết nối kéo image từ ACR sang ACA | Viết test kiểm tra Dockerfile và cấu trúc container | Container chạy thành công trên máy cục bộ |
| D5 | Đo lường thời gian khởi động mô hình | Tích hợp ping kiểm tra trạng thái khởi động | Triển khai container lên Azure Staging | Viết kịch bản kiểm tra smoke test tự động | Dịch vụ hoạt động trên Azure Staging |

### TUẦN 2: Tự Động Hóa CI/CD, Giám Sát Và Bàn Giao

| Ngày | Backend & Machine Learning | Giao diện Web (Frontend) | Hạ tầng Đám mây | Tự động hóa CI/CD & Đảm bảo chất lượng | Cột mốc hoàn thành |
|---|---|---|---|---|---|
| D6 | Tối ưu hóa hiệu năng nạp mô hình | Cấu hình dự án trên Cloudflare Pages | Phân quyền Service Principal cho CI/CD | Xây dựng workflow CI tự động chạy test trên PR | Quy trình CI kiểm tra mã nguồn tự động |
| D7 | Hoàn thiện tài liệu hợp đồng API | Cấu hình CORS và tên miền giao diện | Tích hợp log vào Log Analytics Workspace | Xây dựng workflow CD tự động đẩy image và deploy | Quy trình CD tự động triển khai Azure hoàn thành |
| D8 | Hỗ trợ đối chiếu kết quả kiểm thử | Kiểm thử toàn diện giao diện trên trình duyệt | Kiểm tra hạn mức chi tiêu ngân sách Azure | Thiết lập bước phê duyệt thủ công cho môi trường chính thức | Hệ thống hoàn chỉnh triển khai có kiểm soát |
| D9 | Hoàn thiện tài liệu vận hành kỹ thuật | Hoàn tất nghiệm thu giao diện người dùng | Rà soát cấu hình an toàn hệ thống | Diễn tập kịch bản rollback qua Revision Azure | Quy trình rollback được kiểm chứng |
| D10 | Tổng kết thông số kỹ thuật | Chuẩn bị nội dung trình diễn | Báo cáo chi phí thực tế (0 VNĐ) | Hoàn thiện bộ hồ sơ bàn giao kỹ thuật | Dự án nghiệm thu thành công |

---

## 9. THIẾT KẾ CI/CD CHI TIẾT TRÊN GITHUB ACTIONS VÀ AZURE

### 9.1. Luồng CI (Tự động kích hoạt trên mỗi Pull Request)

Mọi Pull Request tạo vào nhánh develop hoặc main đều phải vượt qua các bước kiểm tra:
1. Lint và kiểm tra chuẩn định dạng mã nguồn (ruff, black).
2. Chạy toàn bộ bộ kiểm thử tự động (pytest tests -v).
3. Kiểm tra tính toàn vẹn của hợp đồng dữ liệu 93 cột toạ độ.
4. Thử nghiệm build image Docker để phát hiện sớm lỗi đóng gói.
5. Chặn merge nếu có bất kỳ bước kiểm tra nào thất bại.

### 9.2. Luồng CD (Tự động kích hoạt khi merge nhánh)

Khi code được hợp nhất vào nhánh chính:
1. Chạy lại toàn bộ bộ kiểm thử để đảm bảo tính nhất quán.
2. Build image Docker với thẻ định danh bằng Git commit SHA (không chỉ dùng thẻ latest).
3. Đăng nhập và đẩy image lên Azure Container Registry (vslacr3795.azurecr.io).
4. Cập nhật Azure Container Apps để tạo bản Revision mới.
5. Chạy smoke test kiểm tra endpoint /health của Revision mới.
6. Chuyển lưu lượng truy cập sang Revision mới khi kiểm tra thành công.

### 9.3. Quản lý bí mật xác thực trên GitHub Actions

Để GitHub Actions có quyền đẩy image và cập nhật Container Apps, cấu hình các thông tin bí mật trong GitHub Secrets:
- AZURE_CREDENTIALS: Thông tin xác thực của Service Principal (gồm clientId, clientSecret, subscriptionId, tenantId).
- ACR_USERNAME và ACR_PASSWORD: Thông tin truy cập Azure Container Registry.

---

## 10. TIÊU CHÍ NGHIỆM THU HỆ THỐNG (Definition of Done)

1. Hệ thống có URL công khai đang hoạt động trên Azure Container Apps và phản hồi kết quả nhận diện chính xác.
2. Mã nguồn không còn bất kỳ đường dẫn tuyệt đối nào, hoạt động hoàn toàn dựa trên cấu hình tương đối và biến môi trường.
3. Các thành phần logic cốt lõi (heatmap, labels, config) chỉ tồn tại một bản duy nhất trong thư mục src/vsl.
4. Endpoint POST /predict phản hồi đúng trạng thái khi thiếu tay (no_hand) hoặc thiếu mặt (no_face).
5. Endpoint GET /health phản ánh đúng trạng thái mô hình và nạp thành công mô hình ResNet50.
6. Endpoint GET /version trả về đầy đủ Git SHA, phiên bản mô hình và thời gian build.
7. Toàn bộ bộ kiểm thử tự động đạt 100% tỷ lệ vượt qua (PASSED).
8. Quy trình CI tự động kích hoạt trên Pull Request và chặn hợp nhất khi có lỗi.
9. Quy trình CD tự động triển khai thành công lên Azure Container Apps.
10. Chi phí vận hành thực tế nằm trọn vẹn trong hạn mức miễn phí 100 USD của Azure for Students (0 VNĐ phát sinh ngoài).
11. Đầy đủ hồ sơ kỹ thuật, hướng dẫn triển khai và hướng dẫn cấu hình tên miền trong thư mục docs/.

---

## 11. CÁC BƯỚC TRIỂN KHAI TIẾP THEO

1. Hoàn tất việc cập nhật các tài liệu kỹ thuật liên quan sang Microsoft Azure.
2. Hợp nhất nhánh feature/US-013 vào develop.
3. Bắt đầu triển khai các User Story tiếp theo liên quan đến cấu hình luồng CI/CD tự động (US-017, US-026) và giao diện web.
