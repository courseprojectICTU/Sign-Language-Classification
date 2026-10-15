# KẾ HOẠCH NÂNG CẤP: WEB HÓA + CI/CD (2 TUẦN / 4 NGƯỜI)

> Vai trò soạn: Product Owner. Bản **v4 (cuối) — backend Google Cloud Run + frontend Cloudflare Pages**. Ngày 2026-10-15.
> Dữ kiện "hiện trạng" đã được **kiểm chứng trực tiếp từ repo**, không suy đoán.

---

## 0. LỊCH SỬ QUYẾT ĐỊNH (và vì sao thay đổi)

**Ngăn xếp đã chốt:** **Cloud Run** (backend) + **Cloudflare Pages** (frontend), cả hai trong free tier.

**Quyết định đã chốt qua 4 vòng:**

| # | Quyết định | Trạng thái |
|---|---|---|
| 1 | MVP = **tải/chụp 1 ảnh → trả ký tự** (không realtime streaming) | ✅ Chốt |
| 2 | Ngân sách = **free** (~0 USD/tháng) | ✅ Chốt |
| 3 | Backend = **Google Cloud Run** (thay vì AWS Lambda) | ✅ Chốt |
| 4 | Frontend = **Cloudflare Pages** (thay vì Firebase) — xem [ADR-001](ADR-001-frontend-hosting.md) | ✅ Chốt |
| 5 | Deploy frontend bằng **GitHub Actions + `wrangler`**, không dùng Git integration của Cloudflare | ✅ Chốt |

**Đổi từ AWS sang Cloud Run mang lại 3 lợi ích kỹ thuật lớn:**

| # | Thay đổi | Hệ quả |
|---|---|---|
| **1** | Cloud Run cho **tới 8 GB RAM** (Lambda bị giới hạn bởi image + cold start) | Chạy **MediaPipe Python ngay trên server** ⇒ **R-1 (lệch landmark JS/Python) BIẾN MẤT HOÀN TOÀN** |
| **2** | Không còn ràng buộc image "phải gầy" | Giữ **TensorFlow** được ⇒ **R-5 hạ cấp** từ "có thể phá hỏng kiến trúc" xuống "tối ưu hoá tuỳ chọn" |
| **3** | Cloud Run có **Revision + Traffic splitting** | Rollback/canary tốt hơn Lambda alias, gần như miễn phí |

**Điểm mấu chốt:** hai rủi ro tôi từng đánh dấu là *có thể phá hỏng kiến trúc* (R-1, R-5) **tồn tại chỉ vì ràng buộc của Lambda**. Đổi nền tảng đã xoá rủi ro thứ nhất và vô hiệu hoá rủi ro thứ hai.

**Hệ quả phụ rất đáng giá:** API contract **đơn giản hơn nhiều**. Không còn phải định nghĩa và bảo vệ "hợp đồng 93 số float" giữa trình duyệt và server — trình duyệt chỉ cần **gửi ảnh**, server làm toàn bộ pipeline giống hệt lúc train.

---

## 1. TÓM TẮT ĐIỀU HÀNH

**Sự thật quan trọng nhất:**

> Dự án **chưa có backend**. Toàn bộ mã nguồn là **3 Jupyter Notebook**. Không có file `.py`, không có test, không có Dockerfile, không có CI, không có hạ tầng.

Yêu cầu "dựa vào backend hiện tại để triển khai lên website" thực chất là **phải viết backend mới**:

| Yêu cầu | Thực tế | Kết luận |
|---|---|---|
| "Triển khai backend lên website" | Chưa có backend | **Xây backend mới** |
| "Sau đó làm CI/CD lên cloud" | Chưa có artifact để deploy | CI/CD làm **song song** |
| "Chỉ tập trung CI/CD" | CI/CD cần artifact ổn định trước | **Tuần 1 artifact, Tuần 2 CI/CD** |

**Điểm kỹ thuật mấu chốt:** `run_realtime.ipynb` mở webcam **trên máy local** (`cv2.VideoCapture(0)`) và hiển thị **trong notebook** — **không thể chạy trên server**. Bắt buộc tách thành frontend (trình duyệt) + backend (Cloud Run).

---

## 2. RÀNG BUỘC "$0" TRÊN GOOGLE CLOUD

> ⚠️ **Cảnh báo trung thực:** chính sách free tier thay đổi theo thời gian. Tôi **không xác minh được đầy đủ** các con số dưới đây trong phiên này (trang pricing của Google render bằng JS nên bị cắt khi tải). Các mục đánh dấu ⚠️ **phải kiểm tra lại** trên trang Google Cloud tại thời điểm tạo tài khoản.

### 2.1. Miễn phí — dùng được

| Dịch vụ | Mức miễn phí | Vai trò |
|---|---|---|
| **Cloud Run** | ⚠️ ~180.000 vCPU-giây + ~360.000 GiB-giây + **2 triệu request**/tháng | **Compute chính** |
| **Artifact Registry** | ⚠️ 0,5 GB | Chứa image |
| **Cloud Build** | ⚠️ ~120 phút build/ngày | Build image (**phương án dự phòng** — xem §9.3) |
| **Cloud Storage** | ⚠️ 5 GB | Frontend tĩnh / artifact |
| **Cloud Logging** | ⚠️ 50 GB/tháng | Log |
| **Secret Manager** | ⚠️ 6 secret | Cấu hình nhạy cảm |
| **Workload Identity Federation** | Miễn phí | **Xác thực CI → GCP không cần key** |
| **Cloudflare Pages** | Không thấy ghi giới hạn băng thông; **500 build/tháng**; preview deploy không giới hạn | Frontend (**đã chốt**) |
| **Firebase Hosting (Spark)** | 10 GB + 360 MB/ngày | Frontend (phương án yếu hơn — xem ADR-001) |

### 2.2. KHÔNG miễn phí — phải tránh

| Dịch vụ | Chi phí | Xử lý |
|---|---|---|
| **Cloud Load Balancer** | ~18 USD/tháng | ❌ **Bỏ** — Cloud Run đã có HTTPS sẵn |
| **Cloud CDN** | ~0,08 USD/GB | ❌ **Bỏ** |
| **Cloud NAT** | Tính theo giờ + dung lượng | ❌ **Bỏ** |
| **`min-instances = 1`** | Tính tiền **liên tục 24/7** | ❌ **Cấm** — xem §2.3 |
| Cloud SQL / Redis | — | ❌ Không cần cho MVP |

