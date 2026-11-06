# HƯỚNG DẪN CHẠY DỰ ÁN

Sign-Language-Classification-v1.0 — chạy trên Windows và Docker Linux.
Mọi lệnh dưới đây đã được **kiểm chứng và chạy thử thật 100%**.

---

## 0. Hiểu đúng trước khi bắt đầu

Dự án này là hệ thống nhận diện **ngôn ngữ ký hiệu tiếng Việt** (23 ký tự) qua ảnh và webcam sử dụng MediaPipe và mô hình CNN ResNet50.

**Model đã được huấn luyện sẵn** tại `train/vsl_cnn_pose_keras.h5` (137 MB, Git LFS). Bạn **không cần train lại** để chạy thử.

Dự án cung cấp 2 hình thức sử dụng chính:
1. **Dịch vụ Backend API qua Container Docker (Chuẩn hóa đám mây & Web hóa - Khuyến nghị):** Chạy FastAPI server đóng gói trong Docker, phục vụ các endpoint `/health`, `/version` và `/predict` cho website hoặc hệ thống khác.
2. **Nhận diện Realtime trực tiếp từ Webcam:** Dùng `run_realtime.cmd` (1-click native OpenCV) hoặc `run_realtime.ipynb` (Jupyter Notebook).

---

## 1. CÁCH CHẠY BACKEND API BẰNG DOCKER (KHUYẾN NGHỊ)

Dành cho việc đóng gói artifact bất biến, kiểm thử API hoặc chuẩn bị triển khai lên Google Cloud Run.

### Bước 1: Mở Docker Desktop
Đảm bảo phần mềm **Docker Desktop** trên máy tính đã được bật và đang ở trạng thái chạy (Engine Running).

### Bước 2: Build Docker Image
Mở **PowerShell** tại thư mục gốc dự án và chạy:

```powershell
docker build -t vsl-api .
```

> **Mẹo:** Để endpoint `/version` phản ánh đúng mã commit Git hiện tại (theo quy tắc `BR-009`):
> ```powershell
> docker build --build-arg GIT_SHA=$(git rev-parse HEAD) -t vsl-api .
> ```

### Bước 3: Khởi chạy Container
```powershell
docker run -d -p 8080:8080 --name vsl-service vsl-api
```

*(Lưu ý: Nếu cổng `8080` trên máy đang bận, bạn có thể đổi cổng ngoài máy host sang `8088:8080`: `docker run -d -p 8088:8080 --name vsl-service vsl-api`)*.

