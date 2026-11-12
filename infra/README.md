# Terraform infrastructure

The root module uses the AzureRM provider. The existing staging Azure Container
Registry is managed by Terraform under US-019; application resources are added
by later user stories. US-018 did not import or change Azure application
resources.

## Adopt the existing staging registry

The staging registry `vslacr3795` already exists. Initialize the root module
with the Azure Blob backend first, then import the existing registry into the
staging state before planning:

```powershell
terraform -chdir=infra import azurerm_container_registry.vsl `
  "/subscriptions/<subscription-id>/resourceGroups/rg-vsl-staging/providers/Microsoft.ContainerRegistry/registries/vslacr3795"
terraform -chdir=infra plan -var-file="environments/staging.tfvars"
```

The import command writes Terraform state but does not modify the Azure
registry. Review the plan and stop if it proposes replacing or destroying the
registry. Do not run import or apply without explicit approval.

The registry cleanup task runs `acr purge` on a daily schedule for `vsl-api`.
`acr purge` is a preview feature; verify its dry-run output and review task logs
before enabling cleanup. It retains up to the three newest eligible tags per
repository after a purge and is not an instantaneous image-count limit.

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

## Subscription cost budget (US-033)

`budget.tf` declares `azurerm_consumption_budget_subscription.monthly` for a
`$5 USD` monthly guardrail with `Actual` spend alerts at `20%` (`$1 USD`) and
`100%` (`$5 USD`). By default, alerts target subscription `Owner` roles; pass
team distribution emails via environment variables without committing them:

```powershell
$env:TF_VAR_budget_alert_emails = '["team-alerts@example.com"]'
terraform -chdir=infra plan -var-file="environments/staging.tfvars"
```

Because `provider "azurerm"` sets `resource_provider_registrations = "none"`,
register `Microsoft.Consumption` once on the subscription if required:

```powershell
az provider register --namespace Microsoft.Consumption
```

If an Azure for Students / Sponsorship subscription restricts ARM budget
creation, set `enable_billing_budget = false` when planning/applying and manage
cost alerts and balance checks through the Azure Portal / Sponsorships portal as
documented in `docs/RUNBOOK.md`.

## Adopt staging Container Apps stack (US-020)

`container_app.tf` manages Log Analytics (`workspace-rgvslstaging8EBp`), the
Consumption Container Apps Environment (`cae-vsl-staging-std`), the User
Assigned Managed Identity (`id-vsl-api-pull`) with `AcrPull`, and the
Container App `vsl-api` (`min_replicas = 0`, `max_replicas = 3`, `1` vCPU,
`2Gi`, HTTP `/health` probes, `VSL_MODEL_PATH`). When adopting the existing
staging stack into `staging.tfstate`, import all five resources before
planning:

```powershell
terraform -chdir=infra import -var-file="environments/staging.tfvars" `
  azurerm_log_analytics_workspace.vsl `
  "/subscriptions/<subscription-id>/resourceGroups/rg-vsl-staging/providers/Microsoft.OperationalInsights/workspaces/workspace-rgvslstaging8EBp"

terraform -chdir=infra import -var-file="environments/staging.tfvars" `
  azurerm_container_app_environment.vsl `
  "/subscriptions/<subscription-id>/resourceGroups/rg-vsl-staging/providers/Microsoft.App/managedEnvironments/cae-vsl-staging-std"

terraform -chdir=infra import -var-file="environments/staging.tfvars" `
  azurerm_user_assigned_identity.vsl_api_pull `
  "/subscriptions/<subscription-id>/resourceGroups/rg-vsl-staging/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-vsl-api-pull"

terraform -chdir=infra import -var-file="environments/staging.tfvars" `
  azurerm_role_assignment.vsl_api_acr_pull `
  "/subscriptions/<subscription-id>/resourceGroups/rg-vsl-staging/providers/Microsoft.ContainerRegistry/registries/vslacr3795/providers/Microsoft.Authorization/roleAssignments/<role-assignment-guid>"

terraform -chdir=infra import -var-file="environments/staging.tfvars" `
  azurerm_container_app.vsl_api `
  "/subscriptions/<subscription-id>/resourceGroups/rg-vsl-staging/providers/Microsoft.App/containerApps/vsl-api"

terraform -chdir=infra plan -var-file="environments/staging.tfvars"
```

Verify the plan performs only in-place updates (no destroy/replace of
`cae-vsl-staging-std` or `vsl-api`) before seeking owner approval for `apply`.
On staging, `container_min_replicas` must remain `0` (`BR-016`) so idle periods
scale down to zero replicas and consume zero compute units. Because `vsl-api`
uses `revision_mode = "Multiple"`, deactivate any older pre-US-020 active
revision that still holds `minReplicas > 0` (`az containerapp revision deactivate`)
so zero-traffic periods can scale down to `0` replicas.
