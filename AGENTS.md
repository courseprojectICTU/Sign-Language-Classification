# AGENTS.md — Sign-Language-Classification-v1.0

Bộ nhớ dự án cho agent. Đọc file này trước khi sửa code. Mọi dữ kiện dưới đây được
kiểm chứng trực tiếp từ repo (không suy đoán). Cập nhật file này khi phát hiện
sự thật mới hoặc khi sửa các "bẫy" được liệt kê.

## 1. Dự án là gì

Phân loại **bảng chữ cái ngôn ngữ ký hiệu tiếng Việt** (23 ký tự) từ webcam.
Pipeline: ảnh webcam → MediaPipe trích landmark bàn tay + mặt → sinh **heatmap
224x224x3** → CNN **ResNet50** → softmax 23 lớp.

Repo: `https://github.com/tpd05/Sign-Language-Classification-v1.0.git`
Toàn bộ code nằm trong **Jupyter Notebook** — không có file `.py`, không có test,
không có CI. `requirements.txt` đã được tạo lại (xem mục 9) vì README có nhắc tới
nhưng file gốc không tồn tại.

## 2. Cấu trúc

```
data/anphabet/<ký tự>/*.csv     landmark thô, 1 file = 1 mẫu
process_images/capture_and_process_images.ipynb   thu thập dữ liệu
train/train_cnn_pose_keras.ipynb                  huấn luyện
train/vsl_cnn_pose_keras.h5                       model đã train (130.7 MB, Git LFS)
train/training_plot_keras.png                     biểu đồ loss/accuracy
run_realtime.ipynb                                inference webcam
requirements.txt                                  deps đã pin (xem mục 9)
```

## 3. Hợp đồng dữ liệu (quan trọng nhất)

Mỗi CSV có **1 dòng header + 1 dòng dữ liệu**, **93 cột**, thứ tự cố định:

| Nhóm | Số cột | Chi tiết |
|---|---|---|
| `hand_{x,y,z}_{0..20}` | 63 | 21 landmark x 3, xen kẽ x,y,z theo từng điểm |
| `face_{x,y,z}_{idx}` | 30 | 10 điểm x 3, `idx` theo đúng thứ tự dưới đây |

`face_keypoints = [10, 152, 234, 454, 33, 263, 1, 61, 291, 199]`

- Giá trị là toạ độ **chuẩn hoá 0..1** của MediaPipe.
- Điểm thiếu (không thấy tay/mặt) được ghi `0.0` và bị `create_heatmap` **bỏ qua**
  khi `x == 0 and y == 0`.
- `df.values.flatten()` cho ra đúng chuỗi `x,y,z` xen kẽ — **trùng khớp** với thứ tự
  mà `run_realtime.ipynb` dựng (`hand_landmarks + face_landmarks`). Giữ nguyên
  quy ước này, đổi thứ tự cột là hỏng model mà không báo lỗi.

**Tổng số mẫu thực tế:** 23 thư mục, mỗi thư mục **70 CSV**, riêng `đ` có **69**
(thiếu `65.csv`). Tổng = 1609 mẫu.

## 4. Các bẫy đã xác nhận — đọc trước khi sửa

1. **Dữ liệu bị bỏ quên:** `load_landmarks_data()` chỉ đọc `for i in range(1, 51)`
   → **20 file cuối (51–70) của mọi ký tự bị bỏ qua**, dù đĩa có 70 file. Thực tế
   chỉ **1150/1609** mẫu được train. Con số 1150 = 23 x 50 chính xác vì `đ` chỉ thiếu
   `65.csv` (nằm ngoài khoảng 1–50). README ghi "50 mẫu/ký tự" — README **sai** so với
   dữ liệu trên đĩa.
2. **Đường dẫn tuyệt đối hard-code** ở 3 nơi, không portable:
   - `BASE_PATH` trong `capture_and_process_images.ipynb` và `train_cnn_pose_keras.ipynb`
   - `MODEL_PATH` trong `run_realtime.ipynb`
   Tất cả đều là `D:\file\project\Sign-Language-Classification-v1.0\...`.
   **Hiện khớp đúng máy này**, nên không cần sửa khi chạy tại chỗ.
