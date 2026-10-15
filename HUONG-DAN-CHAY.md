# HƯỚNG DẪN CHẠY DỰ ÁN

Sign-Language-Classification-v1.0 — chạy trên Windows.
Mọi lệnh dưới đây đã được **kiểm chứng và chạy thử thật 100%**.

---

## 0. Hiểu đúng trước khi bắt đầu

Dự án này là hệ thống nhận diện **ngôn ngữ ký hiệu tiếng Việt** (23 ký tự) qua webcam sử dụng MediaPipe và mô hình ResNet50.

**Model đã được huấn luyện sẵn** tại `train/vsl_cnn_pose_keras.h5` (130.7 MB). Bạn **không cần train lại** để chạy thử.

Dự án cung cấp 2 hình thức chạy nhận diện:
1. **Chạy trực tiếp 1-click (Khuyến nghị - Nhanh và mượt nhất):** Dùng `run_realtime.cmd` hoặc `run_realtime.py`.
2. **Chạy qua Jupyter Notebook:** Dùng `run_realtime.ipynb` (qua Jupyter Web hoặc VS Code).

---

## 1. Kiểm tra Python — bước quan trọng nhất

Mở **PowerShell** tại thư mục project và chạy:

```powershell
py -0p
```

Bạn cần thấy một dòng **3.12** (hoặc 3.9–3.12).

> ⚠️ **Nếu dòng có dấu `*` là Python 3.13 hoặc 3.14:**
> Python 3.13/3.14 **không cài được TensorFlow** (báo `No matching distribution found for tensorflow`).
> Vì vậy hãy đảm bảo máy đã cài Python 3.12: [Tải Python 3.12.7](https://www.python.org/downloads/release/python-3127/).

---

## 2. Chuẩn bị môi trường (Chỉ làm lần đầu nếu máy chưa có .venv)

*(Nếu trong thư mục dự án đã có sẵn thư mục `.venv`, bạn có thể bỏ qua bước này và chạy ngay sang Mục 3).*

Mở PowerShell tại thư mục gốc dự án:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 3. CÁCH CHẠY NHẬN DIỆN REALTIME (Chọn 1 trong 3 cách)

### Cách 1: Chạy trực tiếp 1-click (Khuyến nghị — Nhanh & Mượt nhất)

Mở terminal tại thư mục dự án và gõ:

```cmd
.\run_realtime.cmd
```

*(Hoặc gõ: `py -3.12 run_realtime.py`)*

- Cửa sổ camera OpenCV sẽ hiện lên ngay lập tức (30–60 FPS).
- Nhấn phím **`q`** tại cửa sổ camera để dừng.

---

### Cách 2: Chạy trực tiếp trong VS Code / Antigravity IDE (Interactive Notebook)

1. Mở file [run_realtime.ipynb](file:///d:/file/project/Sign-Language-Classification-v1.0/run_realtime.ipynb) trong IDE.
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

> ⚠️ **Lưu ý:** Luôn khởi động bằng `.\run_notebook.cmd` thay vì gọi `notebook` trần, vì script này đã cấu hình sẵn thư mục cache và kernel chuẩn tránh lỗi quyền ghi trên Windows.

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

- **Thu thập thêm mẫu mới:** Mở [process_images/capture_and_process_images.ipynb](file:///d:/file/project/Sign-Language-Classification-v1.0/process_images/capture_and_process_images.ipynb) → sửa tên ký tự cần chụp ở cell cuối `capture_for_letter('...')` → **Run All**.
- **Train lại mô hình ResNet50:** Mở [train/train_cnn_pose_keras.ipynb](file:///d:/file/project/Sign-Language-Classification-v1.0/train/train_cnn_pose_keras.ipynb) → **Run All** (khuyến nghị có GPU, train trên CPU sẽ mất nhiều giờ).

---

## 6. Xử lý lỗi thường gặp (Troubleshooting)

| Triệu chứng | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `ImportError: DLL load failed while importing cv2` | Chạy trực tiếp bằng binary `.venv\Scripts\python.exe` bị lỗi Windows DLL launcher | Dùng `.\run_realtime.cmd` hoặc trong IDE chọn Kernel trỏ vào `Python 3.12 (VSL)` |
| `PermissionError: C:\Users\...\.jupyter\migrated` | Jupyter mặc định ghi cache ngoài thư mục project bị Windows giới hạn quyền | Khởi động bằng `.\run_notebook.cmd` |
| `Không thể mở camera` / `Không đọc được frame` | Camera không ở index 0 hoặc đang bị app khác chiếm (Zoom/Teams/Camera) | Tắt các app dùng camera, hoặc đổi `cv2.VideoCapture(0)` thành `(1)` |
| Camera bật nhưng không hiện chữ dự đoán | Chưa đưa đủ cả 1 bàn tay và mặt vào khung hình | Nhìn dòng trạng thái `Dang tim: Tay [X] / Mat [X]`, đưa cả mặt và tay vào vùng sáng rõ |
| `No matching distribution found for tensorflow` | Máy đang chạy Python 3.13 hoặc 3.14 mặc định | Cài đặt Python 3.12 và dùng lệnh `py -3.12` |
