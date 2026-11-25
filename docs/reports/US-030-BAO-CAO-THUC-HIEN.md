# Báo Cáo Thực Hiện — US-030

> **User Story:** US-030 — Cổng phê duyệt thủ công cho production  
> **Epic:** EPC-08 — Triển khai liên tục & Hoàn tác  
> **Nhánh:** `feature/US-030-prod-approval`  
> **Trạng thái:** `LOCAL PASS — chờ cấu hình GitHub Environment và xác minh thủ công`

## 1. Phạm vi

US-030 có một Acceptance Criteria (AC-030-01, Critical), một task (TSK-057),
phụ thuộc US-029 và thực hiện BR-017. Theo xác nhận của chủ dự án, production
phải có một staging deployment thành công cho **đúng cùng Git SHA** trước khi
chờ duyệt; cổng Environment nằm trước mọi bước của job production.

Không có endpoint, CLI hay API công khai mới. **API docs: N/A** — thay đổi chỉ
điều khiển GitHub Actions và GitHub Environment; chủ dự án đã xác nhận phạm vi
N/A trước khi viết test.

## 2. Thay đổi

- Thêm job preflight chỉ đọc các workflow run của `develop`, tìm một lần chạy
  `deploy-backend.yml` thành công cho đúng `GITHUB_SHA`; không tìm thấy thì
  dừng fail-closed, trước khi job production bắt đầu.
- Job triển khai phụ thuộc preflight và khai báo Environment theo nhánh:
  `production` cho `main`, `staging` cho `develop`. GitHub Environment protection
  sẽ chặn toàn bộ job production trước build/deploy/traffic cho tới khi được duyệt.
- Preflight không kiểm tra staging đối với push `develop`, vì đây chính là luồng
  triển khai staging.

Workflow chỉ tham chiếu tên Environment; danh sách **required reviewers** phải
được chủ repo cấu hình tại GitHub Settings → Environments → `production`. Cấu hình
reviewer, trạng thái Waiting/Approved và audit người/thời điểm duyệt chưa được
xác minh trực tiếp trên GitHub trong phiên này.

Chính sách cùng SHA là fail-closed như chủ dự án đã chọn. Nếu merge vào `main`
tạo SHA mới thay vì promote cùng commit, production sẽ bị chặn dù code có cùng
nội dung; không tự chuyển sang so sánh tree hash. Không có push, PR, deploy hay
thay đổi tài nguyên Azure trong phiên này.

## 3. Nghiệm thu AC

| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC-030-01 — production chờ duyệt sau khi staging đạt | **PARTIAL** | Test hợp đồng workflow PASS; trạng thái chờ duyệt thật, required reviewers và audit người/thời điểm cần xác minh sau khi cấu hình Environment trên GitHub. |

## 4. Kiểm thử

| Lệnh | Kết quả |
|---|---|
| `& ".\.venv\Scripts\python.exe" -m pytest tests/test_us030_production_approval.py tests/test_us029_deploy_workflow.py -q` | **6 passed** |
| `& ".\.venv\Scripts\python.exe" -m ruff check tests/test_us030_production_approval.py` | **All checks passed** |
| `& ".\.venv\Scripts\python.exe" -m pytest tests -q` | **223 passed, 9 warnings** |
| `& ".\.venv\Scripts\python.exe" -c "import yaml; from pathlib import Path; yaml.load(Path('.github/workflows/deploy-backend.yml').read_text(encoding='utf-8'), Loader=yaml.BaseLoader); print('Workflow YAML syntax parsed')"` | **Workflow YAML syntax parsed** |

## 5. Commit cục bộ

| Commit | Nội dung |
|---|---|
| `6fde20e` | Thêm test hợp đồng cho staging preflight và production gate |
| `6d441bb` | Chỉnh assertion của test theo điều kiện job |
| `dbf75d1` | Thêm preflight cùng SHA và GitHub Environment gate |

## 6. Việc còn lại

1. Chủ repo cấu hình một hoặc nhiều required reviewers cho GitHub Environment
   `production`.
2. Xác nhận quy trình merge giữ nguyên SHA đã deploy staging; nếu không, cần
   thay đổi chính sách cùng SHA trước khi bật promotion.
3. Sau khi cho phép push/PR, xác minh một workflow run production dừng ở trạng
   thái chờ duyệt và kiểm tra audit record. Không phê duyệt một lần triển khai
   production chỉ để thử nghiệm.
