# AGENTS.md — Sign-Language-Classification-v1.0

Bộ nhớ dự án cho agent. Đọc file này trước khi sửa code.
**Cập nhật lần cuối: 2026-11-11** — toàn bộ dữ kiện dưới đây được đo/đọc trực tiếp
từ repo trong phiên đó, không suy đoán. Nếu bạn phát hiện file này lệch với thực tế,
hãy sửa nó ngay (file có tiếng Việt, lưu ý UTF-8 khi sửa).

**Quy trình làm việc bắt buộc** (đồng bộ `develop` → tạo nhánh → đọc US → viết test
trước → làm từng task → nghiệm thu): xem [docs/process/WORKFLOW.md](docs/process/WORKFLOW.md).
Áp dụng cho **mọi** User Story, không có ngoại lệ.

---

## 1. Dự án là gì

Phân loại **bảng chữ cái ngôn ngữ ký hiệu tiếng Việt** (23 ký tự) từ webcam/ảnh.
Pipeline: ảnh → MediaPipe trích landmark bàn tay + mặt → sinh **heatmap
224x224x3** → CNN **ResNet50** → softmax 23 lớp.

**Repo:** `https://github.com/courseprojectICTU/Sign-Language-Classification.git`
(remote `origin`, đã xác minh từ `.git/config`). URL cũ `tpd05/Sign-Language-Classification-v1.0`
**không còn dùng** — đừng trích lại nó.

**Hai nguồn mô tả — chỉ một nguồn là thật:**

| Nguồn | Trạng thái |
|---|---|
| `docs/planning/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md` + `docs/architecture/ADR-001-*` | kế hoạch web hóa + CI/CD trên Azure |
| **chính source + git** | nguồn chân lý; AGENTS.md này bám theo đó |

Mã nguồn hiện tại = **package `src/vsl/` + dịch vụ FastAPI `src/vsl/service.py` (`GET /health`, `POST /predict`, `GET /version`, `CORSMiddleware` qua `VSL_ALLOWED_ORIGINS`) + frontend tĩnh `web/` + multi-stage `Dockerfile` (`linux/amd64`) + `infra/` Terraform + workflow CI PR `.github/workflows/ci.yml` + 3 notebook + 1 script Python native + CLI vận hành (`scripts/`)**.
Đã có bộ kiểm thử tự động `tests/` (bao gồm unit test thuần NumPy cho heatmap theo US-014, hợp đồng 93 landmark US-015, đối chiếu notebook US-016, healthcheck/predict/version/CORS, Dockerfile, benchmark harness US-013, Playwright web US-022, smoke test US-017, rollback US-031, CI workflow US-026, ops contract US-035/US-038 và kiểm thử Terraform US-018/US-019).
Hạ tầng staging đang chạy trên Microsoft Azure Container Apps Standard (`cae-vsl-staging-std` / `vsl-api`, `https://vsl-api.happyforest-6510ce4b.eastasia.azurecontainerapps.io`, `Multiple` revision mode) và Azure App Service (`vsl-vietnam`, `https://vsl-vietnam.azurewebsites.net`, đang được `web/config.js` trỏ tới); frontend tĩnh triển khai trên Cloudflare Pages (`https://sign-language-classification.pages.dev`). Chưa có pipeline CD tự động triển khai lên Azure (`US-029`); hiện có PR CI (`.github/workflows/ci.yml`, không push), workflow OIDC smoke test thủ công (`.github/workflows/azure-oidc-smoke.yml`) và workflow build/push ACR thủ công (`.github/workflows/acr-publish.yml`).

---

## 2. Git — trạng thái thực tế