3. **`np.eye(23)` hard-code** trong notebook train. Thêm/bớt ký tự ở
   `VIETNAMESE_ALPHABET` mà quên sửa số này → lỗi one-hot.
4. **`run_realtime.ipynb` yêu cầu `len(all_landmarks) == 93` chính xác.** Thiếu tay
   (chỉ còn 30 cột mặt) hoặc thừa tay → im lặng không dự đoán gì, không có cảnh báo.
5. **`create_heatmap` bị định nghĩa 2 lần** (train và realtime) với khác biệt: bản
   trong notebook train có kiểm tra `len(landmarks) % 3 != 0`, bản realtime **không**.
   Sửa công thức heatmap phải sửa **cả hai**, nếu không train/inference lệch nhau.
6. **`preprocess_input` của ResNet50** được áp sau khi heatmap đã ở dạng `uint8 0..255`.
   Đây là chuẩn hoá kiểu Caffe (trừ mean BGR), không phải `/255`. Đừng "sửa" thành
   `/255` — model đã học theo mean subtraction.
7. **Không bật `horizontal_flip`** trong `ImageDataGenerator`. Đây là **chủ ý đúng**:
   lật ngang biến ký hiệu tay này thành ký hiệu khác. Đừng bật.
8. **`model.save('vsl_cnn_pose_keras.h5')` ghi vào thư mục làm việc hiện tại**, không
   phải vào `train/`. Chạy notebook từ thư mục khác sẽ tạo file ở sai chỗ.
9. **Đánh giá không lặp lại được:** `train_test_split` có `random_state=42` nhưng
   test set rất nhỏ (~115 mẫu) và chỉ có 1 dòng dữ liệu/tay/người quay. Con số
   "90%" trong README **không phải** bằng chứng về khả năng tổng quát hoá.

## 5. Kiến trúc model (nguồn: `train_cnn_pose_keras.ipynb`)

```
ResNet50(weights='imagenet', include_top=False, input_shape=(224,224,3))
→ GlobalAveragePooling2D
→ Dense(256, relu)
→ Dense(23, softmax)
```

Heatmap: `img_size=(224,224)`, `sigma=5`, hạt nhân `-15..15`, Gaussian
`exp(-(j**2 + k**2) / (2 * sigma**2))`, cộng dồn (accumulate, không ghi đè), chia cho
max, nhân 255, `np.stack([heatmap]*3, axis=2)` → 3 kênh giống hệt nhau.

Lưu ý: `create_heatmap` lặp `for i in range(0, len(landmarks), 3)`, lấy `i` và `i+1`
làm `x, y` — **bỏ qua `z`**. Cao độ bàn tay (z) không được dùng ở bước sinh heatmap.

Train 2 giai đoạn:
1. Đóng băng toàn bộ ResNet50 — Adam `lr=1e-3`, 50 epochs.
2. Mở băng **10 layer cuối** — Adam `lr=1e-4`, 20 epochs.

Cả hai dùng `EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)`,
batch 32, loss `categorical_crossentropy`, split 80/10/10.

## 6. Thứ tự nhãn — nguồn chân lý duy nhất

```python
VIETNAMESE_ALPHABET = ['a','b','c','d','đ','e','g','h','i','k','l','m','n',
                       'o','p','q','r','s','t','u','v','x','y']
```

23 ký tự. **Không có** `f`, `j`, `w`, `z`. Có `đ`. Danh sách này lặp lại ở **cả 3
notebook** — sửa một chỗ phải sửa cả ba, và index chính là nhãn lớp.

`data/anphabet/` chứa đúng 23 thư mục khớp danh sách này.

## 7. Quy ước khi làm việc trong repo này

- Ưu tiên sửa **trực tiếp notebook** (JSON `.ipynb`); không tự ý tách thành `.py`
  trừ khi được yêu cầu.
- `train/vsl_cnn_pose_keras.h5` được **Git LFS** quản lý (xem `.gitattributes`).
  Không commit lại file này bằng git thường.
