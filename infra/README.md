# Terraform infrastructure

The root module uses the AzureRM provider. Application resources are added by
later user stories. Existing Azure resources are not imported or changed by
US-018.

## Azure Blob remote state

Bootstrap the state Storage Account and private Blob container with the separate
Terraform configuration in [`bootstrap-azure/README.md`](bootstrap-azure/README.md).
The bootstrap uses local state in its own directory; never commit that state.

The Terraform identity must be able to access the container through Azure AD
(`Storage Blob Data Contributor`). Azure Blob leases provide state locking.
Use a distinct blob key for each environment:

```powershell
terraform -chdir=infra init `
  -backend-config="resource_group_name=<state-resource-group>" `
  -backend-config="storage_account_name=<state-storage-account>" `
  -backend-config="container_name=<state-container>" `
  -backend-config="key=sign-language-classification/staging.tfstate" `
  -backend-config="use_azuread_auth=true" `
  -backend-config="use_cli=true"
terraform -chdir=infra plan -var-file="environments/staging.tfvars"
```

For production, use `key=sign-language-classification/production.tfstate` and
`environments/production.tfvars`. Replace the production placeholders with
verified Azure values before planning; production details are not yet in the
staging handover.

Do not commit credentials, backend configuration files, Terraform plans, or
local Terraform state. Do not run `terraform apply` without explicit approval.
