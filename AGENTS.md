# AGENTS.md — Sign-Language-Classification-v1.0

Bộ nhớ dự án cho agent. Đọc file này trước khi sửa code.
**Cập nhật lần cuối: 2026-10-28** — trạng thái Git, kiểm thử và US-016 được đối chiếu
trực tiếp trong phiên này. Nếu bạn phát hiện file này lệch với thực tế,
hãy sửa nó ngay (đọc mục 10.0 trước — file có tiếng Việt, `edit` dễ fail).

**Quy trình làm việc bắt buộc** (đồng bộ `develop` → tạo nhánh → đọc US → viết test
trước → làm từng task → nghiệm thu): xem [docs/WORKFLOW.md](docs/WORKFLOW.md).
Áp dụng cho **mọi** User Story, không có ngoại lệ.

---

## 1. Dự án là gì

Phân loại **bảng chữ cái ngôn ngữ ký hiệu tiếng Việt** (23 ký tự) từ webcam.
Pipeline: ảnh webcam → MediaPipe trích landmark bàn tay + mặt → sinh **heatmap
224x224x3** → CNN **ResNet50** → softmax 23 lớp.

**Repo:** `https://github.com/courseprojectICTU/Sign-Language-Classification.git`
(remote `origin`, đã xác minh từ `.git/config`). URL cũ `tpd05/Sign-Language-Classification-v1.0`
**không còn dùng** — đừng trích lại nó.

**Hai nguồn mô tả — chỉ một nguồn là thật:**

| Nguồn | Trạng thái |
|---|---|
| `README.md` | mô tả dự án gốc, có **2 số liệu sai** (xem mục 5, ý 10) |
| `docs/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md` + `docs/ADR-001-*` | kế hoạch web hóa + CI/CD, **một phần đã lỗi thời** (xem mục 13) |
| **chính source + git** | nguồn chân lý; AGENTS.md này bám theo đó |

Mã nguồn hiện tại = **package `src/vsl/` (gồm hợp đồng landmark) + dịch vụ FastAPI `src/vsl/service.py` (GET /health + POST /predict) + 3 notebook + 1 script Python native**.
Bộ kiểm thử tự động `tests/` có **41/41 tests PASSED** trong lần chạy ngày 2026-10-28 sau khi triển khai US-016. Chưa có Dockerfile, CI workflow
hay hạ tầng Cloud Run.

---

## 2. Git — trạng thái thực tế

| Mục | Giá trị (đối chiếu 2026-10-28) |
|---|---|
| Remote `origin` | `https://github.com/courseprojectICTU/Sign-Language-Classification.git` (fetch = push) |
| `origin/HEAD` | → `origin/develop` |
| Nhánh local | `develop`, `feature/US-007`, `feature/US-015`, `feature/US-016` (đang checkout) |
| `develop` | `520e215` Merge pull request #11 from `feature/US-015` (đồng bộ `origin/develop`) |
| `feature/US-015` | `ac6e72d` — US-015 đã merge vào `develop` qua PR #11 |
| `feature/US-016` | `5a98a85` — hoàn tất TSK-026/TSK-027 và cập nhật trạng thái dự án; dựa trên `develop` tại `520e215` |
| LFS | `git-lfs/3.7.0`; `.gitattributes` chỉ có `*.h5 filter=lfs` |
| `train/vsl_cnn_pose_keras.h5` | **file thật 137.042.364 bytes** (LFS đã smudge, không phải pointer) |
| Trạng thái working tree | **Clean** sau khi cập nhật bộ nhớ dự án; nhánh `feature/US-016` chưa push |

### 2.1. BẪY: `git status` và `git diff` trên MSYS

