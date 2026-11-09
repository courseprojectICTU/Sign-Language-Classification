# Runbook — Cost Management, Billing Alerts và MFA

**Phạm vi:** US-033, Google Cloud project của Sign-Language-Classification
**Trạng thái:** Terraform và hướng dẫn đã chuẩn bị; chưa apply lên GCP. Chưa xác minh email hoặc chính sách MFA. Chỉ đánh dấu AC-033-01 PASS sau khi người có quyền billing/admin xác minh cấu hình thực tế.

## Billing Budget và email alerts

Module `infra/billing-budget/` khai báo một budget theo tháng cho một project, tổng mức `$5 USD`:

| Ngưỡng | Terraform threshold | Cơ sở chi tiêu |
|---|---:|---|
| `$1 USD` | `20%` của budget | Chi tiêu hiện tại trong kỳ |
| `$5 USD` | `100%` của budget | Chi tiêu hiện tại trong kỳ |

Budget lọc theo project và tháng dương lịch, loại trừ credits (`EXCLUDE_ALL_CREDITS`) để cảnh báo sớm về mức sử dụng trước credits. Đây là **cảnh báo, không phải giới hạn chi tiêu**; budget không tự dừng dịch vụ và dữ liệu Billing có thể cập nhật trễ.

`team_alert_email` phải là địa chỉ Google Group chứa toàn bộ thành viên dự án cần nhận thông báo. Budget cũng giữ recipients mặc định cho Billing Account admins/users và bật project-level recipients. Chủ sở hữu nhóm chịu trách nhiệm cập nhật membership khi thành viên tham gia/rời dự án.

### Điều kiện và triển khai

1. Xác nhận Project ID, Billing Account ID, billing account đã liên kết với project và currency là USD. Không dùng giá trị giả; nếu billing account dùng currency khác, dừng và điều chỉnh kế hoạch.
2. Tạo/kiểm tra Google Group nhận email; xác nhận mọi thành viên liên quan có trong nhóm và group nhận được thư tự động từ Google Cloud.
3. Người áp dụng cần quyền quản lý billing phù hợp (Billing Account Costs Manager/Administrator) và quyền tạo Monitoring notification channel trên project (Monitoring Editor). Bật Cloud Billing Budgets API và Cloud Monitoring API nếu cần.
4. Đăng nhập bằng danh tính được cấp quyền, dùng Application Default Credentials; không tạo hoặc commit service-account key JSON. Trong PowerShell, cung cấp các giá trị đã được chủ dự án xác nhận:

```powershell
$env:TF_VAR_project_id = "<PROJECT_ID>"
$env:TF_VAR_billing_account_id = "<BILLING_ACCOUNT_ID>"
$env:TF_VAR_team_alert_email = "<GOOGLE_GROUP_EMAIL>"

terraform -chdir=infra/billing-budget init
terraform -chdir=infra/billing-budget validate
terraform -chdir=infra/billing-budget plan
```

5. Người có quyền billing kiểm tra plan: đúng project/account, budget tháng `$5 USD`, ngưỡng `$1/$5`, email Group và default recipients. Chỉ sau khi duyệt plan mới chạy lệnh tương tác:

```powershell
terraform -chdir=infra/billing-budget apply
```

Không dùng `-auto-approve`. Terraform có `prevent_destroy` cho budget. State/plan có thể chứa thông tin nhạy cảm; không commit chúng. Module hiện dùng local state, nên trước khi quản trị nhiều người cần chuyển state sang backend remote được kiểm soát.

### Xác minh email

- Billing → Budgets & alerts: xác nhận đúng project, kỳ tháng, amount và thresholds `20%`/`100%`.
- Monitoring → Alerting → Notification channels: xác nhận email channel đã tạo và hoàn tất xác minh địa chỉ nếu được yêu cầu.
- Dùng chức năng **Test notification** của channel và xác nhận Google Group nhận thư; không tạo usage trả phí để thử threshold.
- Kiểm tra danh sách thành viên Group và recipients mặc định của Billing Account/project. Ghi lại ngày, budget ID và kết quả kiểm thử vào nhật ký nghiệm thu, không ghi credentials.

Email threshold có thể đến trễ do thời gian cập nhật billing data. Nếu cần Pub/Sub, phải có topic/subscriber và quyền truy cập được duyệt; module hiện cấu hình email, không cấu hình Pub/Sub.

## Bắt buộc bật MFA / 2-Step Verification

Chính sách cho managed Google Workspace/Cloud Identity accounts cần Workspace Super Admin; project owner/IAM admin không thể bật chính sách cho mọi tài khoản Google bên ngoài domain của tổ chức.

