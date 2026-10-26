# QUY TRÌNH LÀM VIỆC — US → API Docs → AC → Task → Nghiệm thu

File này là **quy trình bắt buộc** cho mọi User Story trong dự án. Đọc lại file này
trước khi bắt đầu bất kỳ US nào. Nguồn dữ liệu gốc: `docs/product-backlog-cicd-2-tuan.xlsx`.

Cập nhật lần cuối: 2026-10-19 (bổ sung bước API Documentation + bộ khung `docs/api/`).

---

## 0. Nguyên tắc bất biến

1. **Không code trước test.** Acceptance Criteria được chuyển thành test **trước** khi
   viết code tính năng (trừ khi AC không thể test tự động — phải nêu rõ lý do).
2. **API-first.** Nếu US tạo ra tính năng hoặc API, **phải** có `docs/api/US-0XX.md`
   theo `docs/api/_TEMPLATE.md`, ở trạng thái `ANALYSIS_READY` và **đã được duyệt**,
   **trước khi** viết test hay code. Không có file đó = không được bắt đầu.
3. **Không gộp task.** Mỗi task = một thay đổi nhỏ, một commit riêng. Không làm 5 task
   trong 1 lần sửa.
4. **Commit thường xuyên, KHÔNG push.** Push là quyết định của chủ dự án, không tự push.
5. **Bám Business Rules.** Mỗi thay đổi phải chỉ ra BR nào đang được thoả (BR-001…BR-026).
6. **Không mở rộng phạm vi.** Chỉ sửa những gì US yêu cầu.
7. **Nghiệm thu cần chữ ký.** Test xanh **chưa phải** là xong — phải có xác nhận PASS
   của chủ dự án.
8. **Ghi lại bằng chứng.** Mọi báo cáo PASS/FAIL phải kèm output thật, không nói suông.

---

## 1. Bước 0 — Đồng bộ `develop` và tạo nhánh mới

**Luôn làm bước này TRƯỚC khi đọc code hay sửa bất cứ thứ gì.**

### 1.1. Quy ước đặt tên nhánh

| Loại việc | Tiền tố | Ví dụ |
|---|---|---|
| Tính năng theo User Story | `feature/` | `feature/US-001` |
| Sửa lỗi phát hiện trong US | `bugfix/` | `bugfix/US-006-93-columns` |
| Sửa gấp trên nhánh chính | `hotfix/` | `hotfix/cold-start-timeout` |
| Chỉ tài liệu | `docs/` | `docs/workflow` |
| Chỉ test | `test/` | `test/parity-baseline` |
| Việc lặt vặt (config, CI…) | `chore/` | `chore/gitattributes-eol` |

Quy tắc: **chữ thường, ASCII không dấu**, dùng đúng mã US khi có, tối đa ~50 ký tự.

### 1.2. Lệnh (máy này — có sandbox chặn `sh.exe`)

```powershell
# Tạo thư mục hooks rỗng (một lần) để git không spawn sh.exe
New-Item -ItemType Directory -Force .git\no-hooks | Out-Null

git -c http.sslBackend=openssl fetch --prune origin
git -c core.hooksPath=.git/no-hooks checkout develop
git -c core.hooksPath=.git/no-hooks merge --ff-only origin/develop
git -c core.hooksPath=.git/no-hooks checkout -b feature/US-00X
```

### 1.3. Lệnh (terminal bình thường của bạn)

```powershell
git fetch origin
git checkout develop
git pull --ff-only
git checkout -b feature/US-00X
```

### 1.4. Điều kiện qua bước

- `git rev-parse develop` == `git rev-parse origin/develop` (không lệch).
- Nhánh mới tạo từ `develop`, không phải từ nhánh cũ.
- Nếu `merge --ff-only` thất bại → **dừng lại**, báo chủ dự án (develop đã phân kỳ).

---

## 2. Bước 1 — Đọc US từ backlog

Đọc **4 sheet**, không chỉ sheet User Stories:

