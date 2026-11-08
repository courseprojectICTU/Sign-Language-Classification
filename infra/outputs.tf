data "azurerm_client_config" "current" {}

output "github_oidc_client_id" {
  description = "Application client ID for the GitHub OIDC workflow."
  value       = azuread_application.github_deploy.client_id
}

output "github_oidc_tenant_id" {
  description = "Tenant ID for the GitHub OIDC workflow."
  value       = data.azurerm_client_config.current.tenant_id
}

output "github_oidc_subscription_id" {
  description = "Subscription ID for the GitHub OIDC workflow."
  value       = var.subscription_id
}
