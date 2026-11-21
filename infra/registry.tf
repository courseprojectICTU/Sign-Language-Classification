resource "azurerm_container_registry" "vsl" {
  count               = var.manage_registry ? 1 : 0
  name                = var.acr_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = true

  lifecycle {
    prevent_destroy = true
  }
}

moved {
  from = azurerm_container_registry.vsl
  to   = azurerm_container_registry.vsl[0]
}

data "azurerm_container_registry" "shared" {
  count               = var.manage_registry ? 0 : 1
  provider            = azurerm.registry
  name                = var.acr_name
  resource_group_name = local.registry_resource_group_name
}

locals {
  registry_resource_group_name = coalesce(trimspace(var.registry_resource_group_name), var.resource_group_name)
  acr_id                       = var.manage_registry ? azurerm_container_registry.vsl[0].id : data.azurerm_container_registry.shared[0].id
  acr_login_server             = var.manage_registry ? azurerm_container_registry.vsl[0].login_server : data.azurerm_container_registry.shared[0].login_server
}

resource "azurerm_user_assigned_identity" "registry_cleanup" {
  count               = var.manage_registry ? 1 : 0
  name                = "id-${var.environment}-acr-cleanup"
  resource_group_name = var.resource_group_name
  location            = var.location
}

moved {
  from = azurerm_user_assigned_identity.registry_cleanup
  to   = azurerm_user_assigned_identity.registry_cleanup[0]
}

resource "azurerm_role_assignment" "cleanup_delete" {
  count                            = var.manage_registry ? 1 : 0
  scope                            = azurerm_container_registry.vsl[0].id
  role_definition_name             = "AcrDelete"
  principal_id                     = azurerm_user_assigned_identity.registry_cleanup[0].principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

moved {
  from = azurerm_role_assignment.cleanup_delete
  to   = azurerm_role_assignment.cleanup_delete[0]
}

resource "azurerm_container_registry_task" "cleanup" {
  count                 = var.manage_registry ? 1 : 0
  name                  = "vsl-image-cleanup-${var.environment}"
  container_registry_id = azurerm_container_registry.vsl[0].id
  enabled               = true

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.registry_cleanup[0].id]
  }

  platform {
    os = "Linux"
  }

  encoded_step {
    task_content = <<-YAML
      version: v1.1.0
      steps:
        - cmd: mcr.microsoft.com/acr/acr-cli:0.19 acr purge --filter 'vsl-api:.*' --ago 0d --keep 3
    YAML
  }

  timer_trigger {
    name     = "daily"
    schedule = "0 0 * * *"
    enabled  = true
  }

  depends_on = [azurerm_role_assignment.cleanup_delete]
}

moved {
  from = azurerm_container_registry_task.cleanup
  to   = azurerm_container_registry_task.cleanup[0]
}
