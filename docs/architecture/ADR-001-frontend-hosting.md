# ADR-001: Lựa Chọn Nền Tảng Lưu Trữ Giao Diện Web Tĩnh (Frontend Hosting)

- **Trạng thái:** ĐÃ CHỐT — Phương án D (Cloudflare Pages). Backend đặt tại Microsoft Azure Container Apps.
- **Ngày:** 2026-10-15 (Cập nhật chuẩn hóa hạ tầng Azure 2026-11-06)
- **Liên quan:** Kế hoạch 2 tuần và các hợp đồng tích hợp API trong ../planning/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md

---

## 1. Bối cảnh và Yêu cầu

Backend của hệ thống chạy trên dịch vụ Microsoft Azure Container Apps.

Giao diện người dùng (Frontend) được thiết kế tối giản dưới dạng trang web tĩnh HTML/CSS/JavaScript:
- Chụp ảnh trực tiếp từ webcam hoặc chọn tệp tin ảnh từ máy tính.
- Gửi dữ liệu ảnh qua giao thức HTTPS POST tới endpoint /predict của dịch vụ backend.
- Hiển thị kết quả ký tự dự đoán, độ tin cậy và các nhãn gợi ý.

Bốn phương án xem xét:

| Phương án | Nền tảng lưu trữ Frontend | Cơ chế phân phối | Số mục tiêu triển khai |
|---|---|---|---|
| A | Firebase Hosting | Mạng phân phối Firebase CDN | 2 (Frontend và Backend riêng) |
| B | Cùng container Backend | Phục vụ trực tiếp từ FastAPI | 1 (Duy nhất 1 container) |
| C | Vercel | Mạng phân phối Edge Vercel | 2 (Frontend và Backend riêng) |
| D | Cloudflare Pages | Mạng phân phối Cloudflare CDN | 2 (Frontend và Backend riêng) |

---

## 2. Dữ liệu Đối Chiếu Các Nền Tảng

| Tiêu chí | Firebase Hosting | Vercel (Hobby) | Cloudflare Pages (Free) |
|---|---|---|---|
| Băng thông miễn phí | 360 MB/ngày (~10.8 GB/tháng) | Khoảng 100 GB/tháng | Không giới hạn băng thông trong định mức |
| Số lượt build miễn phí | Giới hạn theo CLI/CI | Theo định mức gói cá nhân | 500 build/tháng, 1 build đồng thời |
| Preview deploy mỗi PR | Cần cấu hình thủ công vào CI | Tự động sinh URL xem trước | Tự động sinh URL xem trước cho mọi nhánh |
| Tên miền riêng và chứng chỉ SSL | Miễn phí | Miễn phí | Miễn phí, hỗ trợ nhiều tên miền tùy biến |
| Giới hạn kích thước tệp tin | Theo chuẩn Firebase | Theo chuẩn Vercel | Tối đa 25 MiB mỗi tệp tin |
| Ràng buộc mục đích sử dụng | Không hạn chế | Giới hạn phi thương mại | Không hạn chế |
| Tính năng khôi phục (Rollback) | Có | Có | Có, hỗ trợ rollback tức thì |

---

## 3. Cơ Chế Kết Nối Giữa Frontend Và Backend

Khi frontend đặt tại máy chủ riêng biệt (Cloudflare Pages) và backend đặt tại Azure Container Apps, hai thành phần có tên miền khác nhau:
- Backend: https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io
- Frontend: Tên miền phân phối của Cloudflare Pages (*.pages.dev)

Quy định cấu hình bắt buộc:
1. Backend kích hoạt CORSMiddleware cho phép nguồn gốc (origin) từ Cloudflare Pages.
2. Trình duyệt gọi trực tiếp API qua URL đầy đủ của backend Azure Container Apps.
3. Nếu cần tích hợp proxy qua Cloudflare Pages, sử dụng Pages Functions để chuyển tiếp request.

---

## 4. Phân Tích Các Tiêu Chí Kỹ Thuật

### 4.1. Tác động của thời gian khởi động mô hình tới trải nghiệm người dùng