| Sheet | Lấy gì |
|---|---|
| `Product Backlog (User Stories)` | dòng có Story ID tương ứng: mô tả, precondition, postcondition, rule, dependency, story point |
| `Acceptance Criteria(TestCase)` | mọi AC có cùng Story ID |
| `Task(Công việc)` | mọi task có cùng Story ID |
| `Business Rules (Quy tắc)` | các BR được Story và AC tham chiếu |

Lệnh đọc (Python 3.14 mặc định đã có `openpyxl`):

```powershell
$env:PYTHONIOENCODING = "utf-8"
& "C:\Users\doant\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>
```

---

## 3. Bước 2 — Tóm tắt US cho chủ dự án  (CỔNG A)

Viết lại **ngắn gọn, dễ hiểu**, không dùng thuật ngữ thừa:

- Cần làm gì (2–5 gạch đầu dòng)
- Vì sao (giá trị nghiệp vụ, rủi ro nếu không làm)
- Phạm vi: cái gì **KHÔNG** làm
- Phụ thuộc: US/task nào phải xong trước
- Số AC và số task sẽ phải hoàn thành

**Dừng lại chờ chủ dự án xác nhận đúng ý** rồi mới đi tiếp.

---

## 4. Bước 3 — Phân tích Acceptance Criteria

Với **từng AC**, ghi rõ:

- AC ID + Severity (Critical/High/Medium)
- Given / When / Then → **test case cụ thể**
- Test data lấy từ đâu (file CSV nào, giá trị nào)
- Test tự động được hay phải kiểm thủ công
- Test sẽ nằm ở file nào (`tests/test_<us>_<chủ đề>.py`)

Đầu ra: **bảng AC → test** để chủ dự án duyệt.

---

## 5. Bước 4 — API Documentation  (CỔNG B — bắt buộc nếu US tạo tính năng hoặc API)

### 5.1. Điều kiện áp dụng

| US tạo ra gì | Bắt buộc `docs/api/US-0XX.md`? |
|---|---|
| Endpoint HTTP (`/health`, `/predict`, `/version`…) | ✅ Có |
| Hợp đồng request/response (JSON, mã lỗi) | ✅ Có |
| Hàm/module công khai dùng chung (VD `create_heatmap`) | ✅ Có |
| CLI, tham số dòng lệnh, định dạng file trao đổi | ✅ Có |
| Refactor thuần nội bộ, **không** đổi hợp đồng tiêu thụ | ❌ N/A + lý do, chờ chủ dự án xác nhận |

Nếu là `N/A`: báo rõ lý do trong báo cáo US, **không tự bỏ qua im lặng**.

### 5.2. Việc phải làm

1. Copy bộ khung: `docs/api/_TEMPLATE.md` → `docs/api/US-0XX.md`
2. Đi **đủ 17 mục** của template (mục không áp dụng ghi `N/A` + lý do, không xoá mục).
3. Làm đủ **9 phase** theo `docs/api/README.md` mục 4: Repository Discovery → Story
   Analysis → Domain → Existing API & Security → BR/AC → Gap Analysis → Design →
   Tạo file → Self-review.
4. Tự review theo checklist `docs/api/README.md` mục 5.
5. Đặt trạng thái cuối: `ANALYSIS_READY`, `NEEDS_CLARIFICATION` hoặc `BLOCKED`.

### 5.3. Điều cấm trong bước này

- **Không** sửa source code, không tạo endpoint, không viết test.
- **Không** bịa API/business rule; thiếu bằng chứng → ghi `UNKNOWN` / `CẦN XÁC NHẬN`.
- **Không** tạo endpoint trùng cái đã có (phải chứng minh bằng mục 4 Gap Analysis).

### 5.4. Điều kiện qua cổng

- `docs/api/US-0XX.md` **tồn tại**, đủ 17 mục, không rỗng.
- Trạng thái `ANALYSIS_READY` (hoặc chủ dự án chấp nhận `NEEDS_CLARIFICATION` đã trả lời).
- **Chủ dự án đã duyệt nội dung API.** Chưa duyệt = chưa được viết test.
- Commit riêng: `docs(api): them hop dong API cho US-0XX`

> US-001 (tách `create_heatmap`) có tạo hàm công khai dùng chung → **áp dụng bước này**:
> phải mô tả hợp đồng `create_heatmap(landmarks, img_size, sigma)` trước khi viết test.

