# Runbook — Billing Budget, MFA và kiểm soát chi phí GCP

**Trạng thái US-033:** cấu hình IaC và hướng dẫn đã chuẩn bị; **chưa áp dụng lên GCP**. Không có Cloud CLI/credentials, Billing Account ID, Project ID hoặc Google Group email trong môi trường hiện tại. AC-033-01 chỉ được đánh dấu PASS sau khi budget được tạo, thông báo kiểm thử tới nhóm thành công và MFA được xác minh trong Admin Console.

## Nguyên tắc quan trọng

- Budget được cấu hình là alerts-only: nó **không chặn hoặc giới hạn chi tiêu**. Reporting có thể trễ; hóa đơn cuối kỳ có thể khác dữ liệu budget.
- Budget theo dõi chi phí project **trước khi credits được trừ** (`EXCLUDE_ALL_CREDITS`) để khuyến khích phát hiện usage có phí sớm.
- Ngưỡng `$1` và `$5` là cảnh báo, không phải cam kết chi phí bằng 0. Giữ Cloud Run `min-instances=0`, giới hạn `max-instances`, và không bật dịch vụ cấm.
- Chỉ Billing Account Costs Manager/Administrator và Monitoring Editor được phép thực hiện các bước tương ứng. Không commit billing ID, email cá nhân, Terraform state hoặc credentials.

## Billing Budget $1 / $5

Module Terraform ở `infra/billing-budget/` tạo một budget tháng `$5` cho **một project**. Hai ngưỡng `20%` và `100%` tương ứng `$1` và `$5`. Email alert gửi đến Google Group của dự án, Billing Account Admin/Users và Project Owners.

### Chuẩn bị

1. Xác nhận Billing Account đã liên kết với đúng project.
2. Xác nhận currency của Billing Account là USD; nếu dùng currency khác, dừng apply và hiệu chỉnh budget amount/ngưỡng theo currency đó.
3. Tạo hoặc chọn Google Group chứa toàn bộ thành viên cần nhận cảnh báo; kiểm tra group cho phép nhận email tự động từ Google Cloud.
4. Cấp quyền Billing Account Costs Manager (hoặc Billing Account Administrator) cho người áp dụng và Monitoring Editor trên project để tạo notification channel.
5. Bật `Cloud Billing Budgets API` và `Cloud Monitoring API` trên project nếu chưa bật.
6. Xác nhận Project ID, Billing Account ID và địa chỉ Google Group với chủ dự án. Không điền dữ liệu giả vào cấu hình.

### Plan và apply

Đăng nhập bằng danh tính được cấp quyền (dùng Application Default Credentials; không tạo service-account key JSON). Điền biến môi trường trong PowerShell:

```powershell
$env:TF_VAR_project_id = "<PROJECT_ID>"
$env:TF_VAR_billing_account_id = "<BILLING_ACCOUNT_ID>"
$env:TF_VAR_team_alert_email = "<GOOGLE_GROUP_EMAIL>"

terraform -chdir=infra/billing-budget init
terraform -chdir=infra/billing-budget validate
terraform -chdir=infra/billing-budget plan
```

Người có quyền billing phải kiểm tra plan xác nhận đúng project, ngân sách tháng `$5`, ngưỡng `$1/$5`, email group, project owners và billing admins. Chỉ sau khi duyệt plan mới chạy:

```powershell
terraform -chdir=infra/billing-budget apply
```

Lệnh `apply` yêu cầu xác nhận tương tác; không dùng `-auto-approve`. Terraform có `prevent_destroy` cho budget để hạn chế xóa nhầm. Cấu hình hiện dùng local state; trước khi nhiều người cùng quản trị, chuyển state sang backend remote được kiểm soát và không commit state vào Git.

### Xác minh sau khi apply

1. Trong Billing → Budgets & alerts, xác nhận budget áp dụng đúng project và hiển thị threshold 20%/$1 và 100%/$5.
2. Trong Monitoring → Alerting → Notification channels, xác nhận email channel đã tạo và hoàn tất xác minh địa chỉ nếu được yêu cầu.
3. Dùng chức năng **Test notification** của channel để xác nhận Google Group nhận email; không tạo usage có phí để cố tình kích hoạt budget threshold.
4. Xác nhận Billing Account Admins/Users và Project Owners vẫn nằm trong recipients mặc định.
5. Ghi ID budget, ngày áp dụng và bằng chứng test email vào nhật ký nghiệm thu; không ghi credentials.

Google Cloud có thể mất vài giờ mới gửi email đầu tiên, và usage reporting không tức thời. Nếu cần tự động hóa qua Pub/Sub, bổ sung topic/subscriber riêng đã được duyệt; module hiện dùng email channel.

## MFA / 2-Step Verification

MFA không thể được bật cho người dùng bằng Terraform project resource. Chính sách 2SV thuộc Google Workspace/Cloud Identity và cần **Super Admin**. Project owner không thể cưỡng chế 2SV cho tài khoản Google bên ngoài domain của tổ chức.

### Rollout an toàn cho managed accounts

1. Kiểm kê mọi user có quyền truy cập GCP (project IAM và billing IAM); xác định tài khoản Workspace/Cloud Identity managed và tài khoản bên ngoài.
2. Super Admin thông báo lịch enforcement, vào Admin Console → Security → Authentication → 2-Step Verification; bật cho phép enrollment trước, chọn organization unit/configuration group bao phủ thành viên dự án và đặt thời gian enrollment.
3. Yêu cầu thành viên đăng ký 2SV; ưu tiên passkey/security key hoặc Google Prompt. Ghi nhận mã khôi phục an toàn; enroll và kiểm tra ít nhất hai Super Admin trước khi cưỡng chế.
4. Theo dõi Reports → User Reports → Security hoặc Security Health để kiểm tra enrollment. Chỉ sau khi các tài khoản đã enroll, đặt Enforcement thành On cho nhóm/OU áp dụng.
5. Giữ quy trình khôi phục tài khoản admin và lịch rà soát định kỳ; không loại trừ admin lâu dài khỏi policy.