- Phương án B (Cùng container): Mã HTML/CSS/JS nằm trong container. Khi container khởi động lại hoặc có độ trễ ban đầu, người dùng mở trang web sẽ thấy màn hình trắng trong nhiều giây.
- Phương án A, C, D (Host tĩnh riêng biệt): Giao diện web được tải về tức thì từ mạng phân phối nội dung (CDN). Trạng thái chờ chỉ xảy ra khi người dùng bấm gửi ảnh dự đoán, lúc này giao diện đã sẵn sàng hiển thị thanh tiến trình (spinner) rõ ràng.

Kết luận: Phương án A, C, D vượt trội hơn Phương án B về mặt trải nghiệm giao diện ban đầu.

### 4.2. Rủi ro lệch phiên bản (Version Skew)

- Khi frontend và backend triển khai độc lập, có thể xuất hiện độ lệch ngắn hạn giữa giao diện và định dạng API trong quá trình nâng cấp.
- Giải pháp: Giữ cố định hợp đồng giao tiếp API POST /predict và triển khai backend trước khi triển khai frontend.

### 4.3. Tính năng xem trước (Preview Deployment) trên từng Pull Request

- Cloudflare Pages và Vercel tự động tạo một URL xem trước độc lập cho từng Pull Request.
- Thành viên xét duyệt có thể trực tiếp trải nghiệm và kiểm tra giao diện trên trình duyệt trước khi hợp nhất mã nguồn vào nhánh chính.

### 4.4. Chi phí và hạn mức sử dụng

Cloudflare Pages cung cấp chính sách băng thông mở rộng và 500 lần build miễn phí mỗi tháng, đáp ứng hoàn toàn nhu cầu phát triển và vận hành thực tế mà không phát sinh chi phí.

---

## 5. Tổng Hợp Đánh Giá

| Tiêu chí | Trọng số | A (Firebase) | B (Cùng container) | C (Vercel) | D (Cloudflare) |
|---|---|---|---|---|---|
| Tốc độ tải trang ban đầu | Cao | Tốt | Thấp (chờ nạp) | Tốt | Tốt |
| Preview deploy mỗi PR | Cao | Cần tự làm CI | Không hỗ trợ | Rất tốt | Rất tốt |
| Giá trị thực hành CI/CD | Cao | Trung bình | Thấp | Rất tốt | Rất tốt |
| Tính độc lập thành phần | Cao | Tốt | Phụ thuộc | Tốt | Tốt |
| Băng thông miễn phí | Trung bình | Thấp (360 MB/ngày) | Theo backend | Khá | Rất cao |
| Cấu hình CORS | Thấp | Cần cấu hình | Không cần | Cần cấu hình | Cần cấu hình |

---

## 6. Quyết Định Chính Thức

Hệ thống lựa chọn **Phương án D — Cloudflare Pages** làm nền tảng lưu trữ giao diện người dùng tĩnh, kết nối với Backend tại **Microsoft Azure Container Apps**.

Lý do lựa chọn:
1. Băng thông phân phối rộng rãi, tối ưu cho việc tải tài nguyên hình ảnh.
2. Hỗ trợ tự động tạo bản xem trước (Preview Deployment) cho mọi Pull Request.
3. Không phát sinh chi phí, tuân thủ đúng mục tiêu ngân sách 0 VNĐ.

Các biện pháp kỹ thuật bắt buộc:
1. **Warm-up ping:** Khi người dùng mở giao diện, mã JavaScript tự động gửi một request ngầm tới endpoint /health của backend để khởi động sẵn sàng mô hình trước khi người dùng chụp ảnh.
2. **Cố định hợp đồng API:** Duy trì cấu trúc JSON đầu ra của endpoint /predict ổn định xuyên suốt các lần cập nhật.
3. **Thứ tự triển khai:** Triển khai dịch vụ backend lên Azure Container Apps trước, sau đó mới cập nhật giao diện web lên Cloudflare Pages.
4. **Tự động hóa qua GitHub Actions:** Toàn bộ quy trình đóng gói và phát hành giao diện được điều phối tập trung qua GitHub Actions kết hợp công cụ wrangler.