Trên máy Windows này, một số lệnh git diện rộng qua `sh.exe` có thể gặp bẫy:
```
sh.exe: *** fatal error - NtCreateDirectoryObject(\BaseNamedObjects\msys-2.0S5-...): 0xC0000022
```
Đây là **sandbox chặn MSYS tạo named object**.
- **Lệnh chạy an toàn:** `git remote -v`, `git log`, `git branch -vv`, `git ls-files`, `git rev-parse`, `git hash-object`, `git --no-pager diff --numstat HEAD`.
- **Lệnh commit:** Thêm cờ `-c core.hooksPath=.git/no-hooks` để tránh spawn hooks không cần thiết:
  ```powershell
  git -c core.hooksPath=.git/no-hooks commit -m "..."
  ```
- **Bẫy mạng TLS (schannel):** Luôn thêm `-c http.sslBackend=openssl` khi fetch/push:
  ```powershell
  git -c http.sslBackend=openssl push origin feature/US-002
  ```

---

## 3. Cấu trúc thư mục

```
data/anphabet/<ký tự>/*.csv                     landmark thô, 1 file = 1 mẫu (1609 CSV)
process_images/capture_and_process_images.ipynb   thu thập dữ liệu (dùng sys.path import src.vsl)
train/train_cnn_pose_keras.ipynb                  huấn luyện (ResNet50, import src.vsl)
train/vsl_cnn_pose_keras.h5                       model đã train (137.042.364 bytes, Git LFS)
train/training_plot_keras.png                     biểu đồ loss/accuracy
run_realtime.ipynb                                inference webcam qua Jupyter
run_realtime.py                                   inference webcam native OpenCV (import src.vsl)
run_realtime.cmd                                  launcher 1-click cho run_realtime.py
run_notebook.cmd                                  launcher Jupyter an toàn (xem mục 12.1)
requirements.txt                                  deps đã pin, THUẦN ASCII (mục 10.1)
requirements-dev.txt                              pytest (dev-only)
HUONG-DAN-CHAY.md                                 hướng dẫn chạy cho người dùng
AGENTS.md                                         file này (bộ nhớ dự án)
.github/PULL_REQUEST_TEMPLATE.md                  biểu mẫu PR chuẩn tiếng Việt có dấu
docs/ADR-001-frontend-hosting.md                  ADR chọn Cloudflare Pages
docs/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md            kế hoạch 2 tuần / 4 người
docs/product-backlog-cicd-2-tuan.xlsx             backlog (10 epic, 39 US, 63 AC, 75 task, 26 BR)
docs/WORKFLOW.md                                  quy trình bắt buộc cho mọi US
docs/QUY-TRINH-REVIEW-PULL-REQUEST.md             hướng dẫn 5 bước thẩm định PR cho Reviewer
docs/QUY-TRINH-REVIEW-PULL-REQUEST.docx           bản xuất bản Word (.docx) của quy trình Reviewer
docs/api/README.md                                quy ước + 9 phase + checklist API docs
docs/api/_TEMPLATE.md                             bộ khung 17 mục cho mỗi api doc
docs/api/US-001.md                                hợp đồng API của US-001 (create_heatmap - PASS)
docs/api/US-002.md                                hợp đồng API của US-002 (labels - PASS)
docs/api/US-003.md                                hợp đồng API của US-003 (config - PASS)
docs/api/US-004.md                                hợp đồng API của US-004 (requirements - PASS)
docs/api/US-005.md                                hợp đồng API của US-005 (health - PASS)
docs/api/US-015.md                                hợp đồng US-015 (landmark contract - PASS)
docs/api/US-016.md                                tài liệu hồi cứu US-016 (N/A public API; test contract)
src/vsl/__init__.py                               re-export heatmap, labels, config
src/vsl/config.py                                 cấu hình đường dẫn tập trung (BR-004)
src/vsl/heatmap.py                                create_heatmap — BẢN DUY NHẤT (BR-002)
src/vsl/labels.py                                 VIETNAMESE_ALPHABET + NUM_CLASSES — BẢN DUY NHẤT (BR-003)
src/vsl/landmarks.py                              hợp đồng 93 cột + FACE_KEYPOINTS (BR-001)
src/vsl/service.py                                FastAPI service + GET /health + POST /predict
tests/test_config.py                              test US-003 (AC-003-01, AC-003-02, BR-004: 4 test)
tests/test_health.py                              test US-005 (AC-005-01, AC-005-02, BR-011: 3 test)
tests/test_heatmap.py                             test US-001 (AC-001-01, AC-001-02 + biên: 9 test)
tests/test_labels.py                              test US-002 (AC-002-01, AC-002-02, BR-003: 4 test)
tests/test_landmark_contract.py                   kiểm thử hợp đồng 93 cột (US-015)
tests/test_service_notebook_reference.py          đối chiếu service với kết quả notebook (US-016)
tests/fixtures/notebook_prediction_reference.json kết quả tham chiếu frozen 23 mẫu (US-016)
tests/_generate_service_reference.py              tạo fixture tham chiếu từ luồng notebook (US-016)
tests/test_requirements.py                        test US-004 (AC-004-01, BR-005: 3 test)
tests/test_pipeline_baseline.py                   hồi quy nhận diện 23/23 ký tự đúng
tests/fixtures/heatmap_golden.npz                 golden reference (sinh từ notebook cũ)
tests/_generate_golden.py                         script sinh lại golden (không phải test)
.venv/                                            môi trường Python 3.12.7 đã sẵn sàng (~2,5 GB, gitignored)
```

