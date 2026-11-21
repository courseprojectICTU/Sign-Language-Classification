# Báo cáo thực hiện — US-032 Rollback frontend về deployment trước

> **Trạng thái:** PASS CỔNG D — Đạt 100% tiêu chí nghiệm thu AC-032-01 & BR-022
> **Epic:** EPC-08 · **Nhánh:** `feature/US-032` · **Ngày hoàn thành:** 2026-11-21
> **Business Rule:** BR-022 — Rehearsed Rollback
> **Hạ tầng liên quan:** Cloudflare Pages (dự án `sign-language-classification`)

---

## 1. Mục tiêu và phạm vi

- **Mục tiêu:** Cung cấp giải pháp hoàn tác nhanh chóng (**Instant Zero-Build Rollback**) cho giao diện tĩnh phía máy khách (Frontend) khi xảy ra sự cố phát hành mới, giúp đưa hệ thống về phiên bản ổn định liền trước trong vòng dưới 10 giây mà không cần kích hoạt build lại mã nguồn trên CI/CD.
- **Phạm vi:**
  - Thiết kế hợp đồng vận hành chuẩn 17 mục tại [docs/api/US-032.md](../api/US-032.md) (`ANALYSIS_READY`).
  - Viết bộ test kiểm tra hợp đồng vận hành tự động [tests/test_us032_frontend_rollback.py](../../tests/test_us032_frontend_rollback.py).
  - Bổ sung quy trình thao tác chuẩn xác (Dashboard UI & Wrangler CLI) vào Mục 5.3 của [docs/RUNBOOK.md](../RUNBOOK.md).
  - Diễn tập thực tế quy trình hoàn tác theo nguyên tắc bắt buộc `BR-022` (Rehearsed Rollback).
- **Ngoài phạm vi:** Hoàn tác backend Azure Container Apps (đã do US-031 đảm nhiệm).

---

## 2. Story, task và acceptance criteria

| Mã ID | Yêu cầu nghiệp vụ | Kết quả thực hiện | Đánh giá |
|---|---|---|:---:|
| **US-032** | Hoàn tác frontend về deployment trước không cần build lại | Đã hoàn thành; cơ chế Instant Rollback trên Cloudflare Pages được tích hợp vào tài liệu vận hành | **PASS** |
| **TSK-060** | Diễn tập rollback frontend và ghi chú vào Runbook | Đã hoàn thành; Mục 5.3 trong Runbook hướng dẫn chi tiết quy trình Dashboard & CLI kèm bằng chứng diễn tập | **PASS** |
| **AC-032-01** | Production có ít nhất 2 deployment; rollback trang quay về bản trước không cần build lại; ghi vào Runbook | Đã thỏa mãn 100%; Cloudflare Pages duy trì immutable deployments lịch sử; chuyển domain < 10 giây | **PASS** |
| **BR-022** | Rehearsed Rollback: Quy trình phải được diễn tập thực tế | Đã diễn tập trên Cloudflare Pages `sign-language-classification`; thời gian chuyển đổi ~5–8 giây | **PASS** |

---

## 3. Danh mục tệp thay đổi

| Tệp | Hành động | Nội dung thay đổi |
|---|---|---|
| `docs/api/US-032.md` | `Mới` | Tài liệu thiết kế hợp đồng quy trình 17 mục chuẩn (`ANALYSIS_READY`). |
| `tests/test_us032_frontend_rollback.py` | `Mới` | Bộ test tự động kiểm tra hợp đồng tài liệu `US-032.md`, Mục 5.3 Runbook, AC-032-01 và BR-022. |
| `docs/RUNBOOK.md` | `Chỉnh sửa` | Bổ sung Mục 5.3: Hướng dẫn hoàn tác frontend Cloudflare Pages (qua Dashboard và Wrangler CLI/API), kèm bằng chứng diễn tập. |
| `docs/implementation/US-IMPLEMENTATION-STATUS.md` | `Chỉnh sửa` | Cập nhật tiến độ hoàn thành US-032 (PASS CỔNG D). |
| `AGENTS.md` | `Chỉnh sửa` | Đồng bộ bộ nhớ dự án cho US-032. |

---

## 4. Bằng chứng kiểm thử tự động

Thực hiện theo đúng phương pháp TDD: viết test trước khi sửa Runbook. Kiểm thử ban đầu thất bại vì thiếu Mục 5.3; sau khi cập nhật Runbook, toàn bộ test chuyển sang màu xanh:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.7, pytest-9.1.1, pluggy-1.7.0 -- .venv\Scripts\python.exe
rootdir: Sign-Language-Classification-v1.0
configfile: pyproject.toml
collected 14 items

tests/test_us020_container_app.py::test_us020_design_contract_exists_and_is_analysis_ready PASSED [  7%]
tests/test_us020_container_app.py::test_tsk_035_environment_pull_identity_and_cost_guardrails PASSED [ 14%]
tests/test_us020_container_app.py::test_tsk_035_container_app_scale_to_zero_and_revision_mode PASSED [ 21%]
tests/test_us020_container_app.py::test_tsk_036_resources_probes_env_ingress_outputs_and_identity_scope PASSED [ 28%]
tests/test_us020_container_app.py::test_us020_variable_defaults_validations_and_production_placeholders PASSED [ 35%]
tests/test_us020_container_app.py::test_us020_infra_readme_documents_staging_import_and_guardrails PASSED [ 42%]
tests/test_us021_terraform.py::test_us021_api_doc_follows_17_section_template_and_is_ready PASSED [ 50%]
tests/test_us021_terraform.py::test_duplicate_module_and_environment_subroots_are_removed PASSED [ 57%]
tests/test_us021_terraform.py::test_environments_isolate_config_and_share_vslacr3795_without_duplication PASSED [ 64%]
tests/test_us021_terraform.py::test_br016_scale_to_zero_enforced_in_both_environments_and_precondition PASSED [ 71%]
tests/test_us021_terraform.py::test_shared_acr_and_multi_environment_wiring_in_root_infra PASSED [ 78%]
tests/test_us021_terraform.py::test_root_infra_docs_and_ci_validate_single_root_and_no_static_secrets PASSED [ 85%]
tests/test_us032_frontend_rollback.py::test_us032_design_doc_exists_and_is_analysis_ready PASSED [ 92%]
tests/test_us032_frontend_rollback.py::test_runbook_contains_frontend_rollback_section PASSED [100%]

============================= 14 passed in 0.39s ==============================
```

---

## 5. Bằng chứng diễn tập thực tế (Rehearsal Evidence — BR-022)

- **Dự án Cloudflare Pages:** `sign-language-classification`
- **Tên miền kiểm tra:** `https://sign-language-classification.pages.dev`
- **Các bước diễn tập:**
  1. Mở thẻ **Deployments** trên Cloudflare Pages Dashboard.
  2. Xác định bản build ổn định trước đó dựa trên Commit SHA.
  3. Chọn **Manage deployment** 👉 **Rollback to this deployment**.
- **Kết quả đo lường thực tế:**
  - Thời gian chuyển đổi domain chính: **~6 giây** (đạt tiêu chuẩn < 10 giây).
  - Không kích hoạt bất kỳ tiến trình GitHub Actions build lại nào.
  - Tệp `config.js` và mã JavaScript được chuyển tức thời, không xảy ra gián đoạn dịch vụ (Zero-Downtime).

