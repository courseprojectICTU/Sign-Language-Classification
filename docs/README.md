# HỆ THỐNG TÀI LIỆU DỰ ÁN (DOCUMENTATION INDEX)

Tài liệu này cung cấp sơ đồ phân cấp và mục lục tra cứu toàn bộ tài liệu kỹ thuật của dự án **Sign Language Classification v1.0**.

---

## 1. Sơ Đồ Cấu Trúc Thư Mục Tài Liệu

```text
docs/
├── README.md                          # Sơ đồ và mục lục tra cứu toàn bộ tài liệu (tệp này)
├── architecture/                      # Kiến trúc hệ thống & Quyết định kỹ thuật (ADR)
│   ├── ADR-001-frontend-hosting.md    # Quyết định chọn Cloudflare Pages cho giao diện tĩnh
│   └── THONG_TIN_DE_TAI.txt           # Tổng quan thông tin đề tài, mục tiêu và công nghệ
├── planning/                          # Kế hoạch phát triển & Quản trị Backlog
│   ├── KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md      # Kế hoạch chi tiết 2 tuần (10 ngày)
│   ├── KE-HOACH-CHUYEN-DOI-HA-TANG-AZURE.md   # Kế hoạch chuyển đổi tài liệu sang Azure
│   └── product-backlog-cicd-2-tuan.xlsx       # Product Backlog (Epics, Stories, AC, Tasks, Rules)
├── process/                           # Quy trình phát triển & Đảm bảo chất lượng
│   ├── WORKFLOW.md                    # Quy trình phát triển bắt buộc cho từng User Story
│   ├── QUY-TRINH-REVIEW-PULL-REQUEST.md       # Quy trình 5 bước thẩm định Pull Request
│   └── QUY-TRINH-REVIEW-PULL-REQUEST.docx     # Bản tài liệu định dạng Word
├── infrastructure/                    # Hạ tầng Đám mây, Triển khai & Vận hành
│   ├── HO-SO-BAN-GIAO-HA-TANG.md      # Hồ sơ thông số kỹ thuật hạ tầng Staging Azure
│   ├── HUONG-DAN-TRIEN-KHAI-AZURE.md  # Hướng dẫn đóng gói và triển khai Azure Container Apps
│   └── HUONG-DAN-CAU-HINH-TEN-MIEN-AZURE.md   # Hướng dẫn cấu hình tên miền vsl-vietnam.azurewebsites.net
├── api/                               # Hợp đồng giao tiếp API & Báo cáo kỹ thuật (API Contracts)
│   ├── README.md                      # Quy ước viết và thẩm định tài liệu API
│   ├── _TEMPLATE.md                   # Khung chuẩn 17 mục cho tài liệu API
│   ├── US-013.md                      # Hợp đồng CLI và báo cáo đo lường Cold Start Staging
│   └── US-001.md ... US-016.md        # Đặc tả chi tiết từng User Story
├── reports/                           # Báo cáo tổng hợp đồ án
│   ├── US-012-BAO-CAO-THUC-HIEN.md    # Báo cáo thực hiện và nghiệm thu model lifecycle
│   └── TAI_LIEU_BAO_CAO.doc           # Báo cáo tổng hợp môn học định dạng Word
└── backup_gcp_docs/                   # Bản sao lưu tài liệu gốc trước khi chuyển đổi hạ tầng
```

---

## 2. Mục Lục Tra Cứu Theo Nhóm Chức Năng

### 2.1. Nhóm Kiến Trúc Hệ Thống (`docs/architecture/`)
- [ADR-001-frontend-hosting.md](architecture/ADR-001-frontend-hosting.md): Phân tích 4 phương án lưu trữ frontend (Firebase, cùng container, Vercel, Cloudflare Pages), lý do lựa chọn Cloudflare Pages kết hợp backend Azure Container Apps.
- [THONG_TIN_DE_TAI.txt](architecture/THONG_TIN_DE_TAI.txt): Bản tóm tắt đề tài phục vụ môn học Điện toán đám mây.