### 2.3. Cảnh báo quan trọng nhất: đừng bật "min instances = 1"

Đây là cái bẫy phá vỡ ràng buộc $0 nhanh nhất. Cloud Run mặc định **scale về 0** khi không có traffic ⇒ **không tốn tiền khi idle**.

Nếu đặt `min-instances = 1` để tránh cold start, service chạy 24/7:
`1 vCPU × 730 giờ ≈ 2.630.000 vCPU-giây/tháng` — **vượt xa** mức miễn phí ~180.000 ⇒ **tốn tiền thật**.

**⇒ Bắt buộc giữ `min-instances = 0` và chấp nhận cold start.** Đây là lý do ONNX vẫn đáng làm (§5.3), vì nó rút cold start từ ~20 s xuống ~5 s.

### 2.4. Chuẩn bị tài khoản Google Cloud

Nhóm **đã có thẻ tín dụng/ghi nợ** và **là sinh viên** ⇒ có 2 lợi thế:

1. **Google Cloud free trial**: tài khoản mới thường được ⚠️ **~300 USD credit trong 90 ngày**. Đây là khoản đệm rất lớn — nhưng **hết hạn thì phải quay về free tier**, đừng thiết kế dựa vào nó.
2. **GitHub Student Developer Pack**: ⚠️ thường kèm credit Google Cloud — nên kiểm tra vì nhóm đã có GitHub.

**Bắt buộc làm ngay khi có tài khoản (Ngày 0):**
1. Tạo **Billing Budget** cảnh báo ở ngưỡng **1 USD** và **5 USD**.
2. Bật **MFA** cho tài khoản Google.
3. **Không** tạo service account key dạng JSON — dùng **Workload Identity Federation** (§9.3).

---

## 3. HIỆN TRẠNG ĐÃ KIỂM CHỨNG

### 3.1. Cấu trúc & kích thước

| Hạng mục | Giá trị đo được |
|---|---|
| Tổng dung lượng repo | 135.1 MB (chủ yếu là model) |
| Notebook | 3 |
| File `.py` | **0** |
| `requirements.txt` | ✅ **ĐÃ CÓ** (xem §3.3) |
| `Dockerfile` | **0** |
| Test | **0** |
| CI/CD config | **0** |
| Model `train/vsl_cnn_pose_keras.h5` | 137.042.364 bytes = **130,7 MiB**, quản lý bởi **Git LFS** |
| Dữ liệu | **1609** CSV / 23 thư mục (mỗi ký tự 70 file, riêng `đ` có 69 — thiếu `65.csv`) |
| Git history | 9 commit, gần như chỉ sửa README |
| Nhánh | `main` và `master` **trùng nhau** (0/0 ahead-behind) |

### 3.2. Môi trường (đã xác minh)

| Kiểm tra | Kết quả |
|---|---|
| Python hệ thống mặc định | 3.14.5 → **không có wheel TensorFlow** |
| Python 3.12 khả dụng | ✅ `D:\program\python\python.exe` (3.12.7) |
| `conda` | ❌ **không tồn tại** trên máy |
| env `mnist_project` (notebook kernelspec trỏ tới) | ❌ **không có trên máy** |
| `.venv` | ❌ chưa tạo |
| TF / mediapipe / cv2 / numpy trên Python mặc định | ❌ thiếu toàn bộ |
| `docker`, `gcloud`, `terraform`, `gh` CLI | ❌ **chưa cài** |
| `git lfs` | ✅ 3.7.0 |

### 3.3. `requirements.txt` — đã có và đã được kiểm chứng

Ghim đúng tổ hợp chạy được: `tensorflow==2.19.1`, `keras==3.15.1`, `mediapipe==0.10.21`, `numpy==1.26.4`, `pandas`, `scikit-learn`, `h5py`, `protobuf==4.25.9`, `opencv-python==4.11.0.86`, `pillow`, `matplotlib`, `notebook`, `ipykernel`.

Ba ràng buộc **sống còn** (đọc kỹ trước khi nâng cấp gói):

| Ràng buộc | Lý do |
|---|---|
| **Python phải 3.9–3.12** | 3.13/3.14 không có wheel TensorFlow |
| **mediapipe phải 0.10.x** | Từ 1.0.0 MediaPipe **xoá `mp.solutions`** → cả 3 notebook chết ngay |
| **numpy phải <2** | mediapipe 0.10.x ghim `numpy<2`; ép lên 2.x → lỗi import |

> ✅ **Tin tốt:** rủi ro "môi trường không tái lập" **đã được giải quyết**.
> ⚠️ **Lưu ý cho Cloud Run:** `requirements.txt` hiện có `opencv-python` (bản desktop). Trong container Linux **phải đổi sang `opencv-python-headless`** và thêm `libgl1`/`libglib2.0-0` — bản desktop cần thư viện đồ hoạ không có trong image `slim`.

### 3.4. Xác nhận các "bẫy" trong AGENTS.md (đã đối chiếu source)

| # | Bẫy | Bằng chứng (file:line) | Ảnh hưởng tới deploy |
|---|---|---|---|
| 1 | Chỉ đọc 50/70 file mỗi ký tự | `train_cnn_pose_keras.ipynb:102` — `for i in range(1, 51)` | Chỉ 1150/1609 mẫu được train |
| 2 | Hard-code đường dẫn Windows | `capture:75`, `train:33`, `run_realtime:46` | **Vỡ trên Linux/container** |
| 3 | `np.eye(23)` hard-code | `train:134` | Thêm/bớt ký tự → lỗi one-hot |
| 4 | Yêu cầu đúng 93 landmark, im lặng nếu sai | `run_realtime:145` | UX web: "không có gì xảy ra" |
| 5 | `create_heatmap` định nghĩa 2 lần | `train` + `run_realtime:67` | Train/inference lệch nhau |
| 6 | `preprocess_input` kiểu Caffe | `run_realtime:148` | **Không được đổi thành `/255`** |
| 7 | `horizontal_flip=False` | `train:167` | Đúng chủ ý — giữ nguyên |
| 8 | `model.save()` ghi vào CWD | `train:380` | Artifact sai chỗ |
| 9 | Đánh giá không lặp lại được | test set ~115 mẫu | "90%" không phải bằng chứng |
| 10 | `VIETNAMESE_ALPHABET` lặp 3 nơi | cả 3 notebook | Nguồn chân lý phân tán |

