# AGENTS.md — Sign-Language-Classification-v1.0

Bộ nhớ dự án cho agent. Đọc file này trước khi sửa code.
**Cập nhật lần cuối: 2026-10-19** — toàn bộ dữ kiện dưới đây được đo/đọc trực tiếp
từ repo trong phiên đó, không suy đoán. Nếu bạn phát hiện file này lệch với thực tế,
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

Mã nguồn hiện tại = **3 notebook + 1 script Python**. Không có test, không CI,
không Dockerfile, không backend, không hạ tầng.

---

## 2. Git — trạng thái thực tế

| Mục | Giá trị (đo 2026-10-19) |
|---|---|
| Remote `origin` | `https://github.com/courseprojectICTU/Sign-Language-Classification.git` (fetch = push) |
| `origin/HEAD` | → `origin/develop` |
| Nhánh local | `main`, `develop`, `feature/US-001` (đang checkout) |
| `main` | `3d64e9d` "first commit" — bằng `develop` |
| `develop` | `3d64e9d` "first commit" |
| `feature/US-001` | `d74051f` "update 1" (2026-10-18 13:45:36 +07:00) — đi trước `develop` 2 commit, **nhưng chỉ khác `README.md`** |
| Commit giữa | `0a41b70` "update" — cũng chỉ sửa `README.md` (1 dòng) |
| Nội dung 3 commit | `3d64e9d` "first commit" chứa **toàn bộ** repo (1609 CSV, 3 notebook, `docs/`, `run_realtime.py`, AGENTS.md cũ). 2 commit sau chỉ sửa `README.md`. **Không có code nào khác giữa `develop` và `feature/US-001`.** |
| Tổng số commit | **3** (`git rev-list --all --count`) |
| Tag | không có |
| CI config | không có (`.github/` không tồn tại) |
| LFS | `git-lfs/3.7.0`; `.gitattributes` chỉ có `*.h5 filter=lfs` |
| `train/vsl_cnn_pose_keras.h5` | **file thật 137.042.364 bytes** (LFS đã smudge, không phải pointer) |
| Dung lượng working tree (trừ `.venv`, `.git`) | ~135,2 MB |

**Working tree đang dirty (2 file, chưa commit):**
- `README.md` — sửa tiêu đề `v100` → `v1.0`
- `AGENTS.md` — chính lần cập nhật này

Đối chiếu blob 3 CSV mẫu (`a/1.csv`, `b/50.csv`, `y/70.csv`): **khớp HEAD**. Ba file
này không đổi. (`git diff-index` lại báo cả 1609 CSV là `M` — xem 2.1, đừng tin.)

### 2.1. BẪY: `git status` và `git diff` HỎNG trên máy này

`git status`, và đôi khi `git diff` trên nhiều file, chết bằng:

```
sh.exe: *** fatal error - NtCreateDirectoryObject(\BaseNamedObjects\msys-2.0S5-...): 0xC0000022
fatal: the remote end hung up unexpectedly
```

Đây là **sandbox chặn MSYS tạo named object** (cùng họ với mục 12), **không phải**
repo hỏng, **không phải** lỗi mạng. Đừng "sửa" bằng cách xóa `.git/index` hay
re-init repo.

**Lệnh chạy được:** `git remote -v`, `git log`, `git branch -vv`, `git ls-files`,
`git rev-parse`, `git hash-object`, `git config`, `git --no-pager diff --numstat HEAD -- <file>`.

**Bẫy mạng — `git fetch` / `ls-remote` chết ở tầng TLS:**

```
fatal: unable to access '...': schannel: AcquireCredentialsHandle failed:
SEC_E_NO_CREDENTIALS (0x8009030E) - No credentials are available in the security package
```

Sandbox không cho tiến trình truy cập credential store của Windows. Repo **public** nên
không cần auth — chỉ cần đổi TLS backend sang OpenSSL (đã kiểm chứng 2026-10-19):

