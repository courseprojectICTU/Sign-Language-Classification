# Pull Request: [Ticket/US-ID] - Mô tả ngắn gọn

## Mục đích
Mô tả ngắn gọn: PR này giải quyết vấn đề gì? Liệt kê Issue/Story ID liên quan (ví dụ: US-002, BUG-123).

---

## Loại thay đổi
- [ ] Feature (tính năng mới)
- [ ] Bugfix (sửa lỗi)
- [ ] Refactor (tái cấu trúc mã nguồn, không đổi hành vi)
- [ ] Docs (cập nhật tài liệu)
- [ ] Chore (cấu hình, CI/CD, script, dependency...)
- [ ] Hotfix (sửa lỗi khẩn cấp trên production)

---

## Thay đổi chính (Summary of Changes)

| Loại | File / Module | Mô tả thay đổi |
|---|---|---|
| Feat/Refactor/... | `đường_dẫn_file` | Mô tả ngắn gọn thay đổi |
| ... | ... | ... |

---

## Kiểm tra Chất lượng (Quality Gates)

| Tiêu chí | Trạng thái | Ghi chú |
|---|---|---|
| **Unit Test** | [ ] Pass / [ ] Không có | Lệnh chạy: `pytest tests -v` |
| **Regression Test** | [ ] Pass / [ ] Không có | Lệnh chạy: `pytest tests/test_pipeline_baseline.py -v` |
| **Build / Cú pháp** | [ ] Pass / [ ] Không có | Cú pháp Python hợp lệ, Notebook JSON nguyên vẹn |
| **Lint / Format** | [ ] Pass / [ ] Không có | Không có cảnh báo linter / type checker |
| **Tương thích ngược** | [ ] Đảm bảo / [ ] Có breaking change | Nếu có breaking change $\to$ Ghi chú rõ trong phần Mô tả thêm |

---

## Bằng chứng Kiểm thử (Test Evidence)

| Bộ kiểm thử (Test Suite) | Lệnh chạy | Kết quả (Pass/Fail) | Ảnh chụp màn hình / Log |
|---|---|---|---|
| Unit Test | `pytest tests -v` | [ ] Pass / [ ] Fail | [DÁN_ẢNH_HOẶC_LOG_TẠI_ĐÂY] |
| Regression Baseline | `pytest tests/test_pipeline_baseline.py -v` | [ ] Pass / [ ] Fail | [DÁN_ẢNH_HOẶC_LOG_TẠI_ĐÂY] |
| Khác (nếu có) | ... | [ ] Pass / [ ] Fail | [DÁN_ẢNH_HOẶC_LOG_TẠI_ĐÂY] |

> **Lưu ý:** Test phải chạy trên môi trường Python của dự án: `& "D:\program\python\python.exe" -m pytest tests -v` (hoặc `.\.venv\Scripts\python.exe`).

---

## Ảnh minh chứng (Screenshot / Artifacts)

> Người duyệt (Reviewer) kiểm tra trực tiếp trên GitHub/GitLab. Kéo thả ảnh vào các vị trí bên dưới.

| Loại | Ảnh minh chứng |
|---|---|
| Kết quả kiểm thử (pytest) | ![Pytest Result](DÁN_ẢNH_PYTEST_TẠI_ĐÂY) |
| Pipeline hồi quy (Baseline) | ![Pipeline](DÁN_ẢNH_PIPELINE_TẠI_ĐÂY) |
| Khác (nếu có) | ![Other](DÁN_ẢNH_KHÁC_TẠI_ĐÂY) |

---

## Checklist Người duyệt (Reviewer Checklist)

- [ ] Mã nguồn tuân thủ quy ước lập trình (coding convention) của dự án.
- [ ] Không còn mã nguồn thừa (dead code), code bị comment, hoặc lệnh `print` debug sót lại.
- [ ] Tên biến, hàm, lớp rõ ràng, tuân thủ đúng quy ước đặt tên.
- [ ] Không hard-code các giá trị magic number / magic string trực tiếp trong code.
- [ ] Đầy đủ docstring / comment cho các hàm, module, lớp công khai mới.
- [ ] Không hard-code đường dẫn tuyệt đối (đường dẫn Windows `D:\...`).
- [ ] Không commit các file rác (`__pycache__`, `.pytest_cache`, `.venv`, file tạm `~$*`).
- [ ] Test mới (nếu có) đã được bổ sung vào `tests/` và vượt qua kiểm thử.
- [ ] Đã cập nhật tài liệu liên quan (`docs/`, `README.md`) nếu có thay đổi hành vi hoặc API.
- [ ] Không có breaking change chưa được thông báo hoặc ghi chú rõ ràng.

---

## Ảnh minh chứng UI / Trải nghiệm (Bắt buộc nếu có thay đổi giao diện hoặc luồng người dùng)

| Loại | Ảnh minh chứng |
|---|---|
| Giao diện / Tính năng mới | ![UI Screenshot](DÁN_ẢNH_UI_TẠI_ĐÂY) |
| Terminal / Log thực thi | ![Terminal](DÁN_ẢNH_TERMINAL_TẠI_ĐÂY) |
| Khác | ![Other](DÁN_ẢNH_KHÁC_TẠI_ĐÂY) |

---

## Checklist Tác giả (Self-review trước khi gửi PR)

- [ ] Đã chạy toàn bộ test suite (`pytest tests -v`) $\to$ **100% Passed**.
- [ ] Đã chạy kiểm thử hồi quy (`pytest tests/test_pipeline_baseline.py -v`) $\to$ **23/23 ký tự đúng**.
- [ ] Đã chạy test liên quan đến phạm vi thay đổi $\to$ **Passed**.
- [ ] Đã dọn dẹp mã nguồn debug, `print`, `console.log` thừa.
- [ ] Đã cập nhật đầy đủ tài liệu thiết kế (`docs/api/US-0XX.md`) và nhật ký thực hiện (`docs/WORKFLOW.md`).
- [ ] Đã kiểm tra `git diff` $\to$ không có file rác, không có file lớn (>10MB) không cần thiết.
- [ ] Đã kiểm tra file `.gitignore` chứa đầy đủ các mẫu cần thiết (`.venv/`, `__pycache__/`, `.pytest_cache/`, `~$*`, `*.npz` nếu cần).

---

## Ghi chú / Mô tả thêm (Tùy chọn)

Mô tả thêm nếu có (breaking change, các bước migration, tác động hiệu năng, lưu ý bảo mật, kế hoạch rollback...).

---

## Thông tin Liên quan
- **Mã User Story / Issue:** [US-XXX / BUG-XXX]
- **Mã Epic:** [EPC-XXX]
- **Nhánh nguồn:** `[feature|bugfix|hotfix|docs|chore]/[ID]`
- **Nhánh đích:** `develop`
- **Mục tiêu triển khai:** [Staging / Production / None]

---

> **Lưu ý cho Reviewer:** Nếu PR này có chứa breaking change, vui lòng ghi rõ ràng trong phần "Ghi chú / Mô tả thêm" và đánh dấu `Breaking Change` trong Checklist.