- Repo ~135 MB, chủ yếu là `.h5` (130.7 MB) + 1609 CSV nhỏ.
- Git history hiện chỉ có các lần sửa README — không có nhánh phát triển.
- Khi thay đổi pipeline landmark, phải kiểm tra **cả 3 notebook** cùng lúc
  (thu thập → train → realtime) vì không có hàm dùng chung nào.

## 8. Lưu ý về môi trường soạn thảo file

File này là **UTF-8 không BOM** và chứa tiếng Việt. `Get-Content` mặc định trong
pwsh của phiên này **đọc sai** (ra mojibake), và do đó công cụ `edit` cũng **không
match được** `old_string` chứa ký tự ngoài ASCII. Khi cần sửa file này:

- Dùng `write` để ghi lại toàn bộ, hoặc
- Đọc/kiểm tra bằng `read`, và chỉ `edit` trên các đoạn **thuần ASCII**.

Khi chạy Python in ra ký tự `đ` trên console Windows, phải đặt
`PYTHONIOENCODING=utf-8`, nếu không sẽ gặp `UnicodeEncodeError: 'charmap' codec`.

## 9. Cách chạy — đã kiểm chứng trên máy này

**Ràng buộc môi trường (đã xác minh, không phải phỏng đoán):**

| Yêu cầu | Kết luận |
|---|---|
| Python | **3.12** — Python 3.13/3.14 **không có wheel TensorFlow** |
| mediapipe | **phải là 0.10.x** — từ 1.0.0 MediaPipe đã **xoá `mp.solutions`** |
| numpy | **<2** (mediapipe 0.10.x ghim), đừng nâng lên 2.x |

Trạng thái máy này: `conda` **không tồn tại**; env `mnist_project` mà notebook
kernelspec trỏ tới (từng nằm ở `D:\anaconda3\envs\mnist_project`) **không có trên
máy**. Python khả dụng: `3.14.5` (mặc định) và `3.12.7` tại `D:\program\python\python.exe`.

**Tạo môi trường:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Chạy inference (nhanh nhất — model đã train sẵn):**

```powershell
.\run_notebook.cmd
# mở run_realtime.ipynb → Run All
```

Không cần train lại. `run_realtime.ipynb` tự nạp `train/vsl_cnn_pose_keras.h5`
(đường dẫn hard-code khớp đúng máy này). Cần webcam — máy này có camera ở index 0.

**Chạy training (chỉ khi muốn train lại):**

Mở `train/train_cnn_pose_keras.ipynb`. Chậm trên CPU: ResNet50 x 224x224 x ~1150 ảnh,
50 + 20 epochs. Nên có GPU.

**Thứ tự pipeline đầy đủ:**

1. `process_images/capture_and_process_images.ipynb` — thu thập (mở cửa sổ
   `cv2.imshow`, cần màn hình thật; sửa `capture_for_letter('a')` thành chữ muốn quay).
   Lưu ý cell này ghi vào `BASE_PATH` = `data/anphabet/<chữ>/`, nhưng output cũ trong
   notebook in ra `data\a\1.csv` (đường dẫn cũ trước khi có `anphabet`) — output đó
   là **rác còn sót**, không phải hành vi hiện tại.
2. `train/train_cnn_pose_keras.ipynb` — train, lưu `.h5`.
3. `run_realtime.ipynb` — chạy realtime.

**Kết quả kiểm chứng ngày 2026-10-15** (venv Python 3.12.7, TF 2.19.1, Keras 3.15.1,
mediapipe 0.10.21):

- `load_model('train/vsl_cnn_pose_keras.h5')` → OK, input `(None,224,224,3)`,
  output `(None,23)`. Model được lưu bằng Keras 2 nhưng **vẫn nạp được bằng Keras 3**.
- Toàn bộ pipeline heatmap + `preprocess_input` + predict trên mẫu `1.csv` của cả
  23 ký tự → **23/23 đúng**. Đây chỉ là sanity check trên chính mẫu train, **không
  phải** độ chính xác thực tế.
- 3 cell đầu của `run_realtime.ipynb` chạy trong kernel Jupyter thật → **0 lỗi**.
- `mp.solutions.hands` / `face_mesh` / `drawing_utils` đều tồn tại ở mediapipe 0.10.21;
  **biến mất hoàn toàn** ở mediapipe 1.1.1.