```powershell
git -c http.sslBackend=openssl fetch --prune --tags origin
git -c http.sslBackend=openssl ls-remote --heads origin
```

Đừng kết luận "mất mạng" hay "sai token" khi thấy lỗi schannel.

**Bẫy phụ — đừng tin `git diff-index`:** `git diff-index --name-status HEAD` trên
máy này liệt kê **toàn bộ** file (kể cả 1609 CSV) là `M`, vì index stat cache bị
stale sau khi copy/checkout. Nó so stat, không so nội dung. Muốn biết file có thật
sự đổi, dùng:

```powershell
git hash-object <file>; git rev-parse "HEAD:<file>"   # bằng nhau = không đổi
```

---

## 3. Cấu trúc

```
data/anphabet/<ký tự>/*.csv     landmark thô, 1 file = 1 mẫu
process_images/capture_and_process_images.ipynb   thu thập dữ liệu (9 cell, 5 code)
train/train_cnn_pose_keras.ipynb                  huấn luyện (18 cell, 9 code)
train/vsl_cnn_pose_keras.h5                       model đã train (137.042.364 bytes, Git LFS)
train/training_plot_keras.png                     biểu đồ loss/accuracy
run_realtime.ipynb                                inference webcam qua Jupyter (8 cell, 4 code)
run_realtime.py                                   inference webcam native OpenCV (137 dòng)
run_realtime.cmd                                  launcher 1-click cho run_realtime.py
run_notebook.cmd                                  launcher Jupyter (bắt buộc, xem mục 12.1)
requirements.txt                                  deps đã pin, THUẦN ASCII (mục 10.1)
HUONG-DAN-CHAY.md                                 hướng dẫn chạy cho người dùng
AGENTS.md                                         file này
docs/ADR-001-frontend-hosting.md                  ADR chọn Cloudflare Pages
docs/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md            kế hoạch 2 tuần / 4 người
docs/product-backlog-cicd-2-tuan.xlsx             backlog (nhị phân, đừng đọc bằng read)
docs/WORKFLOW.md                                  quy trình bắt buộc cho mọi US
docs/api/README.md                                quy ước + 9 phase + checklist API docs
docs/api/_TEMPLATE.md                             bộ khung 17 mục cho mỗi api doc
docs/api/US-001.md                                hợp đồng API của US-001 (create_heatmap)
requirements-dev.txt                              pytest (dev-only, không cần cho runtime)
src/vsl/heatmap.py                                create_heatmap — BẢN DUY NHẤT (BR-002)
src/vsl/__init__.py                               re-export create_heatmap
tests/test_heatmap.py                             test US-001 (AC-001-01, AC-001-02 + biên)
tests/test_pipeline_baseline.py                   hồi quy 23/23 ký tự
tests/fixtures/heatmap_golden.npz                 golden reference (sinh từ notebook cũ)
tests/_generate_golden.py                         script sinh lại golden (không phải test)
.venv/                                            môi trường Python 3.12.7 đã sẵn sàng (~2,5 GB, gitignored)
```

**Điểm khác so với các bản mô tả cũ:** dự án **đã có file `.py`** (`run_realtime.py`).
Mọi câu "không có file .py" trong `docs/` là **sai ở thời điểm hiện tại**.

---

## 4. Hợp đồng dữ liệu (quan trọng nhất)

Mỗi CSV có **1 dòng header + 1 dòng dữ liệu**, **93 cột**, thứ tự cố định:

| Nhóm | Số cột | Chi tiết |
|---|---|---|
| `hand_{x,y,z}_{0..20}` | 63 | 21 landmark x 3, xen kẽ x,y,z theo từng điểm |
| `face_{x,y,z}_{idx}` | 30 | 10 điểm x 3, `idx` theo đúng thứ tự dưới đây |

`face_keypoints = [10, 152, 234, 454, 33, 263, 1, 61, 291, 199]`
(giống nhau ở cả 3 notebook và `run_realtime.py:100`)

