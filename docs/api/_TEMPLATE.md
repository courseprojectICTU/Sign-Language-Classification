# API Design — [US-XXX] [Tên User Story ngắn]

> **Trạng thái:** `[DRAFT | ANALYSIS_READY | NEEDS_CLARIFICATION | BLOCKED]`
> **Epic:** `[EPC-0X]` · **Nhánh:** `[feature/US-0XX]` · **Ngày:** `[YYYY-MM-DD]`
> **Người soạn:** `[tên/vai]` · **Người duyệt:** `[chủ dự án]`
>
> File này là **hợp đồng bàn giao**. Không sửa source code khi đang viết file này.
> Điền **đủ 17 mục**. Mục nào không áp dụng thì ghi `N/A` **kèm lý do**, không xoá mục.

---

## 1. Mục tiêu

- Vấn đề cần giải quyết: `[...]`
- Kết quả mong đợi sau US này: `[...]`
- Phạm vi: `[...]` · Ngoài phạm vi: `[...]`

---

## 2. Story Analysis

| Thành phần | Nội dung (trích từ backlog) |
|---|---|
| Story ID | `[US-0XX]` |
| Actor | `[A01 / A02 / A03 / A04]` |
| Goal | `[...]` |
| Resource | `[...]` |
| Action | `[...]` |
| Business Rule | `[BR-0XX, ...]` |
| Acceptance Criteria | `[AC-0XX-01, ...]` |
| Dependency | `[US-0XX / None]` |

---

## 3. Existing Architecture

Ghi theo **thực trạng repo**, không theo mong muốn:

- Backend hiện có: `[chưa có / mô tả]`
- Frontend hiện có: `[chưa có / mô tả]`
- Module liên quan: `[src/vsl/..., run_realtime.py, ...]`
- Cách chạy hiện tại: `[notebook / script / ...]`
- Quy ước response/error hiện có: `[chưa có — cần chốt / mô tả]`

---

## 4. Existing APIs

| Method | Endpoint | Purpose | Nơi định nghĩa | Permission | Scope |
|---|---|---|---|---|---|
| `[GET]` | `[/health]` | `[...]` | `[...]` | `[...]` | `[...]` |

> Nếu dự án chưa có API nào, ghi rõ: **"Chưa có API nào tồn tại (kiểm chứng ngày ...)"**.

---

## 5. API Gap Analysis

| Yêu cầu | API hiện có | Quyết định | Lý do |
|---|---|---|---|
| `[...]` | `[None]` | `[REUSE / MODIFY / NEW / NO API NEEDED / UNKNOWN]` | `[...]` |

Quy tắc: ưu tiên REUSE → MODIFY → NEW. Không tạo endpoint trùng.

---

## 6. Proposed API Changes

### 6.1. `[METHOD] [path]`

- **Method:** `[...]`
- **Endpoint:** `[...]`
- **Purpose:** `[...]`
- **Authentication:** `[public / token / ...]`
- **Authorization:** `[role nào được gọi]`
- **Path Parameters:** `[...]`
- **Query Parameters:** `[...]`
- **Request Body:** `[JSON schema + ví dụ]`
- **Response:** `[JSON schema + ví dụ]`
- **HTTP Status:** `[200/201/400/...]`
- **Validation:** `[điều kiện hợp lệ]`
- **Business Rules:** `[BR-0XX]`
- **Error Cases:** `[mã lỗi + thông điệp]`

> Thêm 6.2, 6.3… cho từng endpoint.

---

## 7. Business Flow

Luồng xử lý từng bước, ví dụ:

```
Client gửi ảnh
  → validate định dạng/kích thước
  → MediaPipe trích landmark (phải đúng 93 giá trị — BR-001)
  → create_heatmap (một bản duy nhất — BR-002)
  → model predict 23 lớp
  → ánh xạ nhãn qua VIETNAMESE_ALPHABET (BR-003)
  → trả JSON {letter, confidence}
```

---

## 8. Security

| Mục | Giá trị |
|---|---|
| Authentication | `[...]` |
| Authorization | `[...]` |
| Role được phép | `[...]` |
| Dữ liệu nhạy cảm | `[...]` |
| Giới hạn tần suất | `[...]` |
| Không được đưa vào request | `actorId`, `createdBy`, `organizationId`… nếu server tự suy ra được |

---

## 9. Organization Scope

- Dự án có multi-tenant không: `[Có / Không]`
- Nếu **Không**: ghi rõ `N/A — dự án một tổ chức, không phân tách dữ liệu theo organization`.
- Nếu **Có**: mô tả `User → Organization → Resource` và cách server xác định scope (không tin client).

---

## 10. Audit Impact

- Có cần ghi log/audit không: `[Có / Không]`
- Ghi gì (ai gọi, lúc nào, kết quả): `[...]`
- Lưu ở đâu: `[...]`

---

## 11. Data Model Impact

- Entity/bảng bị ảnh hưởng: `[...]`
- Trường thêm/sửa: `[...]`
- Migration cần không: `[Có / Không]`

---

## 12. Files Expected To Change

| File dự kiến | Thay đổi | Lý do |
|---|---|---|
| `[src/vsl/api/...]` | `[new]` | `[...]` |
| `[tests/...]` | `[new]` | `[...]` |

> Chỉ **dự kiến**. Không tạo file thật trong bước này.

---

## 13. Acceptance Criteria Mapping

| AC ID | Nội dung AC (tóm tắt) | Endpoint/hành vi đáp ứng | Test sẽ viết |
|---|---|---|---|
| `[AC-0XX-01]` | `[...]` | `[...]` | `[tests/test_...]` |

---

## 14. Test Scenarios

| Loại | Mô tả | Dữ liệu |
|---|---|---|
| Happy path | `[...]` | `[ảnh/CSV mẫu]` |
| Validation | `[...]` | `[...]` |
| Authorization | `[...]` | `[...]` |
| Business failure | `[...]` | `[...]` |
| Regression | `[...]` | baseline 23/23 |

---

## 15. Risks

| Rủi ro | Ảnh hưởng | Giảm thiểu |
|---|---|---|
| `[...]` | `[...]` | `[...]` |

---

## 16. Open Questions

| # | Câu hỏi | Ảnh hưởng | Ai quyết |
|---|---|---|---|
| Q1 | `[...]` | `[...]` | `[PO/tech lead]` |

> Nếu còn câu hỏi chặn thiết kế → trạng thái `NEEDS_CLARIFICATION`, không được sang test.

---

## 17. Implementation Handoff

- **Backend nhận:** `[endpoint, validation, BR, error behavior]`
- **Frontend nhận:** `[endpoint, request/response, error]`
- **Tester nhận:** `[AC + scenario + dữ liệu]`
- **Điều kiện bắt đầu code:** `api.md` ở trạng thái `ANALYSIS_READY` **và** chủ dự án đã duyệt.
