# Terraform infrastructure

This root module currently configures the Google provider and environment inputs.
Cloud resources are added by later user stories.

## Remote state

Create the state bucket in the existing Google Cloud project before initializing
Terraform. The bucket name is supplied at init time rather than committed here.
The GCS backend provides state locking; use separate prefixes for staging and
production so the environments do not share state.

Run these commands from `infra/`, replacing `<state-bucket>` with the existing
bucket name:

```powershell
terraform init `
  -backend-config="bucket=<state-bucket>" `
  -backend-config="prefix=sign-language-classification/staging"
terraform plan -var-file="environments/staging.tfvars"
```

For production, initialize with
`-backend-config="prefix=sign-language-classification/production"` and run
`terraform plan -var-file="environments/production.tfvars"`.

Set `project_id` in the selected tfvars file to the existing Google Cloud
project ID before planning. Do not commit credentials, backend configuration
files, or local Terraform state.
