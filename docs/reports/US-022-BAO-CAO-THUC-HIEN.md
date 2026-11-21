# Báo cáo thực hiện User Story US-022

## 1. Thông tin chung

- **User Story:** US-022 — Trang web tải hoặc chụp ảnh và hiển thị kết quả
- **Epic:** EPC-06 — Giao diện Web & Host tĩnh
- **Nhánh:** `feature/US-022`
- **Nhánh đích dự kiến:** `develop`
- **Thời gian thực hiện:** 2026-11-07
- **Trạng thái:** Hoàn thành phần giao diện và kiểm thử tự động; **chưa nghiệm thu đầy đủ hai Acceptance Criteria** do CORS staging chưa được cấu hình (phụ thuộc US-025).
- **Push / merge:** Chưa thực hiện.

## 2. Mục tiêu và phạm vi

US-022 xây dựng trang web tĩnh cho phép người dùng chọn hoặc chụp ảnh, xem trước,
gửi ảnh đến API dự đoán hiện có và xem ký tự cùng độ tin cậy. Trang cũng hiển thị
trạng thái tải, hướng dẫn chụp và danh sách 23 ký tự được hỗ trợ.

Phạm vi không bao gồm thay đổi API/pipeline backend, warm-up `/health` (US-023),
triển khai Cloudflare Pages (US-024) hoặc cấu hình CORS (US-025). Giao diện gọi
`POST /predict` bằng `multipart/form-data`, trường `file`.

## 3. Công việc đã thực hiện

| Task | Công việc | Kết quả |
|---|---|---|
| TSK-039 | Dựng trang tĩnh; chọn ảnh, xem trước, mở/tắt camera và chụp ảnh | Có các thao tác tải ảnh/camera, preview; xử lý trạng thái camera và tránh mở nhiều stream đồng thời |
| TSK-040 | Kết nối API và hiển thị kết quả | Gửi ảnh khi người dùng bấm Dự đoán; có loading; hiển thị nhãn và confidence; xử lý `no_hand`, `no_face`, lỗi HTTP và lỗi mạng |
| TSK-041 | Kiểm tra nhiều trình duyệt và màn hình nhỏ | Playwright chạy Chromium, Microsoft Edge, Firefox; kiểm tra layout ở viewport 375×812 |
| TSK-042 | Danh sách ký tự và hướng dẫn chụp | Render đủ 23 ký tự theo thứ tự nguồn Python; thêm hướng dẫn; xử lý lỗi tải asset và trạng thái `hidden` của preview |
| Kiểm thử bổ sung | Bảo vệ hành vi preview/camera và response API | Có test hồi quy cho preview ẩn ban đầu, chờ camera preview, không mở trùng camera, `no_hand`/`no_face`, HTTP 400/503 và lỗi mạng |

### Các thay đổi chính

| Nhóm | File | Nội dung |
|---|---|---|
| Giao diện | `web/index.html`, `web/styles.css` | Khung trang, vùng chọn/chụp, preview, loading, kết quả, responsive, danh sách ký tự và hướng dẫn |
| Hành vi frontend | `web/app.js`, `web/config.js` | Cấu hình API URL, `POST /predict`, xử lý thành công/nghiệp vụ/lỗi, camera lifecycle, tải nhãn |
| Nguồn nhãn | `scripts/generate_web_labels.py`, `web/labels.json` | Sinh asset JSON từ `src/vsl/labels.py`, tránh duy trì nguồn nhãn viết tay thứ hai |
| Kiểm thử | `tests/test_us022_web.py`, `requirements-dev.txt` | Playwright acceptance/regression tests và dependency Playwright |
| Đặc tả | `docs/api/US-022.md` | Hợp đồng frontend/API, AC mapping và test scenarios |

Không sửa `src/vsl/service.py` hoặc cấu hình CORS trong nhánh US-022.

## 4. Hợp đồng API và kết quả kiểm tra ảnh thật

Frontend dùng URL staging mặc định:

```text
https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io
```

`POST /predict` nhận `multipart/form-data` có trường bắt buộc `file`. API giải mã ảnh
JPEG/PNG, yêu cầu MediaPipe phát hiện ít nhất một bàn tay và một khuôn mặt trong cùng
ảnh; từ đó tạo 63 tọa độ landmark tay và 30 tọa độ khuôn mặt (tổng 93). Thiếu một
trong hai detection thì trả trạng thái `no_hand`/`no_face`, không phân loại.

Ngày 2026-11-07, ảnh `web/test_sign.jpg` được gửi trực tiếp bằng `curl.exe` đến staging:

- `GET /health`: HTTP 200, `model_loaded: true`, model `v1.0`.
- `POST /predict`: HTTP 200, `status: "ok"`, `detected: true`,
  `has_hand: true`, `has_face: true`.
- Model trả `letter: "d"` với `confidence: 0.9618671536445618`.
- Đây là inference thật; kết quả không xác nhận người trong ảnh có chủ ý tạo ký hiệu `d`.

Ví dụ lệnh PowerShell:

```powershell
curl.exe -sS -i `
  -F "file=@D:\Sign-Language-Classification\web\test_sign.jpg;type=image/jpeg" `
  "https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io/predict"
```

## 5. Kiểm thử và minh chứng

### 5.1. Kiểm thử tự động

