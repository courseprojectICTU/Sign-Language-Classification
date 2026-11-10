module "container_app" {
  source = "../../modules/container_app"

  providers = {
    azurerm          = azurerm
    azurerm.registry = azurerm.registry
  }

  environment                    = var.environment
  resource_group_name            = var.resource_group_name
  location                       = var.location
  container_app_environment_name = var.container_app_environment_name
  container_app_name             = var.container_app_name
  registry_name                  = var.registry_name
  registry_resource_group_name   = var.registry_resource_group_name
  image_repository               = var.image_repository
  image_tag                      = var.image_tag
  cpu                            = var.cpu
  memory                         = var.memory
  min_replicas                   = var.min_replicas
  max_replicas                   = var.max_replicas
  environment_variables          = var.environment_variables
  tags                           = var.tags
}

output "container_app_url" {
  description = "Public URL of the production service."
  value       = module.container_app.container_app_url
}

output "image_reference" {
  description = "Image deployed to production."
  value       = module.container_app.image_reference
}
