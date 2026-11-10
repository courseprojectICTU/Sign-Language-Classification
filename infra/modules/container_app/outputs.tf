output "container_app_id" {
  description = "Resource ID of the Container App."
  value       = azurerm_container_app.this.id
}

output "container_app_url" {
  description = "Public HTTPS URL of the Container App."
  value       = "https://${azurerm_container_app.this.ingress[0].fqdn}"
}

output "container_app_environment_id" {
  description = "Resource ID of the isolated Container Apps environment."
  value       = azurerm_container_app_environment.this.id
}

output "image_reference" {
  description = "Container image deployed by this environment."
  value       = azurerm_container_app.this.template[0].container[0].image
}