- Giá trị là toạ độ **chuẩn hoá 0..1** của MediaPipe.
- Điểm thiếu (không thấy tay/mặt) được ghi `0.0` và bị `create_heatmap` **bỏ qua**
  khi `x == 0 and y == 0`.
- `df.values.flatten()` cho ra đúng chuỗi `x,y,z` xen kẽ — **trùng khớp** với thứ tự
  mà code inference dựng (`hand_landmarks + face_landmarks`). Đổi thứ tự cột là hỏng
  model mà không báo lỗi.

**Số mẫu thực tế (đếm trên đĩa = đếm trong git):** 23 thư mục, mỗi thư mục **70 CSV**,
riêng `đ` có **69** (thiếu `65.csv`). Tổng = **1609 mẫu**.

---

## 5. Các bẫy đã xác nhận — đọc trước khi sửa

1. **Dữ liệu bị bỏ quên:** `load_landmarks_data()` chỉ đọc `for i in range(1, 51)`
   (`train_cnn_pose_keras.ipynb`, cell load data) → **20 file cuối (51–70) của mọi
   ký tự bị bỏ qua**, dù đĩa có 70 file. Thực tế chỉ **1150/1609** mẫu được train.
   1150 = 23 x 50 chính xác vì `đ` chỉ thiếu `65.csv` (nằm ngoài khoảng 1–50).
2. **Đường dẫn tuyệt đối hard-code — nay chỉ còn 2 chỗ:**
   - `BASE_PATH` trong `capture_and_process_images.ipynb` (dòng ~75) — **còn hard-code**
   - `BASE_PATH` trong `train_cnn_pose_keras.ipynb` (dòng ~33) — **còn hard-code**
   - `MODEL_PATH` trong `run_realtime.ipynb` — **ĐÃ SỬA**: thử `train\vsl_cnn_pose_keras.h5`
     (tương đối) trước, chỉ fallback về đường dẫn tuyệt đối khi không thấy file.
   - `run_realtime.py` — dùng `os.path.dirname(__file__)` + fallback tuyệt đối.
   Tất cả đường dẫn tuyệt đối đều là `D:\file\project\Sign-Language-Classification-v1.0\...`,
   khớp đúng máy này. **Chúng sẽ vỡ trên Linux/container** — đây là P0 của kế hoạch deploy.
3. **`np.eye(23)` hard-code** trong notebook train. Thêm/bớt ký tự ở
   `VIETNAMESE_ALPHABET` mà quên sửa số này → lỗi one-hot.
4. **Cả hai đường inference yêu cầu `len(all_landmarks) == 93` chính xác**
   (`run_realtime.ipynb` dòng ~176, `run_realtime.py:109`). Thiếu tay (chỉ còn 30 cột
   mặt) hoặc thừa tay → **im lặng không dự đoán**. `run_realtime.py` có cải thiện nhỏ:
   hiển thị `Tay [OK/X] | Mat [OK/X]`; notebook thì không.
5. **`create_heatmap` nay chỉ còn MỘT bản** tại `src/vsl/heatmap.py` (US-001, commit
   `f83d787`). Trước đó có 3 bản: train notebook, run_realtime notebook, `run_realtime.py`.
   Công thức: `img_size=(224,224)`, `sigma=5`, kernel `range(-sigma*3, sigma*3+1)` = `-15..15`,
   cộng dồn, chia max, nhân 255, `np.stack([heatmap]*3, axis=2)`, **bỏ qua z**.
   Có guard `len(landmarks) % 3 != 0` → in cảnh báo + trả mảng 0 (giữ hành vi cũ).
   Sửa công thức chỉ cần sửa **một chỗ**; `tests/test_heatmap.py` chặn hồi quy bằng golden.
6. **`preprocess_input` của ResNet50** được áp sau khi heatmap đã ở dạng `uint8 0..255`.
   Đây là chuẩn hoá kiểu Caffe (trừ mean BGR), không phải `/255`. Đừng "sửa" thành
   `/255` — model đã học theo mean subtraction.