| Mục | Giá trị (đối chiếu 2026-11-11) |
|---|---|
| Remote `origin` | `https://github.com/courseprojectICTU/Sign-Language-Classification.git` (fetch = push) |
| `origin/HEAD` | → `origin/develop` |
| `develop` / `origin/develop` | `4c44d09` (`Merge pull request #44 from courseprojectICTU/docs/sync-group4-azure-staging`) |
| Nhánh làm việc hiện tại | `feature/US-033` (đã merge `develop` `4c44d09`) |
| Đã merge vào `develop` | `US-001`..`US-008`, `US-010`, `US-012` (PR #32), `US-013` (PR #19), `US-014` (PR #20), `US-015` (PR #11), `US-016` (PR #12), `US-017` (PR #29), `US-018`/`US-019` (PR #22, PR #42), `US-022` (PR #23), `US-024` (PR #33, PR #37, PR #41), `US-025` (PR #28), `US-026` (PR #30), `US-031` (PR #27), `US-035` (PR #24), `US-038` (PR #31), cùng PR `#34`, `#36`, `#40`, `#44` |
| LFS | `git-lfs/3.7.0`; `.gitattributes` chỉ có `*.h5 filter=lfs` |
| `train/vsl_cnn_pose_keras.h5` | **file thật 137.042.364 bytes** (LFS đã smudge, không phải pointer) |
| Ghi chú cục bộ | Thư mục `docs/ideas/` được ignore trong `.gitignore` (không commit/push lên GitHub) |


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
  git -c http.sslBackend=openssl push origin <branch>
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
run_notebook.cmd                                  launcher Jupyter an toàn
pyproject.toml                                    cấu hình Ruff và Black (line-length=100, py312)
requirements.txt                                  deps đầy đủ cho notebook + runtime, THUẦN ASCII
requirements-runtime.txt                          deps tối giản cho Docker runtime image (US-038)
requirements-dev.txt                              pytest, ruff, black, playwright, httpx, fastapi...
Dockerfile                                        multi-stage Linux build ghim digest, port 8080, appuser (US-038)
.dockerignore                                     loại trừ context nặng cho build container (US-010/US-038)
.github/PULL_REQUEST_TEMPLATE.md                  biểu mẫu PR chuẩn tiếng Việt có dấu
.github/workflows/ci.yml                          PR/push CI: Ruff, Black, pytest, Docker build no-push (US-026/US-038)
.github/workflows/azure-oidc-smoke.yml            workflow_dispatch kiểm tra đăng nhập GitHub OIDC (US-019)
.github/workflows/acr-publish.yml                 workflow_dispatch build & push image linux/amd64 qua OIDC lên vslacr3795 (US-024/US-038)
web/index.html                                    giao diện web tĩnh tải/chụp ảnh (US-022)
web/app.js                                        logic gọi POST /predict, camera capture, hiển thị lỗi (US-022)
web/styles.css                                    giao diện responsive cho web/ (US-022)
web/config.js                                     cấu hình window.VSL_CONFIG.apiBaseUrl (US-022/US-024)
web/labels.json                                   23 nhãn sinh từ src/vsl/labels.py (US-022)
infra/versions.tf                                 ghim Terraform và AzureRM provider
infra/provider.tf                                 cấu hình AzureRM theo subscription
infra/backend.tf                                  Azure Blob remote backend
infra/registry.tf                                 cấu hình ACR và tác vụ purge tag định kỳ (US-019)
infra/identity.tf                                 deployment identity, RBAC tối thiểu và GitHub FIC (US-019)
infra/budget.tf                                   Azure subscription budget $5 với cảnh báo $1/$5 (US-033)
infra/outputs.tf                                  định danh OIDC và billing_budget_id (US-019/US-033)
infra/environments/{staging,production}.tfvars   biến theo môi trường; production cần điền giá trị đã xác minh
infra/bootstrap-azure/                            bootstrap Storage Account + private Blob container
infra/README.md                                   hướng dẫn bootstrap và init/plan với Azure Blob state
src/vsl/__init__.py                               re-export heatmap, labels, config
src/vsl/config.py                                 cấu hình đường dẫn tập trung (BR-004)
src/vsl/heatmap.py                                create_heatmap — BẢN DUY NHẤT (BR-002)
src/vsl/labels.py                                 VIETNAMESE_ALPHABET + NUM_CLASSES — BẢN DUY NHẤT (BR-003)
src/vsl/landmarks.py                              hợp đồng 93 cột + FACE_KEYPOINTS (BR-001)
src/vsl/service.py                                FastAPI service + /health, /predict, /version, CORS, lifespan
scripts/benchmark_cold_start.py                  benchmark 5 cold starts với preflight bắt buộc (US-013)
scripts/generate_web_labels.py                    sinh web/labels.json từ VIETNAMESE_ALPHABET (US-022)
scripts/smoke_test.py                             CLI kiểm tra /health, /version, /predict sau deploy (US-017)
scripts/rollback.py                               CLI rollback Azure Container Apps có dry-run và guard (US-031)
scripts/rollback.sh                               script Cloud Run cũ giữ lại cho test_ops_contract.py (legacy)
HUONG-DAN-CHAY.md                                 hướng dẫn chạy cho người dùng
README.md                                         tổng quan, chạy cục bộ, CI, Docker, vận hành
AGENTS.md                                         file này (bộ nhớ dự án)
docs/README.md                                    sơ đồ và mục lục tra cứu toàn bộ tài liệu dự án
docs/RUNBOOK.md                                   sổ tay vận hành & xử lý sự cố ACA/CI/CORS/Rollback/Chi phí
docs/PR_DESCRIPTION_US-038.md                     mô tả tổng hợp PR US-038
docs/implementation/US-IMPLEMENTATION-STATUS.md   bảng trạng thái và tồn đọng sau merge
docs/architecture/ADR-001-frontend-hosting.md     ADR chọn Cloudflare Pages kết hợp backend Azure
docs/architecture/THONG_TIN_DE_TAI.txt            tổng quan đề tài và kiến trúc đám mây
docs/planning/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md   kế hoạch 2 tuần / 4 mảng công việc kỹ thuật
docs/planning/KE-HOACH-CHUYEN-DOI-HA-TANG-AZURE.md kế hoạch chuyển đổi tài liệu sang Azure
docs/planning/product-backlog-cicd-2-tuan.xlsx    backlog (10 epic, 39 US, 63 AC, 75 task, 26 BR)
docs/process/WORKFLOW.md                          quy trình bắt buộc cho mọi US
docs/process/QUY-TRINH-REVIEW-PULL-REQUEST.md     hướng dẫn 5 bước thẩm định PR cho Reviewer
docs/process/QUY-TRINH-REVIEW-PULL-REQUEST.docx   bản xuất bản Word (.docx) của quy trình Reviewer
docs/infrastructure/HO-SO-BAN-GIAO-HA-TANG.md     hồ sơ bàn giao kỹ thuật hạ tầng Azure
docs/infrastructure/HUONG-DAN-TRIEN-KHAI-AZURE.md hướng dẫn đóng gói và triển khai Azure Container Apps
docs/infrastructure/HUONG-DAN-CAU-HINH-TEN-MIEN-AZURE.md hướng dẫn cấu hình tên miền Azure
docs/api/README.md                                quy ước + 9 phase + checklist API docs
docs/api/_TEMPLATE.md                             bộ khung 17 mục cho mỗi api doc
docs/api/US-001.md .. US-038.md                   hợp đồng API/CLI/hạ tầng theo từng User Story
docs/reports/US-012-BAO-CAO-THUC-HIEN.md          báo cáo thực hiện và nghiệm thu US-012
docs/reports/US-019_PR_Description_Cap_Nhat.md    báo cáo PR US-019
docs/reports/US-022-BAO-CAO-API-CORS.md           báo cáo đối chiếu API/CORS US-022
docs/reports/US-022-BAO-CAO-THUC-HIEN.md          báo cáo thực hiện US-022
docs/reports/TAI_LIEU_BAO_CAO.doc                 tài liệu báo cáo tổng hợp môn học định dạng Word
docs/backup_gcp_docs/                             bản sao lưu tài liệu gốc trước khi đổi sang Azure
tests/run_ops_tests.py                            runner kiểm thử nhóm ops contract
tests/test_ci_workflow.py                         kiểm thử workflow CI (US-026)
tests/test_cold_start_benchmark.py                unit test harness benchmark US-013
tests/test_config.py                              test US-003 (BR-004)
tests/test_cors.py                                test CORS allowlist US-025
tests/test_cors_version.py                        test tích hợp CORS và /version
tests/test_dockerfile.py                          test Dockerfile multi-stage & digest (US-010/US-038)
tests/test_health.py                              test US-005 (/health)
tests/test_heatmap.py                             NumPy-only heatmap tests US-014
tests/test_heatmap_contract.py                    golden/repository contract tests US-001
tests/test_labels.py                              test US-002 (BR-003)
tests/test_landmark_contract.py                   kiểm thử hợp đồng 93 cột (US-015)
tests/test_ops_contract.py                        kiểm thử hợp đồng CI/CD, CORS, rollback, runbook, Docker
tests/test_pipeline_baseline.py                   hồi quy nhận diện 23/23 ký tự đúng
tests/test_predict.py                             tests API US-006/US-007
tests/test_requirements.py                        test US-004 (BR-005)
tests/test_rollback.py                            test CLI rollback ACA US-031
tests/test_service_notebook_reference.py          đối chiếu service với kết quả notebook (US-016)
tests/test_smoke_test.py                          test CLI smoke test US-017
tests/test_us012_model_lifecycle.py               kiểm thử nạp model một lần, readiness và log duration (US-012)
tests/test_us016_notebook_direct.py               đối chiếu inference notebook/service; hash chuẩn hóa LF
tests/test_us018_terraform.py                     kiểm tra AzureRM provider, môi trường, Blob backend và bootstrap
tests/test_us019_azure_terraform.py               kiểm tra Terraform ACR cleanup, RBAC và OIDC (US-019)
tests/test_us019_secret_policy.py                 quét private key & static secret trên tree và git history
tests/test_us022_web.py                           kiểm thử Playwright cho giao diện web/ (US-022)
tests/test_us033_cost_guardrails.py               kiểm thử Terraform budget Azure, Entra ID MFA & runbook (US-033)
tests/test_version.py                             test US-008 (/version)
tests/fixtures/notebook_prediction_reference.json kết quả tham chiếu frozen 23 mẫu (US-016)
tests/fixtures/heatmap_golden.npz                 golden reference (sinh từ notebook cũ)
tests/_generate_service_reference.py              chuyển tiếp sang exporter trực tiếp (US-016)
tests/_export_us016_from_notebook.py              xuất dự đoán notebook và SHA model/CSV chuẩn hóa LF
tests/_generate_golden.py                         script sinh lại golden (không phải test)
.venv/                                            môi trường Python 3.12.7 (~2,5 GB, gitignored)
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
   tương đối tự động tính từ `PROJECT_ROOT`. Toàn bộ repository sạch 100% không còn chuỗi `D:\` trong mã nguồn (BR-004).
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
10. **Lưu ý số liệu gốc:** Bộ dữ liệu thực tế có 70 CSV/ký tự (trừ `đ` có 69, tổng 1609 mẫu), không phải 50 mẫu/ký tự.

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

- Python runtime trên terminal bình thường: `.venv\Scripts\python.exe` (Python 3.12.7).
- **Lưu ý trong sandbox agent trên máy Windows này:** `.venv\Scripts\python.exe`, `.venv\Scripts\ruff.exe`, `.venv\Scripts\black.exe` và driver `playwright/driver/node.exe` trong `.venv` có thể gặp lỗi nạp DLL (`_ctypes`/`_ssl`/`0xC0000142`). Khi đó:
  - Chạy Python, `pytest`, và `black` bằng Python gốc `D:\program\python\python.exe` (đã liên kết `.venv\Lib\site-packages` qua `D:\program\python\Lib\site-packages\vsl_project.pth`):
    ```powershell
    & "D:\program\python\python.exe" -m pytest tests --ignore=tests/test_us022_web.py -v
    & "D:\program\python\python.exe" -m black --check src tests scripts
    ```
  - Cài gói bổ sung vào `.venv` bằng `D:\program\python\python.exe -m pip install --prefix ".\.venv" --only-binary=:all: ...` (không cài đè `opencv-python-headless` lên môi trường webcam local nếu đang dùng `opencv-python`).
- Lệnh chạy kiểm thử đầy đủ (trên terminal ngoài sandbox hoặc CI Linux):
  ```powershell
  & ".\.venv\Scripts\ruff.exe" check src tests scripts
  & ".\.venv\Scripts\black.exe" --check src tests scripts
  & ".\.venv\Scripts\python.exe" -m pytest tests -v
  ```
- Lệnh chạy FastAPI server cục bộ chuẩn:
  ```powershell
  & "D:\program\python\python.exe" -m uvicorn src.vsl.service:app --port 8000
  ```
- Khi chạy script python có in tiếng Việt ra console, luôn đặt:
  ```powershell
  $env:PYTHONIOENCODING = "utf-8"
  ```
- File `requirements.txt` và `requirements-dev.txt` bắt buộc phải giữ **thuần ASCII**.

---

## 9. Giới Hạn Ghi Python (Ghi Chú Lịch Sử)

Ghi chú giới hạn ghi từ phiên 2026-10-19 (`C:\Users\doant\...`) chưa được xác minh trên host hiện tại.
Python `.venv` đã ghi được fixture US-016 trong workspace; không suy rộng kết quả này sang đường dẫn ngoài repo.

---

## 10. Tiến độ User Stories & Lịch sử Thực hiện

| Mã US | Tiêu đề | Nhánh / PR | Trạng thái | Ghi chú nghiệm thu |
|---|---|---|---|---|
| **US-001** | Trích xuất `create_heatmap` thành một bản dùng chung duy nhất | PR `#1`..`#4` / `develop` | PASS (2026-10-19) | `src/vsl/heatmap.py`, AC-001-01, AC-001-02 |
| **US-002** | Trích xuất `VIETNAMESE_ALPHABET` thành nguồn chân lý duy nhất | `develop` | PASS (2026-10-25) | `src/vsl/labels.py`, AC-002-01, AC-002-02, BR-003 |
| **US-003** | Loại bỏ đường dẫn tuyệt đối hard-code | `develop` | PASS (2026-10-26) | `src/vsl/config.py`, `VSL_MODEL_PATH`, `VSL_DATA_DIR`, BR-004 |
| **US-004** | Chuẩn hoá `requirements.txt` cho Linux container | `develop` | PASS (2026-10-26) | `requirements.txt`, `opencv-python-headless`, BR-005 |
| **US-005** | API `/health` phản ánh trạng thái model | PR `#9` | PASS (2026-10-26) | `src/vsl/service.py`, GET `/health`, Lifespan BR-011 |
| **US-006** | API `/predict` nhận ảnh và chạy MediaPipe server-side | PR `#10` | PASS (2026-10-26) | `src/vsl/service.py`, POST `/predict`, 93 landmarks, `flip` |
| **US-007** | Trả trạng thái rõ ràng khi không phát hiện tay hoặc mặt | PR `#17` | PASS (2026-11-04) | `status`: `ok`/`no_hand`/`no_face`; log WARNING UTC |
| **US-008** | API `/version` trả model version, Git SHA và build time | PR `#18` | PASS (2026-11-04) | `GET /version`, `GIT_SHA`/Git fallback, UTC ISO 8601 |
| **US-010** | Dockerfile Linux chạy được ở máy cục bộ | `develop` (`51fe345`) | PASS (2026-11-05) | `Dockerfile`, `.dockerignore`, healthcheck `/health` 200 |
| **US-012** | Nạp model một lần ngoài request handler | PR `#32` | PASS (2026-11-08) | Đã merge `develop`; log duration khi load thành công/thất bại |
| **US-013** | Đo và ghi lại thời gian khởi động nguội thực tế | PR `#19` | PASS (Harness & Tests) | `scripts/benchmark_cold_start.py`, `docs/api/US-013.md` |
| **US-014** | Unit test cho `create_heatmap` chạy thuần NumPy | PR `#20` | PASS (2026-11-06) | `tests/test_heatmap.py`, input sai ném `ValueError` |
| **US-015** | Test hợp đồng dữ liệu 93 cột | PR `#11` | PASS (2026-10-27) | `src/vsl/landmarks.py`, `tests/test_landmark_contract.py` |
| **US-016** | Test đối chiếu dịch vụ với kết quả notebook đã biết | PR `#12`, PR `#36` | PASS (2026-10-28) | Fixture 23 mẫu có hash model/CSV chuẩn hóa LF |
| **US-017** | Smoke test tự động sau triển khai | PR `#29` | MERGED (CLI PASS) | `scripts/smoke_test.py`; unit test pass; live deploy/CD chờ US-029 |
| **US-018** | Khởi tạo Terraform và lưu trạng thái từ xa trên Azure | PR `#22` | PASS — STAGING | AzureRM + Blob state `vslstate2026`/`tfstate`; production placeholder |
| **US-019** | ACR, IAM tối thiểu và GitHub Workload Identity Federation | PR `#22`, PR `#42` | PASS — STAGING APPLIED | Đã đăng ký `Microsoft.ManagedIdentity`, apply `infra/` vào `vslstate2026`, OIDC smoke test & `acr-publish.yml` (`42843489497`) chạy xanh; `azurerm_container_registry_task.cleanup` bị gói Students chặn (`TasksOperationsNotAllowed`) |
| **US-022** | Trang web tĩnh tải hoặc chụp ảnh và hiển thị kết quả | PR `#23` | MERGED — PASS | `web/` + `scripts/generate_web_labels.py` + `tests/test_us022_web.py` |
| **US-024** | Triển khai frontend lên Cloudflare Pages | PR `#33`, PR `#37`, PR `#41` | PARTIAL (AC-024-01 LIVE OK) | `https://sign-language-classification.pages.dev` HTTP 200; live CORS/`/health`/`/version`/`POST /predict` đã pass trên cả `vsl-vietnam` (`web/config.js`) và `vsl-api` (`9a1c3aa...`); còn AC-024-02 (scale-to-zero `<1s`) và thử ảnh tay+mặt thật |
| **US-025** | Cấu hình CORS và xử lý lỗi mạng | PR `#28` | PASS — STAGING LIVE | Strict allowlist `VSL_ALLOWED_ORIGINS=https://sign-language-classification.pages.dev` đang chạy live trên cả `vsl-vietnam` lẫn Standard ACA `vsl-api` |
| **US-026** | Pipeline CI chạy lint, test và docker build | PR `#30`, PR `#36` | MERGED | `.github/workflows/ci.yml` + `pyproject.toml` + `tests/test_ci_workflow.py` |
| **US-031** | Rollback backend Azure Container Apps bằng traffic split | PR `#27` | MERGED (CLI PASS) | `scripts/rollback.py`; `vsl-api` trên `cae-vsl-staging-std` đã dùng `Multiple` revision mode; chờ diễn tập live + US-029 |
| **US-033** | Billing Budget và MFA bảo vệ ràng buộc chi phí bằng 0 | `feature/US-033` | PASS — STAGING VERIFIED | Đã apply `vsl-monthly-cost-guardrail-staging` (`$5`, `20%` `$1` / `100%` `$5`, `Owner`) trên `373b1f03-330f-4302-a9e9-aa1fe793bf2e` và xác minh trên Azure Portal; Entra ID `Security defaults: Enabled`; `docs/RUNBOOK.md` Mục 7, `docs/api/US-033.md`, `tests/test_us033_cost_guardrails.py` |
| **US-035** | README và Runbook xử lý sự cố | PR `#24` | MERGED + CLEANED | `README.md`, `docs/RUNBOOK.md`, `US-IMPLEMENTATION-STATUS.md` |
| **US-038** | Tối ưu và tái lập quá trình build image, CI/CD và vận hành | PR `#31` | MERGED + PUBLISHED | Multi-stage digest, `requirements-runtime.txt`; image `9a1c3aa847e19ef4a85d6bec9d36afc3d5c5e76f` đã push lên `vslacr3795` |

---

## 11. Hướng dẫn tiếp tục công việc cho phiên tiếp theo

1. **Hạ tầng Azure staging sau Nhóm 4 (2026-11-11):**
   - `vslacr3795.azurecr.io/vsl-api:9a1c3aa847e19ef4a85d6bec9d36afc3d5c5e76f` đã chạy live trên cả App Service `vsl-vietnam` (`https://vsl-vietnam.azurewebsites.net`, target của `web/config.js`) và Standard ACA `vsl-api` (`https://vsl-api.happyforest-6510ce4b.eastasia.azurecontainerapps.io` trên `cae-vsl-staging-std`, dùng UAMI `id-vsl-api-pull` với `AcrPull`, `Multiple` revision mode).
   - Environment Express cũ `cae-vsl-staging` đã tách `vsl-api` ra; chủ dự án có thể xóa dọn khi xác nhận không còn dùng.
   - `azurerm_role_assignment.deployment_app` đã được khôi phục cho `vsl-api` mới; `azurerm_container_registry_task.cleanup` vẫn bị giới hạn gói Azure for Students (`TasksOperationsNotAllowed`).
2. **US-024 / US-017 kiểm chứng end-to-end với ảnh thật:** chạy `scripts/smoke_test.py --image <ảnh tay+mặt thật>` và kiểm tra browser trực tiếp trên `https://sign-language-classification.pages.dev`; đo `AC-024-02` nếu chủ dự án duyệt thử scale-to-zero (`minReplicas=0`).
3. **US-029:** triển khai pipeline CD tự động (OIDC + push ACR + deploy Standard ACA `vsl-api` / App Service + `scripts/smoke_test.py` + `scripts/rollback.py`).
4. **Quy tắc an toàn:** Không gửi Client Secret trong chat hoặc repository; không commit Terraform state, plan hay credentials; không tự push/PR nếu chưa có quyết định của chủ dự án.