**Kết luận:** `AGENTS.md` **chính xác** so với source. Sai lệch duy nhất: `README.md` ghi "50 mẫu/ký tự" trong khi đĩa có 70.

---

## 4. VẤN ĐỀ & RỦI RO

### P0 — Chặn hoàn toàn việc deploy

| ID | Vấn đề | Trạng thái |
|---|---|---|
| ~~P0-2~~ | ~~Không có `requirements.txt`~~ | ✅ **ĐÃ XONG** |
| **P0-1** | Không có backend/service nào | Mở |
| **P0-3** | Đường dẫn tuyệt đối `D:\...` hard-code 3 nơi | Mở |
| **P0-4** | Logic inference nằm trong notebook, không import được | Mở |
| **P0-5** | `create_heatmap` trùng lặp 2 bản | Mở |
| **P0-6** | Không có test nào | Mở |
| **P0-7** | Model 130,7 MB qua Git LFS | Mở |
| **P0-8** | Chưa có tài khoản Google Cloud | **Chặn cứng — §11** |

### P1 — Cần cho vận hành CI/CD

| ID | Vấn đề |
|---|---|
| **P1-1** | Hai nhánh `main` + `master` trùng nhau → phải chốt 1 |
| **P1-2** | Không có branch protection |
| **P1-3** | Không có healthcheck endpoint |
| **P1-4** | `len(all_landmarks) == 93` fail âm thầm → web cần lỗi rõ ràng |
| **P1-5** | Không có Dockerfile |
| **P1-6** | Không có IaC |
| **P1-7** | Không có logging/metrics |
| **P1-8** | `VIETNAMESE_ALPHABET` lặp 3 nơi |
| **P1-9** | Chưa cài `docker`/`gcloud`/`terraform` CLI |
| **P1-10** | 🆕 `opencv-python` (desktop) sẽ lỗi trong container `slim` → phải chuyển `headless` |

### P2 — Nợ kỹ thuật, xử lý sau 2 tuần

| ID | Vấn đề |
|---|---|
| **P2-1** | Chỉ train 1150/1609 mẫu (`range(1,51)`) — **retrain là việc riêng, ngoài 2 tuần** |
| **P2-2** | `np.eye(23)` hard-code → suy ra từ `len(VIETNAMESE_ALPHABET)` |
| **P2-3** | Test set ~115 mẫu, 1 người quay → "90%" không đáng tin |
| **P2-4** | Sửa heatmap phải sửa 2 bản → hết sau khi gộp module |
| **P2-5** | `đ` thiếu `65.csv` |
| **P2-6** | `model.save()` ghi vào CWD |
| **P2-7** | Repo 135 MB, chưa có `.gitignore` cho artifact |

### Rủi ro dự án

| ID | Rủi ro | Mức | Trạng thái / Giảm thiểu |
|---|---|---|---|
| ~~**R-1**~~ | ~~Landmark MediaPipe JS ≠ Python~~ | ~~Cao~~ | ✅ **ĐÃ XOÁ** — chạy MediaPipe Python trên server (§5.4) |
| **R-5** | Chuyển Keras → ONNX thất bại | **Thấp** (hạ từ Trung bình) | Chỉ còn là **tối ưu cold start**; giữ TensorFlow là phương án dự phòng hợp lệ |
| **R-2** | **Cold start** (Cold Run scale-to-zero) | Trung bình | ONNX (~5 s); hiển thị spinner; **cấm** `min-instances=1` (tốn tiền) |
| **R-3** | **Vượt free tier âm thầm** | Trung bình | **Billing Budget 1 USD**; `min-instances=0`; `max-instances` thấp |
| **R-4** | Image vượt 0,5 GB free của Artifact Registry | Thấp | ONNX giữ image ~700 MB; lifecycle policy xoá image cũ |
| **R-6** | **Chưa có tài khoản Google Cloud** | **Cao** | Làm Ngày 0 **ngay** |
| **R-7** | 4 người × 2 tuần là rất ngắn | **Cao** | Cắt scope (§6); bảo vệ đường găng |
| **R-8** | Nhóm chưa từng làm cloud/CI-CD | Trung bình | Cloud Run đơn giản hơn ECS+ALB rất nhiều; cặp đôi P3–P4 |
| **R-9** | Model chưa chứng minh được độ chính xác thật | Trung bình | Đặt kỳ vọng: đây là **MVP/demo**, không truyền thông "90%" |
| **R-10** | 🆕 **Build và push image chậm**: build mất 3–5 phút, push 700 MB–2,3 GB | Trung bình | **Cache `type=gha` là bắt buộc**; ONNX → image ~700 MB, push nhanh hơn ~3 lần; Cloud Build là dự phòng |

---

## 5. KIẾN TRÚC MỤC TIÊU

### 5.1. Sơ đồ tổng thể

```
┌──────────────────────────────────────┐
│        NGƯỜI DÙNG (Browser)          │
│  - Trang tĩnh: chọn/chụp 1 ảnh       │
│  - Hiển thị ký tự + độ tin cậy       │
│  (KHÔNG chạy MediaPipe trên browser) │
└──────────────┬───────────────────────┘
               │ HTTPS  POST /predict  (multipart: 1 ảnh)
               │
      ┌────────┴─────────┐
      ▼                  ▼
┌───────────────┐  ┌──────────────────────────────────────┐
│ Cloudflare    │  │  Cloud Run (service, scale-to-zero)  │
│ Hosting       │  │  Container: FastAPI + MediaPipe +    │
│ (frontend tĩnh│  │  ONNX Runtime                        │
│  SSL miễn phí)│  │                                      │
└───────────────┘  │  1. nhận ẢNH                         │
                   │  2. MediaPipe PYTHON (hand + face)   │
                   │     ← ĐÚNG thư viện lúc train        │
                   │  3. create_heatmap()  ← dùng CHUNG   │
                   │  4. preprocess_input() Caffe         │
                   │  5. ONNX Runtime → 23 lớp            │
                   │  6. trả {letter, confidence}         │
                   └──────────────┬───────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
     Artifact Registry     Cloud Logging      Cloud Run Revision
     (image ~700 MB)       + Budget alert     + Traffic splitting
```

### 5.2. Thành phần