---

## 4. Hợp đồng dữ liệu (quan trọng nhất)

Mỗi CSV có **1 dòng header + 1 dòng dữ liệu**, **93 cột**, thứ tự cố định:

| Nhóm | Số cột | Chi tiết |
|---|---|---|
| `hand_{x,y,z}_{0..20}` | 63 | 21 landmark x 3, xen kẽ x,y,z theo từng điểm |
| `face_{x,y,z}_{idx}` | 30 | 10 điểm x 3, `idx` theo đúng thứ tự dưới đây |

`face_keypoints = [10, 152, 234, 454, 33, 263, 1, 61, 291, 199]`
(giống nhau ở cả 3 notebook và `run_realtime.py:97`)

- Giá trị là toạ độ **chuẩn hoá 0..1** của MediaPipe.
- Điểm thiếu (không thấy tay/mặt) được ghi `0.0` và bị `create_heatmap` **bỏ qua**
  khi `x == 0 and y == 0`.
- `df.values.flatten()` cho ra đúng chuỗi `x,y,z` xen kẽ — **trùng khớp** với thứ tự
  mà code inference dựng (`hand_landmarks + face_landmarks`). Đổi thứ tự cột là hỏng
  model mà không báo lỗi.

**Số mẫu thực tế:** 23 thư mục, mỗi thư mục **70 CSV**, riêng `đ` có **69** (thiếu `65.csv`).
Tổng = **1609 mẫu**.

---

## 5. Các bẫy đã xác nhận — đọc trước khi sửa

1. **Dữ liệu bị bỏ quên:** `load_landmarks_data()` chỉ đọc `for i in range(1, 51)`
   (`train_cnn_pose_keras.ipynb`, cell load data) → **20 file cuối (51–70) của mọi
   ký tự bị bỏ qua**, dù đĩa có 70 file. Thực tế chỉ **1150/1609** mẫu được train.
