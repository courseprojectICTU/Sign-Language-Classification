# Terraform state bucket bootstrap

Run this one-time bootstrap before initializing the root module in `infra/`.
The bootstrap uses local state because the remote bucket does not exist yet.
Local state files are ignored by Git; keep the generated state file backed up
until the bucket has been created and verified.

From `infra/bootstrap/`, set the actual project ID and bucket name without
committing credentials:

```powershell
terraform init
terraform plan `
  -var="project_id=nhan-dien-tay" `
  -var="bucket_name=nhan-dien-tay-state"
```

After reviewing the plan, create the bucket only with explicit approval:

```powershell
terraform apply `
  -var="project_id=nhan-dien-tay" `
  -var="bucket_name=nhan-dien-tay-state"
```

The bucket enforces uniform bucket-level access and public access prevention,
keeps object versions for recovery, and cannot be destroyed by Terraform.
Bucket names are globally unique; choose another name if this one is already
claimed.

After successful creation, initialize the root module from `infra/`:

```powershell
terraform init `
  -backend-config="bucket=nhan-dien-tay-state" `
  -backend-config="prefix=sign-language-classification/staging"
terraform plan -var-file="environments/staging.tfvars"
```

Use the production prefix and tfvars file for production. The bootstrap state
remains local; do not delete it until the bucket is verified and the bootstrap
resource state has been backed up.
