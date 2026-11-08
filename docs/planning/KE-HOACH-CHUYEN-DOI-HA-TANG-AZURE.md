# Kế Hoạch Chuyển Đổi Tài Liệu Hệ Thống Từ Google Cloud Sang Microsoft Azure

Tài liệu xác định phạm vi, danh mục tài liệu bị ảnh hưởng, bảng ánh xạ công nghệ tương đương và lộ trình cập nhật toàn bộ tài liệu dự án sau khi chuyển đổi hạ tầng từ Google Cloud sang Microsoft Azure.

---

## 1. Bối Cảnh Và Lý Do Chuyển Đổi

Trong giai đoạn đầu, dự án dự kiến sử dụng hạ tầng Google Cloud (Cloud Run, Artifact Registry, Cloud Build). Tuy nhiên, chính sách kích hoạt tài khoản Google Cloud tại Việt Nam yêu cầu khoản đặt cọc xác minh 800.000 VNĐ.

Để đảm bảo mục tiêu tối ưu chi phí (0 VNĐ) và sử dụng tài nguyên ổn định phục vụ làm việc nhóm, hạ tầng Staging đã được chuyển đổi thành công sang **Microsoft Azure** thông qua gói tài trợ **Azure for Students** (hạn mức 100 USD credit, không yêu cầu thẻ tín dụng).

Dịch vụ Staging hiện đã hoạt động tại:  
`https://vsl-api.wittyground-02475ae2.eastasia.azurecontainerapps.io`

---

## 2. Bảng Ánh Xạ Công Nghệ Tương Đương

| Thành phần kỹ thuật | Google Cloud (Cũ) | Microsoft Azure (Mới) | Ghi chú chuyển đổi |
|---|---|---|---|
| Nền tảng Container Serverless | Google Cloud Run | Azure Container Apps (ACA) / Azure App Service | Hoạt động liên tục, cấu hình 1.0 vCPU, 2.0 GiB RAM, cổng 8080 |
| Kho lưu trữ Image | Google Artifact Registry | Azure Container Registry (ACR) | Tên kho hiện tại: `vslacr3795.azurecr.io` |
| Công cụ dòng lệnh quản trị | `gcloud` CLI | Azure CLI (`az`) | Đã cài đặt phiên bản 2.92.0 |
| Cơ chế xác thực CI/CD | Workload Identity Federation (WIF) / Service Account Key | Azure Service Principal + GitHub OIDC Federated Identity Credential | Keyless; lưu các identifier không nhạy cảm trong GitHub Actions Variables |
| Thu thập Log và Giám sát | Google Cloud Logging | Azure Monitor / Log Analytics Workspace | Workspace hiện tại: `workspace-rgvslstaging8lF4` |
| Quản lý ngân sách | Google Cloud Billing Budget | Azure Cost Management / Microsoft Azure Sponsorships | Kiểm tra số dư qua cổng quản lý tài trợ |

---

## 3. Trạng Thái Bản Sao Lưu (Backup)

Toàn bộ 12 file tài liệu gốc trước khi chuyển đổi đã được sao lưu vào thư mục:  
`docs/backup_gcp_docs/`

Danh mục file đã lưu trữ:
1. `docs/backup_gcp_docs/docs/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md`
2. `docs/backup_gcp_docs/docs/product-backlog-cicd-2-tuan.xlsx`
3. `docs/backup_gcp_docs/docs/ADR-001-frontend-hosting.md`
4. `docs/backup_gcp_docs/docs/THONG_TIN_DE_TAI.txt`
5. `docs/backup_gcp_docs/docs/WORKFLOW.md`
6. `docs/backup_gcp_docs/docs/QUY-TRINH-REVIEW-PULL-REQUEST.md`
7. `docs/backup_gcp_docs/docs/api/US-010.md`
8. `docs/backup_gcp_docs/docs/api/US-013.md`
9. `docs/backup_gcp_docs/docs/api/US-005.md`
10. `docs/backup_gcp_docs/docs/api/US-008.md`
11. `docs/backup_gcp_docs/AGENTS.md`
12. `docs/backup_gcp_docs/HUONG-DAN-CHAY.md`

*(Thư mục báo cáo LaTeX tại `report/` được giữ nguyên theo yêu cầu và sẽ cập nhật sau).*

---

## 4. Danh Mục Tài Liệu Cần Cập Nhật & Nội Dung Chi Tiết

