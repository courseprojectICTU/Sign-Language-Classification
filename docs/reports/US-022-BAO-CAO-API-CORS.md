# Báo cáo kiểm tra API và CORS — US-022

- **Ngày kiểm tra:** 2026-11-07
- **Nhánh:** `feature/US-022`
- **Mục đích:** Điều tra thông báo “Không thể kết nối đến dịch vụ” khi người dùng bấm **Dự đoán**.
- **Phạm vi:** Frontend US-022, API staging, kiểm tra API trực tiếp và trình duyệt. Không sửa cấu hình CORS/US-025.

## 1. Kết luận

Nguyên nhân gốc là **API staging chưa cho phép CORS từ frontend origin**
`http://127.0.0.1:8765`. API vẫn hoạt động và phân loại được ảnh khi gọi trực tiếp,
nhưng trình duyệt không cho JavaScript đọc response vì response không có
`Access-Control-Allow-Origin`.

Đây là việc cần xử lý trong **US-025**, không phải lỗi nhận diện ảnh và không phải
lỗi URL trong US-022. Chưa push hoặc merge thay đổi nào.

## 2. Cấu hình URL và trạng thái dịch vụ

`web/config.js` đặt API base URL mặc định:

```text
https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io
```

`web/app.js` gửi `POST /predict` với `multipart/form-data`, trường `file`.
Trình duyệt chạy từ:

```text
http://127.0.0.1:8765/
```

Kiểm tra trực tiếp:

```text
GET https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io/health
HTTP 200
{"status":"ok","model_loaded":true,"model_version":"v1.0"}
```

Kết luận: backend staging đang hoạt động và model đã nạp.

## 3. Kiểm tra ảnh bằng API thật

Ảnh `web/test_sign.jpg` có khuôn mặt và hai bàn tay. Gửi trực tiếp bằng `curl.exe`
đến staging (không qua trình duyệt):

```powershell
curl.exe -sS -i `
  -F "file=@D:\Sign-Language-Classification\web\test_sign.jpg;type=image/jpeg" `
  "https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io/predict" `
  -H "Origin: http://127.0.0.1:8765"
```

Kết quả thực tế: **HTTP 200**.

```json
{
  "status": "ok",
  "detected": true,
  "letter": "d",
  "confidence": 0.9618671536445618,
  "top_k": [
    {"letter": "d", "confidence": 0.9618671536445618},
    {"letter": "k", "confidence": 0.029042797163128853},
    {"letter": "s", "confidence": 0.005681438837200403}
  ],
  "has_hand": true,
  "has_face": true,
  "message": null,
  "model_version": "v1.0"
}
```

Response này xác nhận inference thật thành công. Nhãn `d` là đầu ra của model; kiểm tra
này không xác nhận ý định ký hiệu của người trong ảnh.

## 4. Bằng chứng trình duyệt và CORS

Playwright mở frontend thật tại `http://127.0.0.1:8765/`, chọn ảnh trên và bấm
**Dự đoán**. Cấu hình client đọc đúng API base URL nêu trên. Network/Console ghi nhận:

- Request method: `POST`
- URL: `https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io/predict`
- Request content type: `multipart/form-data; boundary=...`
- Request thất bại tại trình duyệt với `net::ERR_FAILED`; JavaScript không nhận được
  response HTTP để đọc.
- Console:

  ```text
  blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
  ```

- Frontend hiển thị thông báo lỗi kết nối; không hiển thị kết quả dự đoán.

Kiểm tra preflight thủ công:

```powershell
curl.exe -sS -i -X OPTIONS `
  "https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io/predict" `
  -H "Origin: http://127.0.0.1:8765" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: content-type"
```

Kết quả: **HTTP 405 Method Not Allowed**, `Allow: POST`, không có
`Access-Control-Allow-Origin`.

Trong lần gọi từ browser này, network cho thấy POST bị chặn; không ghi nhận OPTIONS tự
động trước POST. Dù vậy, preflight thủ công cũng thất bại. Không nhầm lẫn HTTP 405
preflight với lỗi API inference: POST trực tiếp bằng curl trả 200.

## 5. Yêu cầu thay đổi cho US-025

Triển khai `CORSMiddleware` ở backend và cho phép đúng các origin đã được phê duyệt:

- Origin Cloudflare Pages thực tế và custom domain nếu có.
- `http://127.0.0.1:8765` chỉ cho môi trường phát triển cục bộ.
- Không dùng wildcard (`*`) hoặc wildcard subdomain.
- Cho phép method `POST` cho US-022; thêm `GET` nếu tích hợp `/health` từ frontend.
- Cho phép request header `Content-Type`.
- Đặt `allow_credentials=False`; API hiện không yêu cầu cookie/token.
- Đảm bảo response tới origin được allowlist có `Access-Control-Allow-Origin` khớp
  chính xác và middleware xử lý preflight OPTIONS.

Ví dụ cấu hình mục tiêu (thay placeholder bằng origin triển khai đã xác minh):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "https://<cloudflare-pages-origin-da-xac-minh>",
        # "https://<custom-domain-da-xac-minh>",
    ],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
```

Thay đổi này thuộc US-025. Báo cáo không thêm code hoặc thay đổi cấu hình US-025 vào
nhánh US-022.

## 6. Trạng thái nghiệm thu

| Acceptance Criteria | Trạng thái | Căn cứ |
|---|---|---|
| AC-022-01 — Upload/chụp ảnh và hiển thị ký tự cùng độ tin cậy | **BLOCKED** | Inference staging trực tiếp thành công với `d`, confidence `0.961867`, nhưng browser không đọc được response do thiếu CORS header nên chưa nghiệm thu luồng giao diện end-to-end. |
| AC-022-02 — Loading trong cold start, không báo lỗi sớm hoặc để trang trắng | **BLOCKED** | Test tự động có response trì hoãn dùng API stub đã qua; chưa kiểm tra cold start staging thật từ browser. CORS phải hoạt động trước. |

## 7. Kiểm thử tự động

Các kết quả gần nhất đã quan sát:

| Lệnh | Kết quả |
|---|---|
| `& ".\.venv\Scripts\python.exe" -m pytest tests -q` | **87 passed**, 8 warnings |
| `& ".\.venv\Scripts\python.exe" -m pytest tests/test_us022_web.py tests/test_labels.py -q` | **18 passed** |

Các test frontend dùng API stub để kiểm thử hiển thị response và trạng thái loading;
chúng không thay thế kiểm tra CORS hoặc inference staging thật.

## 8. Bước nghiệm thu tiếp theo

1. Hoàn thành và triển khai CORS trong US-025.
2. Xác nhận `OPTIONS /predict` từ origin đã allowlist trả response CORS hợp lệ.
3. Mở frontend từ chính origin đó; bằng Playwright tải `test_sign.jpg`, bấm **Dự đoán**
   và xác nhận giao diện hiển thị nhãn cùng confidence từ response API thật.
4. Để nghiệm thu AC-022-02, chuẩn bị staging ở trạng thái cold start theo quy trình vận
   hành được duyệt; không tự ý scale hạ tầng từ nhánh US-022. Xác nhận loading xuất hiện,
   trang không trắng/không báo lỗi sớm, rồi response thật được hiển thị.
5. Chạy lại test suite và lưu output cùng ảnh chụp UI/Network làm bằng chứng.

## 9. Trạng thái Git và phạm vi

- Không push hoặc merge.
- Không commit thư mục `infra/`.
- Không commit ảnh kiểm thử `web/test_sign.jpg`.
- Các mục chưa theo dõi trên working tree cần được giữ nguyên và loại khỏi commit nếu
  tạo PR US-022.