7. **Không bật `horizontal_flip`** trong `ImageDataGenerator`. Đây là **chủ ý đúng**:
   lật ngang biến ký hiệu tay này thành ký hiệu khác. Đừng bật.
   (Lưu ý khác: code inference ở **cả hai** đường dùng `cv2.flip(image, 1)` — coi
   gương khung hình. Đây là chủ ý, không phải bug.)
8. **`model.save('vsl_cnn_pose_keras.h5')` ghi vào thư mục làm việc hiện tại**, không
   phải vào `train/`. Chạy notebook từ thư mục khác sẽ tạo file ở sai chỗ.
9. **Đánh giá không lặp lại được:** `train_test_split` có `random_state=42` nhưng
   test set rất nhỏ (~115 mẫu) và chỉ có 1 dòng dữ liệu/tay/người quay.
10. **README sai 2 chỗ:** ghi "50 mẫu/ký tự" (đĩa có 70) và "độ chính xác 90%".
    Con số 90% **không phải** bằng chứng về khả năng tổng quát hoá.

---

## 6. Kiến trúc model (nguồn: `train_cnn_pose_keras.ipynb`)

```
ResNet50(weights='imagenet', include_top=False, input_shape=(224,224,3))
→ GlobalAveragePooling2D
→ Dense(256, relu)
→ Dense(23, softmax)
```

Train 2 giai đoạn:
1. Đóng băng toàn bộ ResNet50 — Adam `lr=1e-3`, 50 epochs.
2. Mở băng **10 layer cuối** — Adam `lr=1e-4`, 20 epochs.

Cả hai dùng `EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)`,
batch 32, loss `categorical_crossentropy`, split 80/10/10.

---

## 7. Thứ tự nhãn — nguồn chân lý duy nhất

```python
VIETNAMESE_ALPHABET = ['a','b','c','d','đ','e','g','h','i','k','l','m','n',
                       'o','p','q','r','s','t','u','v','x','y']
```

23 ký tự. **Không có** `f`, `j`, `w`, `z`. Có `đ`. Danh sách này lặp lại ở **4 nơi**:
3 notebook + `run_realtime.py:26`. Index chính là nhãn lớp. Sửa một chỗ phải sửa cả bốn.

`data/anphabet/` chứa đúng 23 thư mục khớp danh sách này.

---

## 8. Quy ước khi làm việc trong repo này

- Ưu tiên sửa **trực tiếp notebook** (JSON `.ipynb`); không tự ý tách thành `.py`
  trừ khi được yêu cầu. Nếu sửa logic inference, **cân nhắc sửa cả `run_realtime.py`**
  vì nó là đường chạy 1-click được khuyến nghị — đừng sửa notebook rồi bỏ quên nó.
- `train/vsl_cnn_pose_keras.h5` do **Git LFS** quản lý. Không commit lại file này
  bằng git thường.
- Khi thay đổi pipeline landmark, phải kiểm tra **cả 4 nơi** (capture → train →
  notebook realtime → `run_realtime.py`) vì không có hàm dùng chung nào.
- Repo ~135 MB, chủ yếu là `.h5` + 1609 CSV nhỏ.

---

## 9. Môi trường — trạng thái đã kiểm chứng

**Ràng buộc cứng (đã xác minh, không phải khuyến nghị):**

| Yêu cầu | Kết luận |
|---|---|
| Python | **3.12** — Python 3.13/3.14 **không có wheel TensorFlow** |
| mediapipe | **phải là 0.10.x** — từ 1.0.0 MediaPipe đã **xoá `mp.solutions`** |
| numpy | **1.26.4** (mediapipe 0.10.x ghim `<2`) |

Máy này: `conda` **không tồn tại**. Python khả dụng: `3.14.5` (mặc định) và
`3.12.7` tại `D:\program\python\python.exe`.

### 9.1. `.venv` của project — ĐÃ SẴN SÀNG, đừng cài lại

