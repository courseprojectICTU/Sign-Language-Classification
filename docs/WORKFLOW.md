# QUY TRÌNH LÀM VIỆC — US → AC → Task → Nghiệm thu

File này là **quy trình bắt buộc** cho mọi User Story trong dự án. Đọc lại file này
trước khi bắt đầu bất kỳ US nào. Nguồn dữ liệu gốc: `docs/product-backlog-cicd-2-tuan.xlsx`.

Cập nhật lần cuối: 2026-10-19.

---

## 0. Nguyên tắc bất biến

1. **Không code trước test.** Acceptance Criteria được chuyển thành test **trước** khi
   viết code tính năng (trừ khi AC không thể test tự động — phải nêu rõ lý do).
2. **Không gộp task.** Mỗi task = một thay đổi nhỏ, một commit riêng. Không làm 5 task
   trong 1 lần sửa.
3. **Commit thường xuyên, KHÔNG push.** Push là quyết định của chủ dự án, không tự push.
4. **Bám Business Rules.** Mỗi thay đổi phải chỉ ra BR nào đang được thoả (BR-001…BR-026).
5. **Không mở rộng phạm vi.** Chỉ sửa những gì US yêu cầu.
6. **Nghiệm thu cần chữ ký.** Test xanh **chưa phải** là xong — phải có xác nhận PASS
   của chủ dự án.
7. **Ghi lại bằng chứng.** Mọi báo cáo PASS/FAIL phải kèm output thật, không nói suông.

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

## 5. Bước 4 — Viết test TRƯỚC khi code  (CỔNG B)

1. Tạo test cho **toàn bộ** AC.
2. Chạy test → phải **ĐỎ** (vì code chưa có). Nếu xanh ngay, nghĩa là test vô nghĩa
   hoặc tính năng đã tồn tại — phải báo lại.
3. Chỉ ra "lưới an toàn": với US tách code, baseline là **23/23 ký tự đúng** trên
   `data/anphabet/<chữ>/1.csv` (đã kiểm chứng 2026-10-19).
4. Commit riêng: `test(us-00X): ...`

Chỉ sau khi chủ dự án đồng ý danh sách test mới sang bước 5.

---

## 6. Bước 5 — Làm từng task, commit từng task

Lặp cho **mỗi** task trong sheet `Task(Công việc)`:

1. Nêu task ID + expected result (lấy nguyên văn từ backlog).
2. Chỉ ra BR liên quan và cách code thoả BR đó.
3. Sửa **tối thiểu** để task đó xong.
4. Chạy test liên quan + test cũ (không được làm đỏ test cũ).
5. **Commit riêng**.
6. Báo chủ dự án: đã đổi file nào, vì sao, test nào xanh.

### 6.1. Quy ước commit

```
<type>(<scope>): <mô tả ngắn ở thể mệnh lệnh>

- vì sao (BR nào, AC nào)
- ảnh hưởng gì
```

`type`: `feat` | `fix` | `test` | `docs` | `refactor` | `chore`
`scope`: `us-001`, `us-002`…

Ví dụ: `feat(us-001): them module src/vsl/heatmap.py`

---

## 7. Bước 6 — Nghiệm thu  (CỔNG C)

1. Chạy **toàn bộ** test, không chỉ test của US.
2. Kiểm tra "build": import module, chạy pipeline thật, so baseline 23/23.
3. Báo cáo dạng bảng: AC ID → PASS/FAIL → bằng chứng (tên test + output).
4. **Chờ chủ dự án xác nhận PASS.** Chỉ khi có xác nhận mới coi là hoàn thành.
5. Nếu FAIL: sửa, commit tiếp, lặp lại bước 7.

---

## 8. Lệnh chạy test chuẩn

`.venv\Scripts\python.exe` bị lỗi DLL (mục 9.1 AGENTS.md), nên dùng Python gốc:

```powershell
$env:PYTHONPATH = "$PWD\.venv\Lib\site-packages"
& "D:\program\python\python.exe" -m pytest tests -v
```

Điều kiện tiên quyết: `pytest` **chưa có** trong `.venv` — phải cài trước US đầu tiên.

---

## 9. Bẫy môi trường đã gặp (đừng mất thời gian lại)

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

## 10. Trạng thái dự án tại thời điểm tạo file này

- Nhánh: `main` = `develop` = `3d64e9d`; `feature/US-001` có commit tài liệu (đã push).
- Backlog: 10 epic, 39 US (Ready for Dev), 63 AC, 75 task (To Do), 26 BR.
- Chưa có: `src/`, `tests/`, `Dockerfile`, `.github/`, backend, `pytest`.
- Model + dữ liệu: đã kiểm chứng 23/23 đúng, 1609 CSV hợp lệ 93 cột.

---

## 11. Nhật ký thực hiện (điền dần)

| Ngày | US | Nhánh | Task xong | AC PASS | Xác nhận của chủ dự án |
|---|---|---|---|---|---|
| | | | | | |
