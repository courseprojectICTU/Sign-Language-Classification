# Azure Terraform state bootstrap

This one-time configuration creates the Azure Storage Account and private Blob
container required by the root module's remote backend. The target Resource
Group must already exist. Bootstrap state is local to this directory; back it
up securely and do not commit it.

The Azure identity used for the bootstrap must be able to create resources in
the Resource Group and must already have the `Storage Blob Data Contributor`
role on the Resource Group or Storage Account. This role is required because
the provider uses Azure AD authentication and shared-key access is disabled.
The bootstrap does not create role assignments; ask an Azure administrator to
grant the role separately. The AzureRM provider is configured not to register
providers automatically; an administrator must register `Microsoft.Storage`
for the subscription before bootstrap. The storage account name must be
globally unique and contain only 3-24 lowercase letters and digits.

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

After the Storage Account and container exist, initialize `infra/` with the
backend values, `use_azuread_auth=true`, and `use_cli=true` documented in
[`../README.md`](../README.md).
The identity used for the root backend must retain the
`Storage Blob Data Contributor` role. Azure Blob leases provide state locking.
The root module uses separate state keys for staging and production.