| Kiểm tra | Kết quả (2026-10-19) |
|---|---|
| `pyvenv.cfg` | `version = 3.12.7`, `home = D:\program\python` |
| Dung lượng | ~2,5 GB |
| Có mặt | `tensorflow`, `keras`, `mediapipe`, `cv2`, `numpy`, `pandas`, `sklearn`, `h5py`, `notebook`, `PIL`, `matplotlib` |
| Ghim trong `requirements.txt` | tf 2.19.1, keras 3.15.1, mediapipe 0.10.21, numpy 1.26.4, pandas 3.0.6, scikit-learn 1.9.1, h5py 3.16.0, protobuf 4.25.9, opencv(-contrib) 4.11.0.86, pillow 12.3.0, matplotlib 3.11.2, notebook 7.6.3, ipykernel 7.4.0 |

`.venv` được tạo bằng cách **copy `site-packages`** từ một venv 3.12.7 đã cài đủ,
**không** qua `pip install`, vì lý do ở mục 9.2.

**`.venv\Scripts\python.exe` từng bị lỗi DLL** (`0xc06d007e`, `_ctypes`/`cv2` load failed).
Kiểm chứng lại **2026-10-19**: đã chạy được `numpy`, `cv2`, `pytest` và **toàn bộ 10 test**
(10 passed). Nếu lỗi tái xuất hiện, dùng Python gốc + `.pth` như dưới đây.
Cách chữa đang giữ — **đừng xoá**:
1. `.pth` tại `D:\program\python\Lib\site-packages\vsl_project.pth` trỏ vào
   `.venv\Lib\site-packages` (đã tồn tại, nội dung đúng 1 dòng đường dẫn).
2. Kernel toàn cục `vsl_env` ("Python 3.12 (VSL)") đăng ký ở
   `%APPDATA%\jupyter\kernels\vsl_env` **và** `.jupyter-data\kernels\vsl_env`.
3. Launcher dùng Python gốc `D:\program\python\python.exe` + `PYTHONPATH` trỏ vào
   `.venv\Lib\site-packages` (xem `run_notebook.cmd`, `run_realtime.cmd`).

### 9.2. `pip install` quay resolver rất lâu (không phải treo mạng)

Triệu chứng: pip chạy hàng chục phút, **cache pip không tăng byte nào**,
`site-packages` vẫn trống, tiến trình python ngốn **~100% một nhân CPU**.
Phân biệt treo mạng vs resolver: đo CPU. Đã gặp thật: 30 phút, 0 byte tải về.
Xử lý: dừng pip, thử lại với `--only-binary=:all:`.

**Không chạy hai pip cùng lúc vào một `.venv`** — hai tiến trình cùng ghi
`site-packages` sẽ hỏng môi trường. Kiểm tra trước:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'pip install' } |
  Select-Object ProcessId, CreationDate, CommandLine
