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

output "billing_budget_id" {
  description = "Resource ID of the subscription monthly cost guardrail budget when enabled."
  value       = try(azurerm_consumption_budget_subscription.monthly[0].id, null)
}

output "container_app_url" {
  description = "HTTPS endpoint URL of the Azure Container App."
  value       = "https://${azurerm_container_app.vsl_api.ingress[0].fqdn}"
}

output "container_app_fqdn" {
  description = "Ingress FQDN of the Azure Container App."
  value       = azurerm_container_app.vsl_api.ingress[0].fqdn
}

output "container_app_id" {
  description = "Azure Resource ID of the Container App."
  value       = azurerm_container_app.vsl_api.id
}

output "container_app_environment_id" {
  description = "Azure Resource ID of the Container Apps Environment."
  value       = azurerm_container_app_environment.vsl.id
}