| Bộ kiểm thử | Lệnh | Kết quả |
|---|---|---|
| Toàn bộ dự án | `& ".\.venv\Scripts\python.exe" -m pytest tests -q` | **87 passed**, 8 warnings, 0 failed |
| US-022 và nhãn | `& ".\.venv\Scripts\python.exe" -m pytest tests/test_us022_web.py tests/test_labels.py -q` | **18 passed**, 0 failed |
| Regression baseline | `& ".\.venv\Scripts\python.exe" -m pytest tests/test_pipeline_baseline.py -q` | **1 passed**, xác nhận baseline 23/23 ký tự |
| Browser matrix | Playwright trên Chromium, Edge và Firefox | **3 passed** |
| Cú pháp | `node --check web\app.js`; `py_compile` generator và test | PASS |
| Diff | `git diff --check develop...feature/US-022` | PASS, không phát hiện whitespace error |

Các Playwright acceptance test dùng API stub cho kết quả lặp lại; vì vậy những test
này xác nhận hành vi UI nhưng không thay thế kiểm thử browser-to-staging.

### 5.2. Kiểm tra CORS và browser-to-staging

Frontend local chạy tại `http://127.0.0.1:8765`. Playwright xác nhận trang lấy đúng
API URL và gửi:

```text
POST https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io/predict
Content-Type: multipart/form-data; boundary=...
```

Browser Console báo:

```text
blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
net::ERR_FAILED
TypeError: Failed to fetch
```

Giao diện hiển thị thông báo lỗi kết nối. Trong khi đó, cùng request ảnh gọi trực tiếp
bằng `curl.exe` thành công HTTP 200. Như vậy lỗi này không phải do API URL sai, API
ngừng hoạt động hay ảnh không nhận diện được.

Preflight thủ công từ origin frontend:

```powershell
curl.exe -sS -i -X OPTIONS `
  "https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io/predict" `
  -H "Origin: http://127.0.0.1:8765" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: content-type"
```

Kết quả: **HTTP 405 Method Not Allowed**, `Allow: POST`, không có
`Access-Control-Allow-Origin`. Đây là phụ thuộc US-025; không sửa chéo phạm vi trong
US-022. Bằng chứng chi tiết nằm trong [báo cáo API/CORS](./US-022-BAO-CAO-API-CORS.md).

## 6. Trạng thái Acceptance Criteria

| AC | Mức độ | Trạng thái | Bằng chứng / lý do |
|---|---|---|---|
| AC-022-01 — Chọn ảnh, dự đoán và hiển thị ký tự cùng độ tin cậy | Critical | **BLOCKED** | API thật phân loại ảnh thành công khi gọi trực tiếp; tuy nhiên browser không đọc được response staging vì thiếu CORS header nên chưa nghiệm thu luồng end-to-end trên giao diện. |
| AC-022-02 — Cold start có loading, không báo lỗi sớm và không để trang trắng | High | **BLOCKED** | Playwright xác nhận loading khi API stub được trì hoãn; chưa nghiệm thu cold start thật qua browser. Cần CORS hoạt động và môi trường staging cold-start được chuẩn bị theo quy trình được duyệt. |

## 7. Commit trên nhánh US-022

Các commit của nhánh, từ hợp đồng đến phần giao diện/kiểm thử:

| Commit | Nội dung |
|---|---|
| `b7d3daa` | Thêm hợp đồng API US-022 |
| `b151d48` | Thêm Playwright acceptance tests |
| `c885160` | Dựng giao diện chọn/chụp ảnh |
| `7cf4950` | Kết nối API và hiển thị kết quả |
| `1db9fe4` | Kiểm tra browser và mobile layout |
| `5d96061` | Cập nhật hợp đồng asset nhãn |
| `a73ad15`, `613d147` | Test cho generated label asset và render |
| `a774009`, `9895078` | Test hồi quy preview/camera |
| `0e55624` | Ngăn mở trùng camera |
| `9386680` | Test xử lý lỗi API và mạng |
| `7307013` | Hiển thị nhãn hỗ trợ và hướng dẫn chụp |

Tổng cộng **13 commit** được ghi nhận trên nhánh US-022. Nhánh chưa được push/merge
trong phiên nghiệm thu này.

## 8. Việc còn lại để nghiệm thu

1. Hoàn thành US-025: bật `CORSMiddleware` với allowlist origin chính xác; không dùng
   wildcard; cho phép `POST`, `Content-Type`, `allow_credentials=False`. Bổ sung `GET`
   nếu frontend tích hợp warm-up `/health` theo US-023.
2. Deploy backend đã cấu hình CORS và xác nhận `OPTIONS /predict` cùng response POST có
   `Access-Control-Allow-Origin` khớp origin đã cho phép.
3. Chạy Playwright từ origin frontend thật, gọi API staging không mock, và xác nhận UI
   hiển thị `letter`/confidence từ response inference.
4. Nghiệm thu AC-022-02 trong đợt cold start staging có chủ đích, được phê duyệt; xác
   nhận loading tồn tại đến khi request thật hoàn tất.
5. Chạy lại toàn bộ test suite và lưu bằng chứng browser/network sau khi tích hợp.

## 9. Trạng thái Git và phạm vi

- Đang ở nhánh `feature/US-022`; không push hoặc merge.
- Không commit thư mục `infra/`.
- `web/test_sign.jpg` là ảnh kiểm thử chưa theo dõi; không đưa vào commit nếu chưa được
  chủ dự án yêu cầu.
- Báo cáo này là tài liệu bổ sung; không thay đổi source code hay cấu hình US-025.