```

---

## 10. Môi trường soạn thảo file & các bẫy encoding

### 10.0. File này là UTF-8, `edit` dễ fail

File này là **UTF-8 không BOM** và chứa tiếng Việt. `Get-Content` mặc định trong
pwsh của phiên này **đọc sai** (ra mojibake), và do đó công cụ `edit` **không match
được** `old_string` chứa ký tự ngoài ASCII. Khi cần sửa:

- Dùng `write` để ghi lại toàn bộ, hoặc
- Đọc/kiểm tra bằng `read`, và chỉ `edit` trên các đoạn **thuần ASCII**.

Khi chạy Python in ra ký tự `đ` trên console Windows, phải đặt
`PYTHONIOENCODING=utf-8`, nếu không sẽ gặp `UnicodeEncodeError: 'charmap' codec`.

### 10.1. `requirements.txt` PHẢI là thuần ASCII

pip đọc file requirements bằng **encoding mặc định của hệ thống** (`cp1252` trên
Windows này), **không phải UTF-8**. Chú thích tiếng Việt trong file làm pip chết:

```
UnicodeDecodeError: 'charmap' codec can't decode byte 0x8d in position 251
```

Byte `0x8d` là một trong 5 byte không định nghĩa của cp1252, và nó xuất hiện tự
nhiên trong chuỗi UTF-8 tiếng Việt. **Giữ `requirements.txt` thuần ASCII.**
Giải thích tiếng Việt để ở `HUONG-DAN-CHAY.md`.

### 10.2. `.cmd`, không phải `.ps1`

`Get-ExecutionPolicy` trả `RemoteSigned`, nhưng PowerShell vẫn từ chối file `.ps1`
do agent tạo (`is not digitally signed`), dù **không** có Mark-of-the-Web.
File `.cmd`/`.bat` không chịu Execution Policy → dùng `.cmd` (đã kiểm chứng).

### 10.3. Git Bash khác PowerShell

Trong Git Bash, `\` là ký tự escape nên `.\.venv\Scripts\python.exe` bị ghép thành
`..venvScriptspython.exe` → `command not found`. Dùng dấu `/`:

```bash
./.venv/Scripts/python.exe -m notebook
```

### 10.4. Bẫy khi dọn tiến trình

Đừng kill tiến trình bằng bộ lọc khớp với chính câu lệnh đang chạy. Đã gặp thật:
`Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run_notebook' }`
khớp luôn shell đang thực thi lệnh đó → tự kill chính mình. Dùng
`taskkill /PID <pid> /T /F` theo PID cụ thể.

---

## 11. Cách chạy

### 11.1. Inference (nhanh nhất — model đã train sẵn)

```powershell
.\run_realtime.cmd          # khuyến nghị: native OpenCV, không qua Jupyter
# hoặc
py -3.12 run_realtime.py
# hoặc qua notebook
.\run_notebook.cmd          # rồi mở run_realtime.ipynb → Run All
```

Không cần train lại. Cần webcam; `run_realtime.py` thử camera index 0 rồi 1.
Nhấn `q` để dừng.

### 11.2. Training (chỉ khi muốn train lại)

Mở `train/train_cnn_pose_keras.ipynb`. Chậm trên CPU: ResNet50 x 224x224 x ~1150 ảnh,
50 + 20 epochs. Nên có GPU.

### 11.3. Thu thập dữ liệu

`process_images/capture_and_process_images.ipynb` — mở cửa sổ `cv2.imshow`, cần màn
hình thật; sửa `capture_for_letter('a')` thành chữ muốn quay; `NUM_SAMPLES_PER_FOLDER = 50`.
Output cũ còn sót trong notebook in ra `data\a\1.csv` — **rác**, hành vi hiện tại ghi
vào `data/anphabet/<chữ>/`.

### 11.4. Kernel của từng notebook — chỗ dễ mất thời gian

| Notebook | kernelspec | Trạng thái |
|---|---|---|
| `run_realtime.ipynb` | `vsl_env` / "Python 3.12 (VSL)" | ✅ đã đăng ký, chạy được |
| `train_cnn_pose_keras.ipynb` | **không có metadata kernelspec** | Jupyter dùng kernel mặc định (`python3`) — kiểm tra trước khi Run All |
| `capture_and_process_images.ipynb` | `mnist_project` / "Python (project1)" | ❌ **kernel không tồn tại trên máy** → Jupyter sẽ đòi chọn kernel |

---

## 12. `python.exe` BỊ GIỚI HẠN GHI trong workspace — hệ quả quan trọng

**Phát hiện then chốt (đã đo):** trên máy này, `python.exe` **chỉ ghi được file bên
trong thư mục project**. PowerShell thì ghi được mọi nơi. Cùng phiên, cùng user
`doant`, không elevated:

```
FAIL   C:\Users\doant\.jupyter            PermissionError [Errno 13]
FAIL   C:\Users\doant\AppData\Local\Temp  PermissionError [Errno 13]
FAIL   C:\Users\doant                     PermissionError [Errno 13]
OK     D:\file\project\Sign-Language-...  <-- chi workspace
```

Đã loại trừ: ACL hỏng (SDDL bình thường, `doant` FullControl), read-only,
Defender Controlled Folder Access (`EnableControlledFolderAccess = 0`), thiếu admin.
Đây là **confinement của môi trường**, không phải lỗi ACL hay cài đặt.