1. Kiểm kê người dùng trong project IAM và Billing IAM; phân loại managed accounts và external/personal accounts.
2. Super Admin vào Admin Console → Security → Authentication → 2-Step Verification. Chọn OU/group bao phủ thành viên dự án, bật enrollment trước và thông báo hạn hoàn tất.
3. Thành viên enroll 2SV, ưu tiên passkey/security key hoặc Google Prompt. Kiểm tra ít nhất hai tài khoản quản trị có phương án khôi phục trước khi enforcement.
4. Super Admin kiểm tra enrollment trong Reports/User Reports/Security, sau đó bật Enforcement cho OU/group đã chọn. Không loại trừ admin lâu dài; duy trì quy trình khôi phục tài khoản.
5. Với external accounts, yêu cầu chủ tài khoản tự bật và xác minh 2SV trước khi cấp quyền, hoặc chuyển sang managed identity. Workspace admin không thể cưỡng chế policy trên tài khoản ngoài domain.

MFA áp dụng cho danh tính người dùng tương tác, không áp dụng cho service accounts. Automation nên dùng Workload Identity Federation hoặc credentials ngắn hạn; tránh user/service-account keys dài hạn. Ghi ngày enforcement, OU/group, số user đã enroll và ngoại lệ được duyệt. Hiện tại MFA chưa được xác minh vì cần quyền Workspace Super Admin.

## Dịch vụ bị cấm và được phép

Không triển khai dịch vụ bị cấm nếu chưa có ngoại lệ bằng văn bản của chủ dự án và đánh giá chi phí. “Được phép” không đồng nghĩa miễn phí; quota, giá và Free Tier thay đổi theo khu vực/thời điểm.

| Dịch vụ/cấu hình bị cấm | Lý do |
|---|---|
| GPU VM/accelerator (ví dụ A2/G2 hoặc gắn GPU) | Chi phí compute cao, kể cả chạy ngắn hạn. |
| GKE cluster/node pool chạy thường trực hoặc không scale về 0 | Phát sinh phí cluster và compute liên tục. |
| Cloud SQL High Availability, instance lớn, Spanner, AlloyDB hoặc database managed tương đương | Compute, storage, HA và backup có thể bị tính phí liên tục. |
| Vertex AI Pipelines, training, notebook chạy liên tục hoặc endpoint provisioned | Tính phí theo thời gian compute/storage được cấp phát. |
| Cloud NAT vượt Free Tier/allowance đã duyệt; external load balancer hoặc CDN ngoài ngân sách | Phí theo giờ và/hoặc lưu lượng. |
| Cloud Run `min-instances > 0`, CPU always allocated hoặc instance-based billing | Giữ compute hoạt động khi không có request. |
| VM, Memorystore/Redis, Dataproc hoặc managed cluster chạy 24/7 | Tài nguyên thường trực không phù hợp mục tiêu near-zero cost. |
| Reservations/commitments dài hạn hoặc logging/monitoring ingest-retention không giới hạn | Cam kết khó hoàn tác hoặc chi phí tăng ngoài dự kiến. |

| Dịch vụ được phép có điều kiện | Điều kiện sử dụng |
|---|---|
| Cloud Run, request-based | `min-instances=0`, giới hạn `max-instances`, không bật CPU always allocated; theo dõi request và egress. |
| Billing Budget/Monitoring email | Chỉ cho project/account đúng; kiểm tra group recipients và trạng thái channel. |
| Artifact Registry | Chỉ lưu image cần thiết; dùng cleanup/retention và theo dõi dung lượng. |
| Cloud Storage | Lưu object cần thiết, chọn location/retention tối thiểu, lifecycle xóa file tạm. |
| Cloud Build | Chạy khi cần, theo dõi build minutes và artifact storage. |
| IAM, Cloud Identity, Workload Identity Federation | Least privilege, không tạo key dài hạn, rà soát principals định kỳ. |

## Ứng phó khi nhận cảnh báo trên `$1`

1. Người nhận xác nhận alert và báo ngay cho chủ dự án/DevOps; không đợi đến ngưỡng `$5`.
2. Mở Billing Reports đúng project và tháng; nhóm theo service/SKU, đối chiếu actual/forecast để xác định nguồn spend và thời điểm phát sinh.
3. Tạm dừng deploy/thay đổi hạ tầng mới. Kiểm tra Cloud Run instances/revisions/jobs, GPU, GKE, NAT, storage, logs và mọi tài nguyên ngoài allow-list.
4. Người có quyền đánh giá tác động rồi stop/delete hoặc scale-to-zero tài nguyên không cần thiết. Không xóa database/storage có dữ liệu hoặc tắt billing một cách mù quáng.
5. Xác nhận lại Billing Reports/Monitoring sau xử lý; ghi service, nguyên nhân, hành động, người duyệt và kết quả. Nhớ rằng số liệu/email có thể trễ.
6. Khi đạt `$5`, chi phí tăng nhanh, hoặc phát hiện dịch vụ không rõ nguồn gốc: coi là incident, ngừng triển khai, báo owner/Billing Admin và xử lý có kiểm soát trước khi tiếp tục.

## Tham khảo

- [Cloud Billing budgets and alerts](https://cloud.google.com/billing/docs/how-to/budgets)
- [Terraform `google_billing_budget`](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/billing_budget)
- [Deploy 2-Step Verification for Google Workspace](https://knowledge.workspace.google.com/admin/security/deploy-2-step-verification)
- Chi tiết guardrails và quy trình MFA bổ sung: [`billing_security.md`](billing_security.md)
