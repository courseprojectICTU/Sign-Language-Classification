# Azure Terraform state bootstrap

This one-time configuration creates the Azure Storage Account and private Blob
container required by the root module's remote backend. The target Resource
Group must already exist. Bootstrap state is local to this directory; back it
up securely and do not commit it.

The Azure identity used for the bootstrap must have permission to create
resources in the Resource Group and `Storage Blob Data Contributor` access for
the container. The storage account name must be globally unique and contain
only 3-24 lowercase letters and digits.

From the repository root, initialize the bootstrap configuration:

```powershell
terraform -chdir=infra/bootstrap-azure init
terraform -chdir=infra/bootstrap-azure plan `
  -var="subscription_id=<azure-subscription-id>" `
  -var="resource_group_name=<existing-resource-group>" `
  -var="location=eastasia" `
  -var="storage_account_name=<globally-unique-name>"
```

Review the plan. Run `terraform apply` with the same variables only after the
project owner explicitly approves creating the Storage Account and container.
No credentials or storage keys belong in the repository.

After creation, initialize `infra/` with the backend values and
`use_azuread_auth=true` documented in [`../README.md`](../README.md). Azure
Blob leases provide state locking. The root module uses separate state keys for
staging and production.