### Nhóm 1: Tài liệu Kế hoạch và Bộ nhớ dự án
1. **`AGENTS.md` (Bộ nhớ dự án):**
   - Cập nhật mục 1: Mô tả dịch vụ backend và hạ tầng Azure Container Apps thay cho Cloud Run.
   - Cập nhật mục 3: Bổ sung các file hướng dẫn triển khai Azure, hồ sơ bàn giao hạ tầng.
   - Cập nhật mục 10: Trạng thái US-010 và US-013 đồng bộ với Azure Staging URL.
2. **`docs/planning/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md` (Kế hoạch 2 tuần):**
   - Cập nhật kiến trúc Tuần 1 và Tuần 2: Chuyển toàn bộ các mốc tham chiếu GCP/Cloud Run/Artifact Registry sang Azure Container Apps/ACR.
   - Cập nhật quy trình CD tại Mục 9: Sử dụng GitHub Action cho Azure Container Apps thay cho Google Cloud Run deploy.
3. **`docs/process/WORKFLOW.md` (Quy trình làm việc):**
   - Cập nhật tiêu chí nghiệm thu US liên quan đến Cloud Staging.

### Nhóm 2: Tài liệu Đặc tả Hợp đồng và Thiết kế
4. **`docs/architecture/ADR-001-frontend-hosting.md`:**
   - Cập nhật bảng so sánh lựa chọn host: Backend phục vụ tại Azure Container Apps kết hợp Frontend tĩnh tại Cloudflare Pages.
5. **`docs/architecture/THONG_TIN_DE_TAI.txt`:**
   - Cập nhật công nghệ triển khai: Azure Container Apps thay thế cho Cloud Run.
6. **`docs/api/US-010.md`:**
   - Cập nhật chuẩn đóng gói container tương thích nền tảng Azure Container Apps và ACR.
7. **`docs/api/US-013.md`:**
   - Cập nhật tiêu đề và mô tả: Benchmark Cold Start trên Azure Container Apps thay vì Cloud Run.
8. **`docs/api/US-005.md` và `docs/api/US-008.md`:**
   - Chuẩn hóa các trích dẫn về healthcheck probe và metadata phiên bản trên môi trường Azure.

### Nhóm 3: Backlog Dự án
9. **`docs/planning/product-backlog-cicd-2-tuan.xlsx`:**
   - Epic EPC-05: Đổi tiêu đề thành "Hạ tầng Đám mây dưới dạng mã (Cloud Infrastructure as Code)".
   - US-018, US-019, US-020, US-021: Điều chỉnh User Story và Acceptance Criteria theo Azure Container Registry, Azure Container Apps và Service Principal.
   - US-029: Cập nhật luồng CD tự động triển khai lên Azure Container Apps.
   - US-034: Cập nhật cảnh báo qua Azure Monitor / Log Analytics.

---

## 5. Lộ Trình Thực Hiện Cập Nhật (3 Giai Đoạn)

### Giai đoạn 1: Cập nhật tài liệu điều hành và bộ nhớ dự án
- Phạm vi: `AGENTS.md`, `docs/process/WORKFLOW.md`, `HUONG-DAN-CHAY.md`.
- Mục tiêu: Đảm bảo bộ nhớ dự án và hướng dẫn chạy khớp 100% với hạ tầng Azure đang hoạt động.

### Giai đoạn 2: Cập nhật kế hoạch 2 tuần và các hợp đồng thiết kế
- Phạm vi: `docs/planning/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md`, `docs/architecture/ADR-001-frontend-hosting.md`, `docs/architecture/THONG_TIN_DE_TAI.txt`, `docs/api/US-010.md`, `docs/api/US-013.md`.
- Mục tiêu: Chuẩn hóa toàn bộ tài liệu kiến trúc, kế hoạch từng ngày và hợp đồng API theo nền tảng Azure.

### Giai đoạn 3: Cập nhật Product Backlog Excel
- Phạm vi: `docs/planning/product-backlog-cicd-2-tuan.xlsx`.
- Mục tiêu: Đồng bộ toàn bộ Epic EPC-05, US-018 -> US-021, US-029, US-034 trong bảng tính Excel.

---

## 6. Tiêu Chuẩn Nghiệm Thu Kế Hoạch

1. Không còn tồn tại các thông tin yêu cầu tài khoản Google Cloud trong các tài liệu chỉ dẫn vận hành.
2. Toàn bộ tài liệu tuân thủ chuẩn văn phong kỹ thuật gãy gọn, mạch lạc, tuyệt đối không chứa icon/emoji.
3. Bộ kiểm thử tự động của dự án (64/64 tests) tiếp tục duy trì trạng thái PASSED sau mỗi lần cập nhật tài liệu.