| Thành phần | Chọn | Vì sao |
|---|---|---|
| Backend runtime | **Cloud Run** | Scale-to-zero ⇒ $0 khi idle; có HTTPS sẵn; tới 8 GB RAM |
| Registry | **Artifact Registry** | Chuẩn của GCP |
| Frontend | ✅ **Đã chốt: Cloudflare Pages** (xem [ADR-001](ADR-001-frontend-hosting.md)) | Băng thông free không thấy giới hạn; **preview deploy mỗi PR không giới hạn**; không hạn chế thương mại; **tạo pipeline thứ 2 để học CI/CD** |
| Xác thực CI | **Workload Identity Federation** | Không cần service account key (tương đương OIDC của AWS) |
| IaC | **Terraform** (google provider) | Phổ biến, dễ tìm tài liệu |
| CI/CD | **GitHub Actions** | Repo đã ở GitHub |
| Log/Alert | **Cloud Logging** + **Billing Budget** | Bảo vệ ràng buộc $0 |

> **Phương án frontend đơn giản hơn:** phục vụ luôn file tĩnh từ chính container Cloud Run ⇒ chỉ còn **1 deploy target**. Nhanh hơn, nhưng mất pipeline thứ hai để học CI/CD.
>
> ⚠️ **Lưu ý quan trọng đã phân tích ở [ADR-001](ADR-001-frontend-hosting.md):** nếu phục vụ HTML từ chính Cloud Run, thì với `min-instances = 0`, **mỗi lượt truy cập đầu tiên sẽ thấy TRANG TRẮNG 5–20 giây** (cold start chặn cả trang web, không chỉ API). Đây là lý do chính khiến ADR-001 đề xuất **một host tĩnh riêng (Cloudflare Pages)**. Xem ADR để biết đầy đủ trade-off và các biện pháp giảm thiểu.

### 5.3. Vì sao vẫn nên chuyển ONNX (nhưng không bắt buộc)

| | TensorFlow | **ONNX Runtime** |
|---|---|---|
| Kích thước runtime | ~600 MB+ | **~50 MB** |
| Kích thước image | ~2,3 GB | **~700 MB** |
| Cold start | ~15–25 s | **~5 s** |
| Thời gian push image trong CI | Chậm | **Nhanh ~3 lần** |
| Vượt free Artifact Registry 0,5 GB? | Có (tốn ~0,15 USD/tháng) | Nhẹ (tốn ~0,02 USD/tháng) |
| Công sức | 0 | ~0,5–1 ngày + parity test |

**Kết luận:** vì **không được phép bật `min-instances=1`** (§2.3), cold start là thứ người dùng **luôn** gặp ở request đầu. ONNX rút ngắn từ ~20 s xuống ~5 s — đáng làm.

**Nhưng R-5 đã hạ cấp:** nếu chuyển đổi thất bại, **cứ giữ TensorFlow** — vẫn miễn phí, chỉ chậm hơn và tốn ~0,15 USD/tháng. Đây không còn là rủi ro chặn.

### 5.4. Quyết định quan trọng nhất: MediaPipe chạy ở đâu?

| | **Phương án A — Server (MediaPipe Python)** ✅ **CHỌN** | Phương án B — Browser (MediaPipe JS) |
|---|---|---|
| Luồng | Browser gửi **ảnh** → server chạy MediaPipe Python | Browser chạy MediaPipe JS → gửi 93 số |
| Khớp với lúc train | ✅ **Chính xác** — cùng thư viện, cùng phiên bản | ⚠️ Có thể lệch |
| **R-1 (lệch landmark)** | ✅ **Không tồn tại** | ⚠️ Phải kiểm chứng, có thể sai âm thầm |
| Image | ~700 MB | ~300 MB |
| Cold start | ~5 s | ~3 s |
| Băng thông | Cao hơn (~200 KB/ảnh) | ~1 KB |
| Chi phí | Cao hơn nhưng vẫn trong free tier | Thấp hơn |

**Vì sao chọn A:** Cloud Run cho **tới 8 GB RAM** và **không giới hạn image gắt** — những ràng buộc từng buộc ta phải chọn B trên Lambda **không còn tồn tại**. Đổi lại ~2 s cold start và băng thông, ta **xoá được rủi ro sai âm thầm** — rủi ro nguy hiểm nhất trong mọi dự án ML.

**Lưu ý bắt buộc giữ nguyên hành vi lúc train:**
- `run_realtime` **lật ảnh** (`cv2.flip(image,1)`) trước khi trích landmark. Server **phải lật tương tự**.
- `create_heatmap` bỏ qua trục `z` — giữ nguyên.
- `preprocess_input` kiểu Caffe — **không đổi thành `/255`**.

### 5.5. Hợp đồng API (đã đơn giản hơn nhiều so với bản AWS)

```
POST /predict          Content-Type: multipart/form-data
  file: <ảnh JPG/PNG>

200 OK
{
  "status": "ok",
  "letter": "đ",
  "confidence": 0.93,
  "top_k": [{"letter": "đ", "confidence": 0.93}, ...],
  "model_version": "v1.0.0"
}

200 OK (không phát hiện được)
{ "status": "no_hand" }     // ← thay cho việc IM LẶNG như run_realtime.ipynb:145
{ "status": "no_face" }

400 / 413 / 415 khi ảnh sai định dạng / quá lớn / sai content-type
```

> Không còn "hợp đồng 93 số float" — **giảm hẳn một bề mặt lỗi** so với kiến trúc browser-side.
> **Cải thiện so với hiện trạng:** `run_realtime.ipynb` im lặng hoàn toàn khi thiếu tay/mặt (P1-4). API mới **trả trạng thái rõ ràng** để web hiển thị "Không thấy bàn tay, vui lòng thử lại".

---

## 6. PHẠM VI 2 TUẦN

### 6.1. TRONG phạm vi (cam kết)

1. Tách logic inference khỏi notebook thành **package Python** dùng chung.
2. **FastAPI service**: `/health`, `/predict`, `/version`.
3. **Pipeline ảnh server-side**: MediaPipe Python → heatmap → model.
4. **Web UI tối giản**: chụp/tải ảnh → hiển thị ký tự + độ tin cậy.
5. **Chuyển model Keras → ONNX** + parity test Keras vs ONNX *(hạ xuống ưu tiên thứ yếu nếu hết thời gian)*.
6. **Dockerfile** (Linux, **multi-stage**, `opencv-python-headless`, `--platform linux/amd64`) và **pipeline build image có cache** (§9.3).
7. **Test**: unit (heatmap, contract 93 cột) + smoke test API.
8. **CI (GitHub Actions)**: PR → lint + test + build image (không push).
9. **IaC (Terraform)**: Artifact Registry, Cloud Run, IAM, Workload Identity Federation, Budget.
10. **CD**: merge `main` → build → push → **deploy revision mới** → smoke test → **chuyển traffic**; production cần **approval thủ công**.
11. **Rollback** = chuyển traffic về revision trước (vài giây).
12. **Observability**: Cloud Logging + alert lỗi 5xx.