---

## 6. Bước 5 — Viết test TRƯỚC khi code  (CỔNG C)

1. Đã có `docs/api/US-0XX.md` được duyệt (bước 4) — nếu chưa, **quay lại**.
2. Tạo test cho **toàn bộ** AC, đối chiếu cả Test Scenarios ở mục 14 của API docs.
3. Chạy test → phải **ĐỎ** (vì code chưa có). Nếu xanh ngay, nghĩa là test vô nghĩa
   hoặc tính năng đã tồn tại — phải báo lại.
4. Chỉ ra "lưới an toàn": với US tách code, baseline là **23/23 ký tự đúng** trên
   `data/anphabet/<chữ>/1.csv` (đã kiểm chứng 2026-10-19).
5. Commit riêng: `test(us-00X): ...`

Chỉ sau khi chủ dự án đồng ý danh sách test mới sang bước 6.

---

## 7. Bước 6 — Làm từng task, commit từng task

Lặp cho **mỗi** task trong sheet `Task(Công việc)`:

1. Nêu task ID + expected result (lấy nguyên văn từ backlog).
2. Chỉ ra BR liên quan và cách code thoả BR đó.
3. Sửa **tối thiểu** để task đó xong, bám đúng hợp đồng trong `docs/api/US-0XX.md`.
   Nếu code buộc phải lệch hợp đồng → **dừng lại**, cập nhật API docs trước.
4. Chạy test liên quan + test cũ (không được làm đỏ test cũ).
5. **Commit riêng**.
6. Báo chủ dự án: đã đổi file nào, vì sao, test nào xanh.

### 7.1. Quy ước commit

```
<type>(<scope>): <mô tả ngắn ở thể mệnh lệnh>

- vì sao (BR nào, AC nào)
- ảnh hưởng gì
```

`type`: `feat` | `fix` | `test` | `docs` | `refactor` | `chore`
`scope`: `us-001`, `us-002`…

Ví dụ: `feat(us-001): them module src/vsl/heatmap.py`

---

## 8. Bước 7 — Nghiệm thu  (CỔNG D)

1. Chạy **toàn bộ** test, không chỉ test của US.
2. Kiểm tra "build": import module, chạy pipeline thật, so baseline 23/23.
3. Đối chiếu lại `docs/api/US-0XX.md`: code có khớp hợp đồng đã duyệt không.
4. Báo cáo dạng bảng: AC ID → PASS/FAIL → bằng chứng (tên test + output).
5. **Chờ chủ dự án xác nhận PASS.** Chỉ khi có xác nhận mới coi là hoàn thành.
6. Nếu FAIL: sửa, commit tiếp, lặp lại bước này.

---

## 9. Lệnh chạy test chuẩn

Chạy từ **thư mục gốc project** (kiểm chứng 2026-10-19: 10 passed, ~24 s).

### 9.1. Lệnh chính

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

Python gốc cũng chạy được và tương đương (thấy `.venv\Lib\site-packages` nhờ
`vsl_project.pth`, **không cần** đặt `PYTHONPATH`):

```powershell
& "D:\program\python\python.exe" -m pytest tests -v
py -3.12 -m pytest tests -v
```

> Nếu `.venv\Scripts\python.exe` tái phát lỗi DLL `0xc06d007e`, dùng Python gốc ở trên.

### 9.2. Các biến thể hay dùng

| Mục đích | Lệnh |
|---|---|
| Chỉ test nhanh, bỏ test nạp model (~3 s) | `-m pytest tests -q -k "not 23_23"` |
| Chạy 1 file | `-m pytest tests/test_heatmap.py -v` |
| Chạy 1 test | `-m pytest "tests/test_heatmap.py::test_ac_001_01_chi_con_mot_dinh_nghia_tren_toan_repo" -v` |
| Dừng ngay ở lỗi đầu | `-m pytest tests -x` |
| Xem test nào thu thập được (không chạy) | `-m pytest tests --collect-only -q` |
| Chỉ hiện test hỏng + tóm tắt | `-m pytest tests -q` |

