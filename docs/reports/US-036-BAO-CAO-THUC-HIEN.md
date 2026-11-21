# Báo Cáo Thực Hiện & Nghiệm Thu — US-036

> **User Story:** US-036 — Cập nhật AGENTS.md theo cấu trúc mới  
> **Epic:** EPC-10 — Tài liệu & Bàn giao  
> **Nhánh:** `feature/US-036`  
> **Mốc thời gian nghiệm thu:** 2026-11-21  
> **Người thực hiện:** Antigravity Agent  
> **Trạng thái:** `HOÀN THÀNH — ĐÃ SẴN SÀNG DUYỆT CỔNG D`

---

## 1. Tổng Quan Kết Quả Thực Hiện

Theo quy tắc **`BR-024`** (*Living Documentation*), tài liệu vận hành và bộ nhớ dự án (`AGENTS.md`) phải được cập nhật cùng đợt thay đổi để không gây nhầm lẫn hoặc dựa vào thông tin lỗi thời.

User Story **US-036** đã hoàn tất việc chuẩn hóa toàn diện file `AGENTS.md` khớp 100% với hiện trạng mã nguồn, kiến trúc đa nền tảng (FastAPI + Cloudflare Pages + Azure Container Apps), cập nhật baseline Git, bổ sung các bẫy kỹ thuật mới phát sinh, và thiết lập bộ kiểm thử tự động `tests/test_us036_agents_contract.py`.

---

## 2. Đối Chiếu Tiêu Chí Nghiệm Thu (Acceptance Criteria)

| Mã AC | Mô tả tiêu chí | Kết quả kiểm thử | Trạng thái |
|---|---|---|:---:|
| **`AC-036-01`** | Đọc `AGENTS.md` và đối chiếu với repository; mô tả trong `AGENTS.md` khớp với thực tế; không còn câu nào nói dự án chỉ có notebook. | - Bộ test `tests/test_us036_agents_contract.py` (6/6 tests) kiểm tra tự động mốc thời gian, kiến trúc FastAPI/Cloudflare/ACA, bẫy OIDC/Black/CORS, cây thư mục và bảng tiến độ.<br>- Toàn bộ 6 test đều PASS 100%. | **PASS** ✅ |

---

## 3. Đối Chiếu Công Việc (Tasks)

| Mã Task | Tên công việc | Kết quả thực hiện | Commit | Trạng thái |
|---|---|---|---|:---:|
| **TSK-067** | Cập nhật AGENTS.md theo cấu trúc mới | - Cập nhật mốc ngày `2026-11-21`, baseline `8d3f15e`, release `v1.0.0` trên `main` (`bf6c257`).<br>- Bổ sung các file mới vào cây thư mục Section 3.<br>- Bổ sung Bẫy 11 (OIDC subject claim), Bẫy 12 (Windows sandbox Python 3.12 DLL crash), Bẫy 13 (CORS preview domain allowlist).<br>- Cập nhật môi trường thực thi chuẩn (Python 3.14) và bảng tiến độ (US-032, US-036). | `2ca8e55` | **DONE** ✅ |

---

## 4. Tuân Thủ Quy Tắc Nghiệp Vụ (Business Rules)

| Mã BR | Tên quy tắc | Nội dung tuân thủ |
|---|---|---|
| **`BR-024`** | Living Documentation | Toàn bộ các thay đổi về hạ tầng Azure, Cloudflare Pages, quy trình CI/CD và các bẫy vận hành thực tế đã được đồng bộ trực tiếp vào `AGENTS.md`, ngăn ngừa mọi nguy cơ sai sót cho các phiên làm việc sau. |
| **`BR-019`** | Secret Zero-Leakage | Không đưa bất kỳ thông tin nhạy cảm, client secret, hay token bí mật nào vào `AGENTS.md` hoặc tài liệu báo cáo. |

---

## 5. Bằng Chứng Thực Thi Kiểm Thử (Test Output)

### 5.1. Kiểm thử hợp đồng bộ nhớ dự án:
```powershell
& "py" -3.14 -m pytest tests/test_us036_agents_contract.py -v
```
Output:
```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\doant\AppData\Local\Python\pythoncore-3.14-64\python.exe
cachedir: .pytest_cache
rootdir: D:\HocTap\HK7\DienToanDamMay\project\Sign-Language-Classification-v1.0
configfile: pyproject.toml
plugins: anyio-4.13.0, platformdirs-4.13.3
collecting ... collected 6 items

tests/test_us036_agents_contract.py::test_agents_md_exists_and_utf8 PASSED [ 16%]
tests/test_us036_agents_contract.py::test_agents_md_metadata_freshness PASSED [ 33%]
tests/test_us036_agents_contract.py::test_agents_md_reflects_new_architecture PASSED [ 50%]
tests/test_us036_agents_contract.py::test_agents_md_directory_structure PASSED [ 66%]
tests/test_us036_agents_contract.py::test_agents_md_contains_operational_traps PASSED [ 83%]
tests/test_us036_agents_contract.py::test_agents_md_progress_table PASSED [100%]

============================== 6 passed in 0.16s ==============================
```

### 5.2. Kiểm tra định dạng & Linting:
```powershell
& "py" -3.14 -m black --check src tests scripts
& "py" -3.14 -m ruff check src tests scripts
```
Output:
```
All done! ✨ 🍰 ✨
50 files would be left unchanged.
All checks passed!
```

### 5.3. Kiểm thử hồi quy tích hợp:
```powershell
& "py" -3.14 -m pytest tests/test_us036_agents_contract.py tests/test_us032_frontend_rollback.py tests/test_ops_contract.py -v
```
Output:
```
============================= 21 passed in 1.87s ==============================
```

---

## 6. Kết Luận & Đề Xuất
User Story **US-036** đã hoàn thành đầy đủ các tiêu chuẩn nghiệm thu và tuân thủ nghiêm ngặt quy trình `WORKFLOW.md`. Sẵn sàng để chủ dự án xem xét nghiệm thu **CỔNG D**.