### 6.2. NGOÀI phạm vi (ghi rõ để không kỳ vọng nhầm)

- Real-time streaming webcam (WebSocket/WebRTC).
- Đăng nhập / phân quyền / multi-user.
- Retrain model, sửa `range(1,51)`, cải thiện độ chính xác.
- Nhận diện từ/câu (chỉ **1 ký tự**).
- Mobile app, multi-region, auto-scaling phức tạp.
- CI/CD cho việc train model (MLOps).
- **Cloud Load Balancer, Cloud CDN, Cloud NAT, `min-instances=1`** — mọi thứ phá vỡ ràng buộc $0.

---

## 7. PHÂN CÔNG 4 NGƯỜI

| Vai | Mã | Trách nhiệm chính | Sản phẩm bàn giao |
|---|---|---|---|
| **Backend / ML** | **P1** | Tách inference thành package; FastAPI; pipeline ảnh + MediaPipe server-side; chuyển ONNX | `src/vsl/*.py`, `service/`, test |
| **Frontend / Web** | **P2** | Trang tĩnh (tải/chụp ảnh, hiển thị kết quả); **Cloudflare Pages**; CORS; warm-up ping | `web/`, pipeline frontend |
| **Platform / DevOps** | **P3** | Terraform (Cloud Run, Artifact Registry, IAM, WIF); Billing Budget; chi phí | `infra/`, dự án GCP chạy được |
| **CI/CD / QA** | **P4** | GitHub Actions; branch protection; smoke test; revision/traffic + rollback; docs | `.github/workflows/`, runbook |

**Nguyên tắc phối hợp:**
- P1 và P2 **chốt contract API Ngày 1** (§5.5) để làm song song.
- P3 và P4 **ghép cặp** ở Tuần 2 vì CI/CD và IaC phụ thuộc lẫn nhau.
- Standup 15 phút/ngày: hôm qua / hôm nay / đang chặn gì.

---

## 8. KẾ HOẠCH 10 NGÀY

### Ngày 0 (TRƯỚC Ngày 1) — việc chặn, làm song song được ngay

| Việc | Người | Ghi chú |
|---|---|---|
| **Tạo tài khoản Google Cloud + dự án** | PO + P3 | **Chặn cứng toàn bộ Tuần 2** |
| Bật **Billing Budget 1 USD** + MFA | P3 | Xong **trước** khi deploy bất cứ gì |
| Cài `docker`, `gcloud` CLI, `terraform`, `gh` | cả nhóm | Hiện **chưa có** |
| Tạo `.venv` Python 3.12 + `pip install -r requirements.txt` | P1 | Xác minh tổ hợp đã pin |

### TUẦN 1 — Tạo artifact có thể deploy

| Ngày | P1 (Backend/ML) | P2 (Frontend) | P3 (Platform) | P4 (CI/CD & QA) | Cột mốc |
|---|---|---|---|---|---|
| **D1** | Chốt contract API; `.venv`; tạo `src/vsl/` | Chốt UI flow; khởi tạo `web/` | Tạo dự án GCP; Terraform skeleton + state | Dọn nhánh: chốt `main`, xoá `master`, branch protection | **Contract API ký chốt** |
| **D2** | Gộp `create_heatmap` + `VIETNAMESE_ALPHABET` thành 1 bản; bỏ hard-code path | Trang tĩnh: form tải/chụp ảnh | Terraform: Artifact Registry + IAM + WIF | CI PR: lint + test (numpy, **không cần TF**) | **Module dùng chung** |
| **D3** | FastAPI `/predict` nhận **ảnh** + MediaPipe Python server-side | Gọi API local; hiển thị kết quả | Terraform: Cloud Run service | Unit test heatmap + contract 93 cột | **Pipeline ảnh chạy server-side** |
| **D4** | Dockerfile Linux **multi-stage**, `opencv-headless`, `--platform linux/amd64` | Xử lý `no_hand`/`no_face`, trạng thái loading | Terraform: Cloud Run + `min-instances=0` | CI: build Docker image **có cache** | **`docker run` chạy được** |
| **D5** | Đo cold start thực tế; ghi nhận baseline | Kết nối UI ↔ API; **thêm warm-up ping khi tải trang** | `terraform apply` + deploy thủ công lần đầu | Smoke test script | **🎯 Service chạy trên Cloud Run (staging)** |

### TUẦN 2 — Tự động hoá deploy

| Ngày | P1 (Backend/ML) | P2 (Frontend) | P3 (Platform) | P4 (CI/CD & QA) | Cột mốc |
|---|---|---|---|---|---|
| **D6** | **Chuyển `.h5` → `.onnx`** + parity test Keras vs ONNX | Tạo dự án **Cloudflare Pages**; deploy thủ công bằng `wrangler` lần đầu | Terraform: tách staging/prod | CD backend staging: build + push + deploy revision | **CD backend staging tự động** |
| **D7** | So sánh cold start TF vs ONNX; chốt runtime | **CORS**, tên miền, HTTPS, xử lý lỗi mạng | IAM: GitHub Actions dùng **WIF** (bỏ key) | **Pipeline frontend**: preview deploy mỗi PR + CD production; smoke test sau deploy | **Cả 2 pipeline chạy; không còn key tĩnh cho GCP** |
| **D8** | Tài liệu API; hỗ trợ điều tra lỗi | Kiểm thử end-to-end trình duyệt | Terraform: môi trường **production** | CD prod + **manual approval** | **Prod deploy có duyệt** |
| **D9** | Runbook backend | UAT giao diện | Cloud Logging alert 5xx + Budget check | **Diễn tập rollback bằng traffic split**; tag `v1.0.0` | **Rollback chạy được** |
| **D10** | Cập nhật `AGENTS.md` | Quay demo | Rà soát chi phí, xác nhận $0 | Viết `README` deploy; retro; backlog | **🎯 Demo cuối + bàn giao** |

### Đường găng

```
tài khoản GCP (D0) ─┐
contract (D1) → module (D2) → API ảnh (D3) → Dockerfile (D4) → Cloud Run (D5)
   → CD (D6–D7) → approval (D8) → rollback (D9) → demo (D10)
```

