# Báo cáo thực hiện — US-012 Nạp model một lần ngoài request handler

> **Trạng thái:** PASS — chủ dự án xác nhận nghiệm thu ngày 2026-11-08
> **Epic:** EPC-03 · **Nhánh:** `feature/US-012`
> **Business Rule:** BR-011 — Single Model Load per Container
> **API docs:** N/A — US-012 củng cố lifecycle nội bộ và log vận hành, không thay đổi hợp đồng tiêu thụ của `/health` hoặc `/predict`. Chủ dự án đã duyệt quyết định này trước khi viết test.

## 1. Mục tiêu và phạm vi

Đảm bảo model được nạp trong sự kiện FastAPI lifespan một lần cho mỗi lần khởi động ứng dụng, được giữ ở `app.state.model` để phục vụ request, và ghi thời gian nạp để hỗ trợ đối chiếu cold start.

Không thay đổi pipeline dự đoán, schema/status HTTP, hay cấu hình triển khai. Backlog không quy định ngưỡng thời gian phản hồi, do đó báo cáo không đặt thêm ngưỡng hiệu năng.

## 2. Story, task và acceptance criteria

| ID | Yêu cầu | Kết quả |
|---|---|---|
| US-012 | Model chỉ nạp một lần khi container khởi động, không nạp lại theo request | Đạt; lifespan gán model vào `app.state.model` và các request dùng lại instance đó |
| TSK-019 | Nạp model trong sự kiện startup và lưu ở phạm vi ứng dụng | Đạt; kiểm thử kích hoạt lifespan và xác minh readiness |
| TSK-020 | Ghi log thời gian nạp model | Đạt; log cả thành công và thất bại với `duration_ms` |
| AC-012-01 (Critical) | Gửi 10 request `/predict`; log chứng minh model chỉ nạp đúng một lần | PASS; test xác minh `load_model` được gọi đúng một lần, xử lý đủ 10 request và có log duration hợp lệ |

## 3. Thay đổi

| File | Nội dung |
|---|---|
| `src/vsl/service.py` | Đo thời gian quanh thao tác `load_model` bằng đồng hồ monotonic `perf_counter`; thêm `duration_ms` vào log thành công và thất bại. Cơ chế load vẫn nằm trong lifespan; response/API không đổi. |
| `tests/test_us012_model_lifecycle.py` | Kiểm thử lifespan thật bằng `TestClient`, readiness sau startup, 10 request dự đoán dùng chung model, log duration, và health `503` khi load thất bại. Model, MediaPipe extraction và preprocessing được mock để test không cần tải model lớn hoặc phụ thuộc detector thực. |

## 4. Bằng chứng kiểm thử

Test-first được thực hiện: trước khi sửa code, test lifecycle đã đỏ vì thiếu log `duration_ms` (`1 failed, 1 passed`); sau thay đổi, test xanh.

| Phạm vi | Lệnh | Kết quả |
|---|---|---|
| US-012 + health + predict | `& ".\.venv\Scripts\python.exe" -m pytest tests/test_us012_model_lifecycle.py tests/test_health.py tests/test_predict.py -q` | **19 passed**, 4 warnings, 15.72s |
| Toàn bộ suite | `& ".\.venv\Scripts\python.exe" -m pytest tests -v` | **75 passed**, 8 warnings, 49.22s |
| Kiểm tra whitespace của commits | `git diff --check HEAD~2..HEAD` | Thành công, không có lỗi |

Các cảnh báo trên là cảnh báo phụ thuộc/runtime hiện có; không có test thất bại.

## 5. Giới hạn xác minh

Kiểm thử tích hợp kích hoạt đúng ASGI lifespan và gửi 10 request trên `TestClient`; nó mock `load_model` để cô lập lifecycle và không đo cold-start thực tế trên Azure. Không có ngưỡng latency trong AC-012-01. Dockerfile/triển khai container đã được nghiệm thu ở US-010; US-012 không thay đổi cấu hình container.

## 6. Commits triển khai và nghiệm thu

- `51ae37d test(us-012): cover model startup lifecycle`
- `f0f293c feat(us-012): log model startup duration`
- Chủ dự án xác nhận PASS sau khi xem kết quả toàn bộ suite.
- Các thay đổi đang ở `feature/US-012`; chưa push hoặc mở PR.