### Tài khoản ngoài domain và service accounts

- Với tài khoản Google cá nhân/external, yêu cầu chủ tài khoản tự bật 2SV và xác minh trước khi cấp quyền; hoặc chuyển sang danh tính managed. Workspace Super Admin không thể cưỡng chế policy trên tài khoản ngoài domain.
- MFA là cho danh tính người dùng tương tác. Service account không có 2SV; automation nên dùng Workload Identity Federation/short-lived credentials, tránh user key và service-account key JSON.
- Sau rollout, lưu ngày bật policy, phạm vi OU/group, số user đã enroll và số ngoại lệ được chủ dự án chấp thuận. Hiện trạng chưa được xác minh, nên US-033 vẫn chờ nghiệm thu.

## Dịch vụ bị cấm

Không tạo hoặc bật các dịch vụ/cấu hình dưới đây nếu chưa có ngoại lệ được chủ dự án phê duyệt bằng văn bản và đánh giá chi phí:

| Dịch vụ/cấu hình | Lý do cấm |
|---|---|
| GPU VM/accelerator (A2, G2 hoặc GPU attach) | GPU có thể phát sinh chi phí cao ngay cả với thời gian chạy ngắn. |
| GKE cluster chạy thường trực hoặc node pool không scale về 0 | Phí cluster/node và tài nguyên nền liên tục. |
| Cloud SQL High Availability, instance lớn, Spanner, AlloyDB hoặc database managed tương đương | Compute/storage/HA có thể tính phí liên tục; không cần cho MVP hiện tại. |
| Vertex AI Pipelines/Training/Notebook chạy liên tục hoặc endpoint provisioned | Tính phí theo compute/storage và thời gian provisioned. |
| Cloud NAT ngoài hạn mức được duyệt; external load balancer; Cloud CDN | Có phí theo giờ/lưu lượng và không thuộc kiến trúc demo tối thiểu. |
| Cloud Run `min-instances > 0`, instance-based billing hoặc CPU always allocated | Giữ compute chạy khi idle, trái yêu cầu scale-to-zero. |
| Compute Engine VM, Redis/Memorystore, Dataproc hoặc managed cluster chạy 24/7 | Tài nguyên luôn bật có thể vượt xa budget nhỏ. |
| Commitments, reservations hoặc dịch vụ trả trước dài hạn | Tạo nghĩa vụ chi phí khó hoàn tác. |
| Logging/Monitoring ingest hoặc retention lớn không giới hạn | Dữ liệu quan sát vượt quota miễn phí có thể bị tính phí. |

## Dịch vụ được phép có điều kiện

| Dịch vụ/cấu hình | Điều kiện |
|---|---|
| Cloud Run request-based | `min-instances=0`, giới hạn `max-instances`, request timeout phù hợp, không bật CPU always allocated. |
| Cloud Billing Budget và Cloud Monitoring email channels | Chỉ dùng để cảnh báo cho đúng project/account; xác nhận recipients. |
| Artifact Registry | Lưu image cần thiết; bật cleanup/retention và theo dõi dung lượng. |
| Cloud Storage | Chỉ lưu object cần thiết, bucket location/retention tối thiểu, lifecycle xóa file tạm. |
| Cloud Build | Chỉ dùng trong quota và theo dõi build minutes/artifact storage. |
| IAM, Cloud Identity, Workload Identity Federation | Least privilege; không tạo key dài hạn; rà soát principals định kỳ. |

“Được phép” không đồng nghĩa “miễn phí”. Free Tier/quota thay đổi theo thời gian và vùng; kiểm tra bảng giá hiện hành, budget và usage trước khi bật dịch vụ.

## Xử lý email cảnh báo $1

1. Người nhận xác nhận alert và thông báo ngay cho chủ dự án/DevOps; không bỏ qua vì còn dưới `$5`.
2. Mở Billing Reports cho đúng project và tháng; nhóm theo service/SKU để xác định nguồn spend. So sánh actual spend, forecast và thời điểm phát sinh.
3. Tạm dừng deploy/thay đổi hạ tầng mới; kiểm tra Cloud Run min/max instances, revisions, jobs, GPU, GKE, NAT, storage, logs và tài nguyên không thuộc allow-list.
4. Với tài nguyên không cần thiết, người có quyền xác nhận rồi stop/delete hoặc scale-to-zero. Không xóa database/storage có dữ liệu hoặc tắt billing một cách mù quáng.
5. Xác nhận lại Billing Reports/Monitoring sau khi xử lý, ghi service gây phí, hành động, người duyệt và kết quả. Budget alert không cập nhật tức thời.
6. Nếu đạt `$5`, hoặc có dịch vụ không rõ nguồn gốc/đang tăng nhanh, coi là incident: ngừng triển khai, báo owner/billing admin, xử lý tài nguyên sau khi đánh giá tác động và cập nhật runbook.

## Tài liệu tham khảo

- [Cloud Billing budgets and alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets)
- [Terraform `google_billing_budget`](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/billing_budget)
- [Deploy 2-Step Verification (Google Workspace Admin)](https://knowledge.workspace.google.com/admin/security/deploy-2-step-verification)