### Bước 4: Kiểm tra & Trải nghiệm API trên Trình duyệt
Sau khi chạy container khoảng 5–10 giây (server nạp xong mô hình):
* **Giao diện Swagger UI tương tác:** Truy cập **[http://localhost:8080/docs](http://localhost:8080/docs)**
  - `GET /health`: Kiểm tra trạng thái sẵn sàng của mô hình (`{"status": "ok", "model_loaded": true}`).
  - `GET /version`: Xem phiên bản mô hình, mã Git SHA và build time.
  - `POST /predict`: Tải ảnh chụp ký hiệu tay để nhận kết quả dự đoán chữ cái tiếng Việt.
* **Theo dõi log hoạt động của container:**
  ```powershell
  docker logs -f vsl-service
  ```
  *(Nhấn `Ctrl + C` để thoát màn hình xem log)*.

### Bước 5: Tắt và dọn dẹp Container khi dùng xong
```powershell
docker stop vsl-service
docker rm vsl-service
```

> **Triển khai lên Đám mây (Cloud Deployment):**
> Để đưa container này lên chạy 24/24 trên Microsoft Azure (miễn phí 100% bằng tài khoản sinh viên), xem hướng dẫn chi tiết tại [docs/infrastructure/HUONG-DAN-TRIEN-KHAI-AZURE.md](docs/infrastructure/HUONG-DAN-TRIEN-KHAI-AZURE.md).

---

## 2. CÁCH CHẠY BACKEND API TRỰC TIẾP QUA PYTHON (KHÔNG CẦN DOCKER)

Nếu bạn chưa cài Docker hoặc muốn chạy nhanh mã nguồn Python cục bộ:

```powershell
& "D:\program\python\python.exe" -m uvicorn src.vsl.service:app --port 8000
```
Truy cập giao diện Swagger UI tại: **[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

## 3. CÁCH CHẠY NHẬN DIỆN REALTIME QUA WEBCAM CỤC BỘ

### Cách 1: Chạy trực tiếp 1-click (Nhanh & Mượt nhất)

Mở terminal tại thư mục dự án và gõ:

```cmd
.\run_realtime.cmd
```

*(Hoặc gõ: `py -3.12 run_realtime.py`)*

- Cửa sổ camera OpenCV sẽ hiện lên ngay lập tức (30–60 FPS).
- Nhấn phím **`q`** tại cửa sổ camera để dừng.

---

### Cách 2: Chạy trực tiếp trong VS Code / Antigravity IDE (Interactive Notebook)

1. Mở file [run_realtime.ipynb](run_realtime.ipynb) trong IDE.
2. Nhìn lên **góc trên bên phải** của giao diện Notebook (nút chọn **Kernel**):
   - Chọn kernel: **Python 3.12 (VSL)** hoặc **Python 3.12.7** (`D:\program\python\python.exe`).
   - *(Lưu ý: Không chọn `.venv\Scripts\python.exe` vì launcher stub của Windows có thể gây lỗi nạp DLL)*.
3. Nhấn **Run All** (hoặc chạy từng cell). Cửa sổ camera sẽ bật lên. Nhấn **`q`** trên camera để dừng.

---

### Cách 3: Chạy qua giao diện Jupyter Notebook trên trình duyệt

```cmd
.\run_notebook.cmd
```

Trình duyệt tự động mở Jupyter:
1. Mở file `run_realtime.ipynb`.
2. Chọn menu **Cell → Run All**.
3. Cửa sổ camera sẽ bật lên. Nhấn **`q`** trên cửa sổ camera để dừng.

> **Lưu ý:** Luôn khởi động bằng `.\run_notebook.cmd` thay vì gọi `notebook` trần, vì script này đã cấu hình sẵn thư mục cache và kernel chuẩn tránh lỗi quyền ghi trên Windows.

---

## 4. Hướng dẫn khi đưa tay trước camera

1. **Bắt buộc đưa đủ cả 1 BÀN TAY và KHUÔN MẶT** vào trong khung hình camera.
2. Màn hình sẽ vẽ khung xương bàn tay màu xanh lá cây để bạn quan sát.
3. Nếu thiếu tay hoặc mặt, phía trên sẽ hiện dòng trạng thái cảnh báo màu cam:
   `Dang tim: Tay [OK/X] | Mat [OK/X]`
4. Khi camera bắt đủ cả tay và mặt (93 landmark), hệ thống sẽ lập tức hiển thị nhãn ký tự dự đoán màu xanh lá cây:
   `Letter: a (99.8%)`
5. Bảng chữ cái nhận diện gồm 23 ký tự tiếng Việt:
   ```
   a, b, c, d, đ, e, g, h, i, k, l, m, n, o, p, q, r, s, t, u, v, x, y
   ```
   *(Không có f, j, w, z)*.

---

## 5. Thu thập dữ liệu và Train lại (Chỉ khi cần)

- **Thu thập thêm mẫu mới:** Mở [process_images/capture_and_process_images.ipynb](process_images/capture_and_process_images.ipynb) → sửa tên ký tự cần chụp ở cell cuối `capture_for_letter('...')` → **Run All**.
- **Train lại mô hình ResNet50:** Mở [train/train_cnn_pose_keras.ipynb](train/train_cnn_pose_keras.ipynb) → **Run All** (khuyến nghị có GPU, train trên CPU sẽ mất nhiều giờ).

---

## 6. Xử lý lỗi thường gặp (Troubleshooting)

| Triệu chứng | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `docker run` báo `port is already allocated` | Cổng 8080 đang bị socket TIME_WAIT hoặc ứng dụng khác chiếm | Đổi sang cổng khác bằng cờ `-p 8088:8080` khi chạy container |
| `docker compose up` báo `no configuration file provided` | Dự án dùng trực tiếp `Dockerfile` theo chuẩn Cloud Run | Sử dụng lệnh `docker build` và `docker run` |
| `ImportError: DLL load failed while importing cv2` | Chạy trực tiếp bằng binary `.venv\Scripts\python.exe` bị lỗi Windows DLL launcher | Dùng `.\run_realtime.cmd` hoặc dùng Python gốc `D:\program\python\python.exe` |
| `PermissionError: C:\Users\...\.jupyter\migrated` | Jupyter mặc định ghi cache ngoài thư mục project bị Windows giới hạn quyền | Khởi động bằng `.\run_notebook.cmd` |
| `Không thể mở camera` / `Không đọc được frame` | Camera không ở index 0 hoặc đang bị app khác chiếm (Zoom/Teams/Camera) | Tắt các app dùng camera, hoặc đổi `cv2.VideoCapture(0)` thành `(1)` |
| Camera bật nhưng không hiện chữ dự đoán | Chưa đưa đủ cả 1 bàn tay và mặt vào khung hình | Nhìn dòng trạng thái `Dang tim: Tay [X] / Mat [X]`, đưa cả mặt và tay vào vùng sáng rõ |
| `No matching distribution found for tensorflow` | Máy đang chạy Python 3.13 hoặc 3.14 mặc định | Cài đặt Python 3.12 và dùng lệnh `py -3.12` |