## 10. Môi trường `.venv` của project — trạng thái và các bẫy đã gặp

**Trạng thái: `.venv` trong project ĐÃ SẴN SÀNG dùng.** Đã kiểm chứng bên trong
chính `.venv` đó: Python 3.12.7, tensorflow 2.19.1, keras 3.15.1, mediapipe 0.10.21
(có `mp.solutions`), opencv 4.11.0, numpy 1.26.4, pandas 3.0.6, notebook 7.6.3.
`load_model('train/vsl_cnn_pose_keras.h5')` OK; test 23 ký tự trên mẫu `1.csv`
cho **23/23 đúng**. **Không cần chạy `pip install` lại.**

Nó được tạo bằng cách copy `site-packages` từ một venv Python 3.12.7 đã cài đủ
(cùng base `D:\program\python`), **không** qua `pip install`, vì lý do ở mục 10.2.

### 10.1. `requirements.txt` PHẢI là thuần ASCII

pip đọc file requirements bằng **encoding mặc định của hệ thống** (`cp1252` trên
Windows này), **không phải UTF-8**. Chú thích tiếng Việt trong file làm pip chết:

```
UnicodeDecodeError: 'charmap' codec can't decode byte 0x8d in position 251
```

Byte `0x8d` là một trong 5 byte không định nghĩa của cp1252, và nó xuất hiện tự
nhiên trong chuỗi UTF-8 tiếng Việt. **Giữ `requirements.txt` thuần ASCII.**
Giải thích tiếng Việt để ở `HUONG-DAN-CHAY.md`.

### 10.2. `pip install` quay resolver rất lâu (không phải treo mạng)

Triệu chứng: pip chạy hàng chục phút, **cache pip không tăng byte nào**,
`site-packages` vẫn trống, tiến trình python ngốn **~100% một nhân CPU**.

Cách phân biệt treo mạng vs resolver: đo CPU. Nếu cache đứng yên **và** CPU tăng
~30s trong 30s → resolver backtracking. Đã gặp thật: chạy 30 phút, 0 byte tải về.

Xử lý: dừng pip, thử lại với `--only-binary=:all:`.

### 10.3. Không chạy hai pip cùng lúc vào một `.venv`

Đã gặp thật: người dùng chạy `pip install -r requirements.txt` trong terminal
trong khi agent cũng chạy lệnh tương tự. Hai tiến trình cùng ghi `site-packages`
sẽ hỏng môi trường. Kiểm tra trước bằng:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'pip install' } |
  Select-Object ProcessId, CreationDate, CommandLine