### 12.1. Hệ quả bắt buộc: Jupyter phải trỏ config vào workspace

Jupyter mặc định dùng `C:\Users\doant\.jupyter` → chết ngay:

```
PermissionError: [Errno 13] Permission denied: 'C:\Users\doant\.jupyter\migrated'
```

`run_notebook.cmd` set `JUPYTER_CONFIG_DIR`, `JUPYTER_DATA_DIR`, `JUPYTER_RUNTIME_DIR`
trỏ vào `.jupyter-config/`, `.jupyter-data/`, `.jupyter-runtime/` (đã gitignore) và
tạo thư mục nếu thiếu. **Luôn dùng nó thay cho `python -m notebook`.**

### 12.2. Cảnh báo cho mọi tác vụ Python khác

Bất kỳ thư viện nào ghi ra ngoài project sẽ hỏng theo cách khó hiểu: cache
HuggingFace, `~/.keras`, `~/.matplotlib`, `~/.cache`. Nếu gặp `PermissionError` với
đường dẫn trong `C:\Users\doant\...`, nguyên nhân gần như chắc chắn là cái này —
hãy trỏ biến môi trường tương ứng vào trong project, **đừng đi sửa ACL**.

---

## 13. `docs/` — kế hoạch nâng cấp, và phần đã lỗi thời

`docs/` mô tả kế hoạch **web hóa + CI/CD trong 2 tuần / 4 người** (soạn 2026-10-15,
vai trò Product Owner). Kiến trúc đã chốt:

| Thành phần | Quyết định |
|---|---|
| MVP | tải/chụp **1 ảnh** → trả ký tự (không realtime streaming) |
| Backend | **Google Cloud Run**, `min-instances = 0`, free tier (~0 USD) |
| Frontend | **Cloudflare Pages**, deploy bằng GitHub Actions + `wrangler` (ADR-001) |
| Nguyên tắc | MediaPipe + TensorFlow chạy **trên server**, trình duyệt chỉ gửi ảnh |

**Phần đã lỗi thời — đừng trích lại như sự thật hiện tại:**

| `docs/` ghi | Thực tế 2026-10-19 |
|---|---|
| "9 commit" | **3** commit |
| "nhánh `main` và `master` trùng nhau" | **không có nhánh `master`**; có `main`, `develop`, `feature/US-001` |
| "File `.py`: 0" | **1** file: `run_realtime.py` |
| "`.venv` chưa tạo" | **đã có**, 3.12.7, đủ package |
| "model 130,7 MiB" | đúng (137.042.364 bytes) |
| "1609 CSV / 23 thư mục" | đúng |

Phần **vẫn còn giá trị** trong `docs/`: ràng buộc free tier GCP, thiết kế CI/CD,
phân công, tiêu chí nghiệm thu.

---

## 14. Những gì dự án CHƯA có (đừng tìm, đừng giả định)

- ❌ Backend/API (không `app.py`, không FastAPI/Flask, không route `/predict`)
- ❌ `Dockerfile`, `.dockerignore`
- ❌ CI/CD (không `.github/workflows/`, không pipeline config)
- ❌ `gcloud`, `terraform`, `gh` CLI; `docker` CLI có nhưng **daemon chưa chạy**
- ❌ `scripts/`; `src/` mới có `vsl/heatmap.py` + `__init__.py`, chưa có package API
- ⚠️ Hàm dùng chung: `create_heatmap` đã tách (US-001); `VIETNAMESE_ALPHABET`
  **vẫn lặp 4 nơi** (US-002 sẽ xử lý)

**Đã có (đừng tìm nữa):** `tests/` + pytest 9.1.1 (10 test cho US-001),
`docs/api/` (khung + hợp đồng US-001), `requirements-dev.txt`.

Nếu task yêu cầu một trong những thứ trên, đó là **việc xây mới**, không phải "sửa".
