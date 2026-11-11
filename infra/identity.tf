resource "azuread_application" "github_deploy" {
  display_name     = "vsl-github-actions-${var.environment}"
  sign_in_audience = "AzureADMyOrg"
}

resource "azuread_application_federated_identity_credential" "github_develop" {
  application_id = azuread_application.github_deploy.id
  display_name   = "github-develop"
  description    = "GitHub Actions OIDC trust for the develop branch."
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = var.github_oidc_subject
}

resource "azuread_service_principal" "github_deploy" {
  client_id = azuread_application.github_deploy.client_id
}

resource "azurerm_role_assignment" "deployment_push" {
  scope                            = azurerm_container_registry.vsl.id
  role_definition_name             = "AcrPush"
  principal_id                     = azuread_service_principal.github_deploy.object_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "deployment_app" {
  scope                            = azurerm_container_app.vsl_api.id
  role_definition_name             = "Container Apps Contributor"
  principal_id                     = azuread_service_principal.github_deploy.object_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
