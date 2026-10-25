# API Documentation — quy ước chung

Thư mục này chứa **hợp đồng API** của dự án. Mỗi User Story tạo ra hoặc thay đổi
một hợp đồng tiêu thụ **phải** có một file ở đây **trước** khi viết test và code.

- Bộ khung bắt buộc: [`_TEMPLATE.md`](_TEMPLATE.md)
- Quy trình tổng thể: [`docs/WORKFLOW.md`](../WORKFLOW.md)
- Nguồn yêu cầu: `docs/product-backlog-cicd-2-tuan.xlsx`

---

## 1. Khi nào BẮT BUỘC có API docs

Bắt buộc khi US tạo mới hoặc thay đổi **hợp đồng mà bên ngoài tiêu thụ**:

| Loại | Ví dụ | Bắt buộc |
|---|---|---|
| Endpoint HTTP | `GET /health`, `POST /predict`, `GET /version` | ✅ |
| Định dạng request/response | JSON body, mã lỗi | ✅ |
| Hàm/module công khai dùng chung | `src/vsl/heatmap.py: create_heatmap(...)` | ✅ |
| CLI / tham số dòng lệnh | `run_realtime.py --camera 1` | ✅ |
| Định dạng file trao đổi | CSV 93 cột | ✅ |
| Refactor thuần nội bộ, không đổi hợp đồng | đổi tên biến, tách file | ❌ (ghi `N/A` + lý do) |

Nếu US **không** rơi vào nhóm bắt buộc, vẫn phải ghi rõ trong báo cáo:
`API docs: N/A — lý do: ...` và được chủ dự án xác nhận.

---

## 2. Quy ước đặt tên

| Nội dung | Quy ước |
|---|---|
| File của một US | `US-0XX.md` (một file/US, dù có nhiều endpoint) |
| Bộ khung | `_TEMPLATE.md` (không sửa, chỉ copy) |
| File README | `README.md` (file này) |

Không dùng tên khác. Không tạo thư mục con khi chưa có nhu cầu thật.

---

## 3. Vòng đời trạng thái

```
DRAFT
  → ANALYSIS_READY       (đã đủ 17 mục + self-review)
  → NEEDS_CLARIFICATION  (thiếu thông tin, chặn thiết kế)
  → BLOCKED              (không truy cập được repo/dependency)
```

- Chỉ file ở `ANALYSIS_READY` mới được dùng làm căn cứ viết test/code.
- Không dùng trạng thái `DONE`.

---

## 4. Quy trình 9 phase (áp dụng khi soạn `US-0XX.md`)

| Phase | Nội dung | Bắt buộc |
|---|---|---|
| 1 | Repository Discovery — cấu trúc thật, module liên quan | ✅ |
| 2 | Story Analysis — actor, goal, resource, action, BR, AC | ✅ |
| 3 | Architecture & Domain Analysis — entity/service hiện có | ✅ |
| 4 | Existing API & Security Analysis | ✅ |
| 5 | Business Rules & Acceptance Criteria → rule kiểm thử được | ✅ |
| 6 | API Gap Analysis — REUSE / MODIFY / NEW / NO API NEEDED | ✅ |
| 7 | API Design — request, response, status, validation, error | ✅ |
| 8 | Tạo `US-0XX.md` từ `_TEMPLATE.md`, đủ 17 mục | ✅ |
| 9 | Self-review theo checklist mục 5 dưới đây | ✅ |

Không được nhảy sang test/code khi phase 8–9 chưa xong.

---

## 5. Checklist self-review (phải tick hết)

- [ ] Story được cover đầy đủ, không bịa yêu cầu
- [ ] Mọi AC đều được map sang endpoint/hành vi + test
- [ ] Đã kiểm tra API hiện có, không tạo endpoint trùng
- [ ] Request không chứa `actorId`/`organizationId` nếu server tự suy ra được
- [ ] Response/error khớp convention hiện có (hoặc nêu rõ đề xuất + lý do nếu chưa có)
- [ ] Validation đầy đủ (kiểu dữ liệu, biên, số lượng)
- [ ] Authorization rõ ràng theo role A01–A04
- [ ] Organization scope kết luận rõ (kể cả khi `N/A`)
- [ ] Audit impact kết luận rõ
- [ ] Data model impact kết luận rõ
- [ ] Mọi Business Rule liên quan được dẫn chứng (BR-001…BR-026)
- [ ] Có Test Scenarios cho happy path + validation + lỗi + regression
- [ ] Open Questions đã nêu hết (nếu còn chặn → `NEEDS_CLARIFICATION`)
- [ ] **Không** sửa source code khi soạn tài liệu
- [ ] Trạng thái cuối là `ANALYSIS_READY` hoặc `NEEDS_CLARIFICATION`/`BLOCKED`

---

## 6. Cách dùng nhanh

```powershell
Copy-Item docs\api\_TEMPLATE.md docs\api\US-0XX.md
# điền 17 mục, tự review theo mục 5, rồi chờ chủ dự án duyệt
```

Sau khi `ANALYSIS_READY` và được duyệt → mới sang bước viết test (WORKFLOW bước 5).

---

## 7. Quy tắc bất biến

1. **Docs trước, code sau.** Không có `US-0XX.md` = không được viết test/code cho US đó.
2. **Một bản duy nhất.** Sửa API phải sửa chính file docs, không viết docs thứ hai.
3. **Không bịa.** Thiếu bằng chứng → ghi `UNKNOWN` hoặc `CẦN XÁC NHẬN`.
4. **Không giấu thay đổi.** Nếu thiết kế API buộc đổi hành vi cũ, ghi rõ ở mục 5 và 15.
