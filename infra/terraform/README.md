# US-018 / US-019 — Terraform, GCS state, Artifact Registry and GitHub OIDC

## Prerequisites / bootstrap

- Existing billed Google Cloud project, GCP IAM privileges to enable APIs, create
  service accounts, WIF and Artifact Registry, plus Cloud Storage access.
- Terraform >=1.6, gcloud SDK authenticated with `gcloud auth application-default login`.
- Create a globally unique bucket for **state before** `terraform init`. Recommended:
  uniform bucket-level access, public access prevention, versioning, restricted IAM
  access, and a separate bootstrap owner. Choose a location compliant with your course.
- The state bucket is intentionally bootstrapped outside the main state configuration.
- Never commit state, backend credentials or `.tfvars` containing secrets.

```bash
# Replace IDs; run this once with a privileged GCP identity.
gcloud services enable storage.googleapis.com --project=PROJECT_ID
gcloud storage buckets create gs://YOUR_UNIQUE_TF_STATE_BUCKET --project=PROJECT_ID --location=ASIA-SOUTHEAST1 --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update gs://YOUR_UNIQUE_TF_STATE_BUCKET --versioning

cd infra/terraform
terraform init -backend-config="bucket=YOUR_UNIQUE_TF_STATE_BUCKET" -backend-config="prefix=sign-language/dev"
terraform fmt -check
terraform validate
terraform plan -var="project_id=PROJECT_ID"
# After review and approval:
terraform apply -var="project_id=PROJECT_ID"
```

Apply enables APIs and provisions Artifact Registry, a least-privilege image
publisher service account, GitHub OIDC provider, and a WIF binding restricted
to the exact GitHub repository. The provider additionally restricts OIDC
authentication to `refs/heads/main` to keep production uploads off feature PRs.

## GitHub Actions (future deployment pipeline)

- Add provider output as GitHub variable `GCP_WIF_PROVIDER`.
- Add service account output as GitHub variable `GCP_SERVICE_ACCOUNT`.
- Grant workflow `id-token: write` and `contents: read`.
- Call `google-github-actions/auth` then `setup-gcloud` and configure Docker
  credential helper for the region's docker.pkg.dev host.
- Build and push only from main, tag images by immutable Git commit SHA.
- PR workflows should only run Terraform `fmt` and `validate`, never `apply`.

## Security / costs

Billing budget is an independent, outstanding project task. Creating a budget
requires a billing account and is **not** automatically included here.
Use budget alerts and verify quotas; a budget does not cap spending.
The cloud deployment itself is **not complete** until `terraform apply`,
registry permissions, GitHub OIDC and a real signed-in push are tested.