### 9.3. Điều kiện tiên quyết

`pytest` đã cài (9.1.1) và ghi trong `requirements-dev.txt`. Máy mới cần:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`.pytest_cache/` đã nằm trong `.gitignore`.

---

## 10. Bẫy môi trường đã gặp (đừng mất thời gian lại)

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `git status` chết: `sh.exe ... 0xC0000022` | sandbox chặn MSYS named object | tránh `git status`; dùng `git diff --numstat`, `git ls-files`, `git hash-object` |
| `git commit` chết tương tự | `git commit` luôn spawn `sh.exe` | dùng plumbing: `write-tree` → `commit-tree` → `update-ref` |
| `git fetch/push` báo `schannel: SEC_E_NO_CREDENTIALS` | sandbox chặn credential store | thêm `-c http.sslBackend=openssl` |
| push chết ở hook LFS | `pre-push` là script `sh` | `--no-verify` **chỉ khi** commit không đụng `*.h5` |
| `git diff-index` báo mọi file là `M` | index stat cache stale | so `git hash-object` với `git rev-parse HEAD:<file>` |
| `pip install` treo ở 100% CPU | resolver backtracking | `--only-binary=:all:` |
| camera không đọc được frame | OpenCV mặc định dùng MSMF, hỏng trên máy này | dùng `cv2.CAP_DSHOW` (đã kiểm chứng chạy được) |

---

## 11. Trạng thái dự án tại thời điểm tạo file này

- Nhánh: `main` = `develop` = `3d64e9d`; `feature/US-001` có commit tài liệu (đã push).
- Backlog: 10 epic, 39 US (Ready for Dev), 63 AC, 75 task (To Do), 26 BR.
- Chưa có: `src/`, `tests/`, `Dockerfile`, `.github/`, backend, `pytest`.
- Đã có bộ khung API: `docs/api/_TEMPLATE.md`, quy ước `docs/api/README.md`.
- Model + dữ liệu: đã kiểm chứng 23/23 đúng, 1609 CSV hợp lệ 93 cột.

---

## 12. Nhật ký thực hiện (điền dần)

| Ngày | US | Nhánh | API docs | Task xong | AC PASS | Xác nhận của chủ dự án |
|---|---|---|---|---|---|---|
| 2026-10-19 | **US-001** | `feature/US-001` | `docs/api/US-001.md` (`ANALYSIS_READY`, đã duyệt) | TSK-001, TSK-002 | AC-001-01, AC-001-02 — **10/10 test** | ✅ **PASS** (chủ dự án xác nhận 2026-10-19) |
| 2026-10-25 | **US-002** | `feature/US-002` | `docs/api/US-002.md` (`ANALYSIS_READY`, đã duyệt) | TSK-003, TSK-004 | AC-002-01, AC-002-02 — **14/14 test** | ✅ **PASS** (chủ dự án xác nhận 2026-10-25) |
| 2026-10-26 | **US-003** | `feature/US-003` | `docs/api/US-003.md` (`ANALYSIS_READY`, đã duyệt) | TSK-005, TSK-006 | AC-003-01, AC-003-02 — **18/18 test** | ✅ **PASS** (chủ dự án xác nhận 2026-10-26) |
| 2026-10-26 | **US-004** | `feature/US-004` | `docs/api/US-004.md` (`ANALYSIS_READY`, đã duyệt) | TSK-007 | AC-004-01 — **21/21 test** | ✅ **PASS** (chủ dự án xác nhận 2026-10-26) |
| 2026-10-26 | **US-005** | `feature/US-005` | `docs/api/US-005.md` (`ANALYSIS_READY`, đã duyệt) | TSK-008 | AC-005-01, AC-005-02 — **24/24 test** | ✅ **PASS** (chủ dự án xác nhận 2026-10-26) |
| 2026-10-26 | **US-006** | `feature/US-006` | `docs/api/US-006.md` (`ANALYSIS_READY`, đã duyệt) | TSK-009, TSK-010, TSK-011 | AC-006-01, AC-006-02 — **32/32 test** | ✅ **PASS** (chủ dự án xác nhận 2026-10-26) |