2. **Đường dẫn tuyệt đối hard-code:** **ĐÃ GIẢI QUYẾT TRIỆT ĐỂ (US-003)**.
   Đã thay thế bằng module `src/vsl/config.py` đọc từ `VSL_MODEL_PATH`, `VSL_DATA_DIR` kèm fallback
   tương đối tự động tính từ `PROJECT_ROOT`. Toàn bộ repository sạch 100% không còn chuỗi `D:\` (BR-004).
3. **`np.eye(23)` và `Dense(23)` hard-code:** **ĐÃ GIẢI QUYẾT TRIỆT ĐỂ (US-002)**.
   Đã thay thế bằng `np.eye(NUM_CLASSES)` và `Dense(NUM_CLASSES)` với `NUM_CLASSES = len(VIETNAMESE_ALPHABET)`
   suy ra tự động từ `src/vsl/labels.py`.
4. **Cả hai đường inference yêu cầu `len(all_landmarks) == 93` chính xác.**
   Thiếu tay hoặc thừa tay $\to$ im lặng không dự đoán (`run_realtime.py` có in cảnh báo `Tay [OK/X] | Mat [OK/X]`).
5. **`create_heatmap` chỉ có MỘT bản duy nhất:** tại `src/vsl/heatmap.py` (US-001, commit `f83d787`).
   Công thức: `img_size=(224,224)`, `sigma=5`, kernel `-15..15`, cộng dồn, scale 255, 3 kênh RGB, bỏ qua `z`.
6. **`VIETNAMESE_ALPHABET` chỉ có MỘT bản duy nhất:** tại `src/vsl/labels.py` (US-002, commit `3bd486e`).
   Kiểu `tuple` bất biến gồm đúng 23 ký tự. Toàn bộ notebook, script và test đều import từ đây.
7. **`preprocess_input` của ResNet50:** Áp sau khi heatmap đã ở dạng `uint8 0..255`.
   Chuẩn hoá Caffe (trừ mean BGR), **tuyệt đối không chia cho 255**.
8. **Import trực tiếp từ `keras` thay vì `tensorflow.keras`:**
   Trên TF 2.19 + Keras 3, `tensorflow.keras` dùng lazy-loader khiến Language Server/Pyright
   trong IDE báo lỗi ảo `Cannot find module ...`. Đã chuẩn hoá sang `from keras.models import ...`
   và `from keras.applications.resnet50 import ...` để code sạch cảnh báo 100%.
9. **Không bật `horizontal_flip`** trong `ImageDataGenerator`: Lật ngang sẽ biến ký hiệu tay này
   thành ký hiệu tay khác. Code realtime dùng `cv2.flip(image, 1)` (coi gương) là chủ ý đúng.
10. **README ghi sai 2 chỗ:** ghi "50 mẫu/ký tự" (thực tế 70) và "độ chính xác 90%".

---

## 6. Kiến trúc model (nguồn: `train_cnn_pose_keras.ipynb`)

```
ResNet50(weights='imagenet', include_top=False, input_shape=(224,224,3))
→ GlobalAveragePooling2D
→ Dense(256, relu)
→ Dense(NUM_CLASSES, softmax)
```

Train 2 giai đoạn:
1. Đóng băng toàn bộ ResNet50 — Adam `lr=1e-3`, 50 epochs.
2. Mở băng **10 layer cuối** — Adam `lr=1e-4`, 20 epochs.

Cả hai dùng `EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)`, batch 32.

---

## 7. Thứ tự nhãn — Nguồn chân lý duy nhất (BR-003)

Được định nghĩa duy nhất tại `src/vsl/labels.py`:

```python
VIETNAMESE_ALPHABET = (
    'a', 'b', 'c', 'd', 'đ', 'e', 'g', 'h', 'i', 'k', 'l', 'm', 'n',
    'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'x', 'y'
)
NUM_CLASSES = len(VIETNAMESE_ALPHABET)  # = 23
```

- Bắt buộc có `đ`. Không có `f`, `j`, `w`, `z`.
- Dạng `tuple` bất biến (immutability) để ngăn chặn can thiệp sửa đổi runtime.
- Index trong tuple chính là nhãn lớp đầu ra của mạng nơ-ron.

---

## 8. Môi trường thực thi chuẩn

- Python runtime cho test & dev: `.venv\Scripts\python.exe` (Python 3.12.10, xác minh 2026-10-28).
- Lệnh chạy kiểm thử chuẩn:
  ```powershell
  & ".\.venv\Scripts\python.exe" -m pytest tests -v
  ```
  (Lần chạy sau thay đổi US-016: **41/41 tests PASSED**, 2026-10-28, ~33s).
- Lệnh chạy FastAPI server cục bộ chuẩn:
  ```powershell
  & ".\.venv\Scripts\python.exe" -m uvicorn src.vsl.service:app --port 8000
  ```
- Khi chạy script python có in tiếng Việt ra console, luôn đặt:
  ```powershell
  $env:PYTHONIOENCODING = "utf-8"
  ```
- File `requirements.txt` bắt buộc phải giữ **thuần ASCII**.

---

## 9. Giới Hạn Ghi Python (Ghi Chú Lịch Sử)

Ghi chú giới hạn ghi từ phiên 2026-10-19 (`C:\Users\doant\...`) chưa được xác minh trên host hiện tại.
Python `.venv` đã ghi được fixture US-016 trong workspace; không suy rộng kết quả này sang đường dẫn ngoài repo.

---

## 10. Tiến độ User Stories & Lịch sử Thực hiện

| Mã US | Tiêu đề | Nhánh | Trạng thái | Ghi chú nghiệm thu |
|---|---|---|---|---|
| **US-001** | Trích xuất `create_heatmap` thành một bản dùng chung duy nhất | `feature/US-001` | ✅ **PASS (2026-10-19)** | `src/vsl/heatmap.py`, AC-001-01, AC-001-02 (10 tests) |
| **US-002** | Trích xuất `VIETNAMESE_ALPHABET` thành nguồn chân lý duy nhất | `feature/US-002` | ✅ **PASS (2026-10-25)** | `src/vsl/labels.py`, AC-002-01, AC-002-02, BR-003 (14 tests) |
| **US-003** | Loại bỏ đường dẫn tuyệt đối hard-code | `feature/US-003` | ✅ **PASS (2026-10-26)** | `src/vsl/config.py`, biến môi trường `VSL_MODEL_PATH`, `VSL_DATA_DIR`, BR-004 (18 tests) |
| **US-004** | Chuẩn hoá `requirements.txt` cho Linux container | `feature/US-004` | ✅ **PASS (2026-10-26)** | `requirements.txt`, `opencv-python-headless`, BR-005 (21 tests) |
| **US-005** | API kiểm tra sức khỏe `/health` phản ánh trạng thái model | `feature/US-005` | ✅ **PASS (2026-10-26)** | `src/vsl/service.py`, GET `/health`, Lifespan BR-011 (24 tests) |
| **US-006** | API `/predict` nhận ảnh và chạy pipeline MediaPipe Python server-side | `feature/US-006` | ✅ **PASS (2026-10-26)** | `src/vsl/service.py`, POST `/predict`, MediaPipe 93 landmarks, tham số `flip`, AC-006-01, AC-006-02, BR-001, BR-006, BR-007 (32 tests) |
| **US-015** | Test hợp đồng dữ liệu 93 cột | `feature/US-015` | ✅ **PASS (2026-10-27)** | `src/vsl/landmarks.py`, `tests/test_landmark_contract.py`, AC-015-01/02, TSK-024/025, BR-001 (đã merge qua PR #11) |
| **US-016** | Test đối chiếu dịch vụ với kết quả notebook đã biết | `feature/US-016` | 🛠 **ĐANG CHỜ NGHIỆM THU** | Fixture tham chiếu 23 mẫu, test AC-016-01/02 và tài liệu hồi cứu `docs/api/US-016.md`; 41/41 test xanh, chờ chủ dự án xác nhận PASS |

---

## 11. Hướng dẫn tiếp tục công việc cho phiên tiếp theo

Khi bắt đầu phiên làm việc mới:
1. Đọc lại file này (`AGENTS.md`) và [`docs/WORKFLOW.md`](docs/WORKFLOW.md).
2. US-016 đã hoàn tất TSK-026/027 và toàn bộ test xanh; trình báo cáo CỔNG D để Chủ dự án xác nhận PASS.
3. Không push hoặc tạo PR nếu chưa có quyết định của Chủ dự án; sau nghiệm thu, làm US tiếp theo theo đầy đủ quy trình trong [`docs/WORKFLOW.md`](docs/WORKFLOW.md).