```

### 10.4. Git Bash khác PowerShell

Trong Git Bash, `\` là ký tự escape nên `.\.venv\Scripts\python.exe` bị ghép thành
`..venvScriptspython.exe` → `command not found`. Dùng dấu `/`:

```bash
./.venv/Scripts/python.exe -m notebook
```

## 11. python.exe BỊ GIỚI HẠN GHI trong workspace — hệ quả quan trọng

**Phát hiện then chốt (đã đo, không suy đoán):** trên máy này, `python.exe` **chỉ ghi
được file bên trong thư mục project**. PowerShell thì ghi được mọi nơi.

Bản đồ ghi file đo trực tiếp từ cùng một phiên, cùng user `doant`, không elevated:

```
FAIL   C:\Users\doant\.jupyter            PermissionError [Errno 13]
FAIL   C:\Users\doant\AppData\Local\Temp  PermissionError [Errno 13]
FAIL   C:\Users\doant                     PermissionError [Errno 13]
OK     D:\file\project\Sign-Language-...  <-- chi workspace
```

**Đã loại trừ các nguyên nhân thường gặp:**

| Nghi ngờ | Bằng chứng | Kết quả |
|---|---|---|
| ACL hỏng | `(Get-Acl ...).Sddl` | Bình thường: `doant` FullControl kế thừa, owner `doant` |
| Read-only | `Attributes` | Chỉ `Directory` |
| Defender Controlled Folder Access | `Get-MpPreference` | `EnableControlledFolderAccess = 0`, danh sách trống |
| Thiếu quyền admin | `IsInRole(Administrator)` | `False` — tiến trình thường, không elevated |

Đây là **confinement của môi trường**, không phải lỗi ACL hay cài đặt.

### 11.1. Hệ quả bắt buộc: Jupyter phải trỏ config vào workspace

Jupyter mặc định dùng `C:\Users\doant\.jupyter` (ngoài vùng cho phép) → chết ngay:

```
PermissionError: [Errno 13] Permission denied: 'C:\Users\doant\.jupyter\migrated'
```

Đã tạo sẵn `run_notebook.cmd` để xử lý. **Luôn dùng nó thay cho `python -m notebook`:**

```powershell
.\run_notebook.cmd
```

Script set `JUPYTER_CONFIG_DIR`, `JUPYTER_DATA_DIR`, `JUPYTER_RUNTIME_DIR` trỏ vào
`.jupyter-config/`, `.jupyter-data/`, `.jupyter-runtime/` trong project (đã có trong
`.gitignore`). Đã kiểm chứng: Jupyter khởi động được (server trả HTTP, chỉ 403 vì
thiếu token — tức là đã chạy, không phải lỗi khởi động).

### 11.2. Cảnh báo cho mọi tác vụ Python khác

Bất kỳ thư viện Python nào ghi ra ngoài project sẽ hỏng theo cách khó hiểu. Ví dụ:
cache của HuggingFace, `~/.keras`, `~/.matplotlib`, `~/.cache`. Nếu gặp
`PermissionError` với đường dẫn trong `C:\Users\doant\...`, nguyên nhân gần như chắc
chắn là cái này — hãy trỏ biến môi trường tương ứng vào trong project, đừng đi sửa ACL.

### 11.3. Bẫy khi dọn tiến trình

Đừng kill tiến trình bằng bộ lọc khớp với chính câu lệnh đang chạy. Đã gặp thật:
`Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run_notebook' }`
khớp luôn shell đang thực thi lệnh đó → tự kill chính mình. Dùng `taskkill /PID <pid> /T /F`
theo PID cụ thể.

### 11.4. Vì sao launcher là `.cmd` chứ không phải `.ps1`

`Get-ExecutionPolicy` trên máy này trả `RemoteSigned` (scope `CurrentUser`), nhưng
PowerShell vẫn từ chối file `.ps1` do agent tạo:

```
.\run_notebook.ps1 : ... is not digitally signed.
You cannot run this script on the current system.
    + FullyQualifiedErrorId : UnauthorizedAccess
```

Đã kiểm tra: file **không** có Mark-of-the-Web (`Get-Item -Stream *` chỉ thấy `:$DATA`,
không có `Zone.Identifier`), nên không phải nguyên nhân "downloaded from internet".

**Kết luận thực dụng: dùng `.cmd`.** File `.cmd`/`.bat` không chịu sự chi phối của
PowerShell Execution Policy, nên chạy được ngay bằng `run_notebook.cmd` — đã kiểm chứng.

Nếu vẫn muốn dùng `.ps1`, phải gọi kèm cờ:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_notebook.ps1
```

### 11.5. Lỗi DLL Load Failed trên .venv\Scripts\python.exe va giai phap .pth

`.venv\Scripts\python.exe` tren Windows (venvlauncher stub) bi crash khi goi C extensions
(`_ctypes`, `cv2`, `_wmi` cua pandas) voi ma loi `0xc06d007e` va
`ImportError: DLL load failed while importing _ctypes: A dynamic link library (DLL) initialization routine failed.`

Giai phap da ap dung:
1. File `.pth` tai `D:\program\python\Lib\site-packages\vsl_project.pth` tro truc tiep vao
   `.venv\Lib\site-packages`. Nho do Python goc (`D:\program\python\python.exe`) nhan dien
   toan bo thu vien ma khong gap loi DLL.
2. Dang ky kernel toan cuc `Python 3.12 (VSL)` (`vsl_env`) cho ca Jupyter va VS Code / IDE.
3. Cung cap launcher 1-click `run_realtime.cmd` / `run_realtime.py` chay truc tiep native
   OpenCV khong can qua Jupyter.