**Ưu tiên cắt khi trễ:** ONNX (D6) là thứ **cắt được đầu tiên** — giữ TensorFlow vẫn chạy. Không được cắt: module dùng chung (D2), API (D3), Dockerfile (D4).

---

## 9. THIẾT KẾ CI/CD CHI TIẾT

### 9.1. CI (mọi Pull Request)

```
PR mở
 ├─ 1. Lint               (ruff)                         ~10s
 ├─ 2. Format check       (black --check)                ~5s
 ├─ 3. Unit test heatmap  (pytest, numpy — KHÔNG cần TF)  ~30s
 ├─ 4. Contract test      (đúng 93 cột, đúng thứ tự)     ~5s
 ├─ 5. Docker build       (chỉ build, KHÔNG push)        ~3-5 ph
 └─ 6. Chặn merge nếu đỏ
```

> **Quan trọng:** tách `create_heatmap` thành module **thuần numpy** để test nhanh, không phải cài TensorFlow. Test cần TF/ONNX chỉ chạy trên `main`.

### 9.2. CD (merge vào `main`)

```
merge vào main
 ├─ Chạy lại toàn bộ CI
 ├─ Build image → tag = <git-sha>        (KHÔNG dùng :latest)
 ├─ Push Artifact Registry
 ├─ Deploy REVISION MỚI lên Cloud Run  (CHƯA nhận traffic)
 ├─ Smoke test trực tiếp revision mới (qua tag URL của revision)
 ├─ Chuyển traffic STAGING → 100% revision mới (tự động)
 └─ ⏸  CHỜ DUYỆT THỦ CÔNG (GitHub Environment: production)
      └─ Chuyển traffic PRODUCTION → revision mới
           ├─ Smoke test production
           └─ Nếu fail → chuyển traffic về revision trước NGAY
```

### 9.3. Đóng gói image Docker (build)

**✅ Đã chốt: build bằng GitHub Actions**, dùng `docker/build-push-action` với buildx. Cloud Build chỉ là phương án dự phòng.

| | **GitHub Actions** ✅ *chọn* | Cloud Build *(dự phòng)* |
|---|---|---|
| Nơi build | Runner của GitHub | Hạ tầng Google |
| Push lên Artifact Registry | Qua Internet — chậm hơn với image 700 MB–2,3 GB | Nội bộ Google — nhanh hơn nhiều |
| Cache layer | `type=gha` (GitHub Actions cache) | Layer cache sẵn có |
| Định mức miễn phí | Miễn phí với repo công khai; 2.000 phút/tháng với repo riêng | ⚠️ ~120 phút build/ngày |
| Bí mật | WIF | WIF |
| **Lý do chọn** | Giữ **toàn bộ pipeline ở một nơi** — dễ học, dễ gỡ lỗi | Chỉ chuyển nếu push qua Internet thành nút cổ chai |

**Checklist Dockerfile — bắt buộc:**

| # | Yêu cầu | Lý do |
|---|---|---|
| 1 | **Multi-stage build**: stage `builder` cài build-deps và `pip install` vào venv; stage runtime chỉ copy venv | Loại trình biên dịch và header khỏi image cuối |
| 2 | **Ghim base image bằng digest** — `FROM python:3.12-slim@sha256:...` | Thẻ `python:3.12-slim` có thể đổi nội dung bất kỳ lúc nào ⇒ build không tái lập |
| 3 | **`--platform linux/amd64`** bắt buộc | Cloud Run **không nhận image arm64**; lỗi này chỉ lộ ra ở bước deploy |
| 4 | **Thứ tự COPY**: `requirements.txt` → `pip install` → model → source | Để sửa mã nguồn **không** kích hoạt cài lại toàn bộ phụ thuộc |
| 5 | **Non-root user** | Giảm thiệt hại nếu container bị chiếm quyền |
| 6 | **`.dockerignore`** loại `.git`, `data/`, `*.ipynb`, `.venv/` | Build context 135 MB (chủ yếu CSV + LFS) sẽ bị đẩy lên runner **mỗi lần build** |
| 7 | **HEALTHCHECK** trỏ `/health` | Đồng bộ với healthcheck của Cloud Run |

**Cache là bắt buộc, không phải tuỳ chọn:**