### 2.2. Nhóm Kế Hoạch & Quản Trị (`docs/planning/`)
- [KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md](planning/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md): Bản kế hoạch lộ trình 10 ngày, chia thành 4 mảng công việc kỹ thuật, tiêu chí nghiệm thu (DoD) và thiết kế CI/CD.
- [KE-HOACH-CHUYEN-DOI-HA-TANG-AZURE.md](planning/KE-HOACH-CHUYEN-DOI-HA-TANG-AZURE.md): Bản kế hoạch 3 giai đoạn chuyển đổi toàn bộ tài liệu hệ thống từ Google Cloud sang Microsoft Azure.
- [product-backlog-cicd-2-tuan.xlsx](planning/product-backlog-cicd-2-tuan.xlsx): Bảng tính quản trị Backlog gồm 7 sheet: 1ProductOwner, 2User Roles, Epics, Product Backlog, Acceptance Criteria, Task, Business Rules.

### 2.3. Nhóm Quy Trình Vận Hành (`docs/process/`)
- [WORKFLOW.md](process/WORKFLOW.md): Quy trình 8 bước bắt buộc cho mọi User Story: Đồng bộ develop -> Đọc backlog -> Tóm tắt US -> Phân tích AC -> Viết tài liệu API -> Viết test trước code -> Làm từng task -> Nghiệm thu.
- [QUY-TRINH-REVIEW-PULL-REQUEST.md](process/QUY-TRINH-REVIEW-PULL-REQUEST.md): Hướng dẫn 5 bước thẩm định Pull Request dành cho người duyệt mã nguồn.

### 2.4. Nhóm Hạ Tầng & Triển Khai Đám Mây (`docs/infrastructure/`)
- [HO-SO-BAN-GIAO-HA-TANG.md](infrastructure/HO-SO-BAN-GIAO-HA-TANG.md): Hồ sơ kỹ thuật bàn giao môi trường Staging Azure Container Apps (Resource Group, URL, ACR, Service Principal, biến môi trường).
- [HUONG-DAN-TRIEN-KHAI-AZURE.md](infrastructure/HUONG-DAN-TRIEN-KHAI-AZURE.md): Hướng dẫn chi tiết từng bước đóng gói Docker image, đẩy lên Azure Container Registry và cấu hình Azure Container Apps.
- [HUONG-DAN-CAU-HINH-TEN-MIEN-AZURE.md](infrastructure/HUONG-DAN-CAU-HINH-TEN-MIEN-AZURE.md): Hướng dẫn cấu hình tên miền dịch vụ `vsl-vietnam.azurewebsites.net`.

### 2.5. Nhóm Hợp Đồng API & Báo Cáo Kỹ Thuật (`docs/api/`)
- [README.md](api/README.md): Quy ước đặt tên, 9 phase xây dựng tài liệu API và checklist thẩm định.
- Chứa các hợp đồng kỹ thuật chi tiết: `US-001.md` (tạo heatmap), `US-002.md` (nhãn 23 ký tự), `US-003.md` (cấu hình đường dẫn), `US-004.md` (phụ thuộc Linux), `US-005.md` (/health), `US-006.md` (/predict), `US-007.md` (trạng thái thiếu landmark), `US-008.md` (/version), `US-010.md` (đóng gói Dockerfile), `US-013.md` (hợp đồng CLI và báo cáo đo lường cold start staging), `US-015.md` (hợp đồng 93 cột), `US-016.md` (đối chiếu tham chiếu).

### 2.6. Nhóm Báo Cáo Tổng Hợp (`docs/reports/`)
- [US-012-BAO-CAO-THUC-HIEN.md](reports/US-012-BAO-CAO-THUC-HIEN.md): Ghi nhận phạm vi, task, bằng chứng kiểm thử, quyết định API docs N/A và nghiệm thu US-012.
- [TAI_LIEU_BAO_CAO.doc](reports/TAI_LIEU_BAO_CAO.doc): Tài liệu báo cáo hoàn chỉnh đồ án môn học Điện toán đám mây.