```yaml
- uses: docker/build-push-action@v6
  with:
    platforms: linux/amd64
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

Không có cache, **mỗi lần CI chạy đều trả giá 3–5 phút cài TensorFlow** — và pipeline sẽ bị tránh sử dụng vì quá chậm.

**Số đo bắt buộc mỗi lần build:** ghi lại **kích thước image** và **thời gian build** vào log CI. Mục tiêu: **≤ 1 GB** khi dùng ONNX; nếu giữ TensorFlow thì ghi nhận thực tế ~2,3 GB.

> **Quét lỗ hổng bảo mật (SHOULD — chưa chốt):** thêm Trivy ở chế độ **chỉ báo cáo** (`exit-code: 0`), không chặn pipeline. Lý do: image TensorFlow thường chứa nhiều CVE và nếu bật chặn ngay từ đầu thì CI sẽ đỏ liên tục, làm mất tác dụng của cổng chặn chất lượng.

### 9.4. Pipeline frontend (Cloudflare Pages)

Đây là pipeline thứ hai — phần dạy được nhiều nhất về CI/CD (xem [ADR-001](ADR-001-frontend-hosting.md) §4.3).

```
PR mở  (CHỈ chạy khi có thay đổi trong web/**)
 ├─ Deploy PREVIEW  → wrangler pages deploy web/ --branch=<tên-nhánh>
 ├─ Lấy URL preview → comment tự động vào PR
 └─ Người review bấm URL để DÙNG THỬ trước khi merge

merge vào main  (CHỈ chạy khi có thay đổi trong web/**)
 ├─ Deploy PRODUCTION → wrangler pages deploy web/ --branch=main
 └─ Smoke test: tải trang + kiểm tra warm-up ping trả 200
```

```yaml
# Preview cho mỗi PR
- run: npx wrangler pages deploy web/ --project-name=vsl-frontend --branch=${{ github.head_ref }}
  env:
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
```

**Ba điểm cần chú ý:**

| Điểm | Chi tiết |
|---|---|
| **Trigger theo đường dẫn** | Dùng `paths: ['web/**']` để **không** deploy frontend khi chỉ đổi backend. Đây là khái niệm CI/CD mà pipeline một-target không dạy được. |
| **⚠️ Cloudflare dùng token tĩnh** | Khác với GCP (đã dùng WIF, không key). Cloudflare buộc dùng API token. **Giảm thiểu: tạo token chỉ có quyền `Pages:Edit` trên đúng 1 tài khoản** — đây là quyền hẹp hơn nhiều so với một key cloud. Ghi rõ vào runbook. |
| **Rollback** | Cloudflare Pages có tính năng rollback về deployment trước — **không cần build lại**. |

> **Thứ tự deploy (MT-3):** backend **luôn** deploy trước frontend. Backend tương thích ngược; frontend là bên thích nghi.

### 9.5. Nguyên tắc bắt buộc

| Nguyên tắc | Lý do |
|---|---|
| **Tag image = git SHA**, không `latest` | Truy vết được |
| **Deploy revision mới TRƯỚC, chuyển traffic SAU** | Smoke test trên revision mới mà **không ảnh hưởng người dùng** — lợi thế lớn của Cloud Run |
| **Rollback = chuyển traffic về revision trước** | Vài giây, không build lại |
| **Xác thực GCP bằng Workload Identity Federation** | Không có service account key để rò rỉ |
| **Token Cloudflare giới hạn quyền `Pages:Edit`** | Cloudflare buộc dùng token tĩnh; giới hạn quyền để thu hẹp thiệt hại nếu rò rỉ |
| **`min-instances = 0`** | Bắt buộc để giữ $0 — xem §2.3 |
| **`max-instances` thấp (2–3)** | Chặn leo thang chi phí nếu bị tấn công |
| **Artifact Registry lifecycle: giữ 3 image** | Không vượt 0,5 GB free |
| **Ghim base image bằng digest + `--platform linux/amd64`** | Build tái lập được; tránh lỗi image arm64 bị Cloud Run từ chối |
| **Cache layer cho `docker build` (`type=gha`)** | Không cache thì mỗi lần CI chạy mất thêm 3–5 phút cài TensorFlow |
| **Ghi lại kích thước image và thời gian build mỗi lần** | Không đo thì không biết image có phình ra theo thời gian hay không |
| **Smoke test sau mỗi deploy** | Phát hiện hỏng ngay |
| **Billing Budget 1 USD** | Bảo vệ ràng buộc $0 |

### 9.6. Quản lý model 130 MB

| Cách | Ưu | Nhược | Quyết định |
|---|---|---|---|
| **ONNX/TF, bake vào image** | Không gọi mạng; cold start nhanh; đơn giản | Mỗi lần đổi model phải build lại | ✅ **Chọn cho MVP** |
| Tải từ Cloud Storage lúc cold start | Đổi model không cần build | Cold start chậm hơn; cần retry | Giai đoạn 2 |
| Model Registry / GCS có versioning | Chuẩn MLOps | Thừa cho 2 tuần | Backlog |

---

## 10. TIÊU CHÍ NGHIỆM THU (Definition of Done)

- [ ] **DoD-1** — Có URL công khai; người ngoài nhóm mở được và nhận dự đoán từ 1 ảnh.
- [ ] **DoD-2** — Không còn đường dẫn `D:\` nào trong code.
- [ ] **DoD-3** — `create_heatmap` chỉ tồn tại **1 bản duy nhất**; train và inference cùng import.
- [ ] **DoD-4** — `VIETNAMESE_ALPHABET` chỉ tồn tại **1 bản duy nhất**.
- [ ] **DoD-5** — MediaPipe chạy **server-side bằng Python** (đúng thư viện lúc train) — kiểm chứng bằng test so với kết quả notebook.
- [ ] **DoD-6** — *(nếu làm ONNX)* Parity test Keras vs ONNX đạt, chênh lệch trong ngưỡng cho phép.
- [ ] **DoD-7** — Mở PR → CI tự chạy; CI đỏ thì **không merge được**.
- [ ] **DoD-8** — Merge `main` → tự động deploy staging, **không thao tác tay**.
- [ ] **DoD-9** — Deploy production cần **approval thủ công**.
- [ ] **DoD-10** — **Rollback đã diễn tập** bằng traffic split, hoàn thành < 5 phút.
- [ ] **DoD-11** — `/health` trả 200 và phản ánh đúng trạng thái model.
- [ ] **DoD-12** — Có alert Cloud Logging cho lỗi 5xx.
- [ ] **DoD-13** — CI **không chứa service account key** (dùng WIF).
- [ ] **DoD-14** — **Billing Budget đã bật**; hoá đơn tháng demo **< 1 USD**.
- [ ] **DoD-15** — **`min-instances = 0`** được xác nhận trong Terraform.
- [ ] **DoD-16** — Ghi lại **cold start thực đo** (TF và/hoặc ONNX).
- [ ] **DoD-17** — `README` hướng dẫn deploy + runbook xử lý sự cố.
- [ ] **DoD-18** — `AGENTS.md` được cập nhật theo cấu trúc mới.
- [ ] **DoD-19** — **Preview deploy mỗi PR hoạt động**; URL preview được **comment tự động vào PR**.
- [ ] **DoD-20** — Pipeline frontend **chỉ chạy khi `web/**` thay đổi** (không deploy frontend khi chỉ sửa backend).
- [ ] **DoD-21** — **Warm-up ping** có mặt và chạy ngay khi tải trang.
- [ ] **DoD-22** — **Cloudflare API token chỉ có quyền `Pages:Edit`** trên đúng 1 tài khoản; token được ghi rõ trong runbook.
- [ ] **DoD-23** — **Rollback frontend** đã diễn tập (Cloudflare Pages rollback về deployment trước).
- [ ] **DoD-24** — Image build trong CI **có cache layer** (`type=gha`); **thời gian build được ghi lại** mỗi lần chạy.
- [ ] **DoD-25** — Dockerfile dùng **multi-stage**; base image **ghim bằng digest**; build chỉ định **`--platform linux/amd64`**.
- [ ] **DoD-26** — **Kích thước image được đo và ghi lại**; đạt **≤ 1 GB** nếu dùng ONNX (hoặc ghi nhận thực tế nếu giữ TensorFlow).
- [ ] **DoD-27** — *(SHOULD — chưa chốt)* Image được **quét lỗ hổng** ở chế độ chỉ báo cáo, không chặn pipeline.

---

## 11. VIỆC CẦN LÀM TIẾP NGAY

### 11.1. Chặn cứng — phải xong trước Ngày 1

| # | Việc | Ai | Vì sao chặn |
|---|---|---|---|
| **B1** | **Tạo tài khoản Google Cloud + dự án mới** | PO + P3 | **Không có tài khoản = không deploy được gì** |
| **B2** | Bật **Billing Budget 1 USD** + MFA | P3 | Bảo vệ ràng buộc $0 |
| **B3** | Cài `docker`, `gcloud` CLI, `terraform`, `gh`, **Node.js** (cho `npx wrangler`) | cả nhóm | Không có thì không build/deploy được |
| **B4** | **Tạo tài khoản Cloudflare + dự án Pages**; tạo **API token chỉ có quyền `Pages:Edit`** | P2 + P4 | Không có thì không deploy frontend được; token phải hẹp quyền ngay từ đầu (DoD-22) |

### 11.2. Cần bạn (PO) quyết

| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| ~~Q1~~ | ✅ **Đã chốt: Cloudflare Pages** (backend Google Cloud Run) — xem [ADR-001](ADR-001-frontend-hosting.md) | Đã chốt, có đầu việc cho P2 và P4 |
| **Q2** | Chấp nhận **cold start ~5 s** (có ONNX) hoặc **~20 s** (giữ TensorFlow) ở request đầu không? | Nếu không chấp nhận → phải bật `min-instances=1` → **phá ràng buộc $0** |
| **Q3** | Có cần **tên miền riêng** không? | Cloudflare Pages và Vercel đều cho tên miền + SSL **miễn phí**; Cloud Run cần LB (~18 USD/tháng) → tránh |
| **Q4** | Model có cần cải thiện độ chính xác trong 2 tuần này? | Có → **phải cắt** bớt CI/CD, không kịp cả hai |

### 11.3. Chuẩn bị kỹ thuật (làm được ngay, không cần tài khoản)

1. Tạo `.venv` Python 3.12 và cài `requirements.txt`; xác minh model nạp được.
2. Xoá nhánh `master`, giữ `main`, bật branch protection.
3. Tạo `src/vsl/`, chuyển `create_heatmap` + `VIETNAMESE_ALPHABET` vào đó.
4. **Đổi `opencv-python` → `opencv-python-headless`** trong requirements (§3.3).
5. Thêm `.gitignore` cho `.venv/`, `*.onnx`, artifact build.
6. Viết **test so sánh kết quả service với notebook** trên mẫu `1.csv` của 23 ký tự (đã biết kết quả đúng 23/23) — đây là lưới an toàn khi tách code.

---

## 12. BACKLOG GIAI ĐOẠN SAU (ngoài 2 tuần)

| Ưu tiên | Việc |
|---|---|
| Cao | Sửa `range(1,51)` → dùng đủ 1609 mẫu; retrain; đo lại độ chính xác **trung thực** |
| Cao | Tạo test set thật: nhiều người, nhiều điều kiện sáng, tách theo người quay |
| Cao | Sửa `np.eye(23)` → suy ra từ `len(VIETNAMESE_ALPHABET)` |
| Trung bình | Real-time streaming (WebSocket/WebRTC) |
| Trung bình | Lượng tử hoá model (int8) → giảm cold start, giảm dung lượng |
| Trung bình | Pipeline CI/CD riêng cho việc train model (MLOps) |
| Trung bình | Model registry + versioning trên Cloud Storage |
| Trung bình | Canary deploy thật bằng traffic split (5% → 100%) |
| Thấp | Nhận diện từ/câu thay vì từng ký tự |
| Thấp | Xác thực người dùng, rate limiting, chống lạm dụng API |

---

## 13. KẾT LUẬN CỦA PRODUCT OWNER

**Điểm tích cực:** model đã train xong, dữ liệu đầy đủ, logic inference đã chạy được, `requirements.txt` đã có tổ hợp kiểm chứng, và **kết quả trên mẫu train đã được xác nhận 23/23 đúng**. Phần khó nhất của ML đã xong.

**Việc chọn Cloud Run là một quyết định tốt, không chỉ là đổi nhà cung cấp.** Nó xoá rủi ro nguy hiểm nhất (R-1 — landmark lệch khiến model dự đoán sai âm thầm) bằng cách cho phép chạy **đúng thư viện MediaPipe Python như lúc train**, đồng thời hạ cấp rủi ro ONNX từ "có thể phá hỏng kiến trúc" xuống "tối ưu hoá tuỳ chọn". Kèm theo đó, **API contract đơn giản hơn** — chỉ còn "gửi ảnh", thay vì phải bảo vệ một hợp đồng 93 số float.

**Cloud Run cũng cho rollback tốt hơn:** deploy revision mới → smoke test → **mới chuyển traffic**. Người dùng không bao giờ chạm vào revision chưa kiểm chứng. Đây là điều Lambda alias không làm được sạch sẽ bằng.

**Ba rủi ro phải xử lý sớm, không để tới Tuần 2:**

1. **R-6 — chưa có tài khoản Google Cloud.** Việc **chặn cứng** duy nhất. Làm ngay vì xác minh tài khoản có thể mất vài giờ tới vài ngày.
2. **R-2 — cold start.** Vì **không được phép** bật `min-instances=1` (§2.3), cold start là thứ người dùng **luôn** gặp. Hãy **đo thực tế ở Ngày 5** và quyết định ONNX dựa trên số liệu, không dựa trên phỏng đoán.
3. **R-3 — vượt free tier âm thầm.** Bật Billing Budget **trước** khi deploy bất cứ thứ gì.

**Ngăn xếp đã chốt:** backend **Google Cloud Run** + frontend **Cloudflare Pages**, cả hai trong free tier, tổng chi phí mục tiêu **< 1 USD/tháng**.

**Việc quan trọng nhất cần làm ngay:**

1. **Tạo tài khoản Google Cloud + dự án** (B1) — và **bật Billing Budget 1 USD ngay sau đó** (B2).
2. **Tạo tài khoản Cloudflare + dự án Pages + API token hẹp quyền** (B4) — làm song song được, không cần chờ GCP.
3. **Trong lúc chờ tài khoản:** tạo `.venv`, tách `src/vsl/`, viết test so sánh service với notebook (đã biết đáp án 23/23). Đây là cách dùng thời gian chờ hiệu quả nhất và cũng là lưới an toàn cho toàn bộ việc tách code.

**Nếu buộc phải cắt:** xem §8 — cắt ONNX trước, rồi tới frontend riêng (gộp vào container). **Không được cắt** module dùng chung, API ảnh, và Dockerfile.
