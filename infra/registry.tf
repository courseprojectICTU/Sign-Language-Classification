resource "azurerm_container_registry" "vsl" {
  name                = var.acr_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = true

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_user_assigned_identity" "registry_cleanup" {
  name                = "id-${var.environment}-acr-cleanup"
  resource_group_name = var.resource_group_name
  location            = var.location
}

resource "azurerm_role_assignment" "cleanup_delete" {
  scope                            = azurerm_container_registry.vsl.id
  role_definition_name             = "AcrDelete"
  principal_id                     = azurerm_user_assigned_identity.registry_cleanup.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_container_registry_task" "cleanup" {
  name                  = "vsl-image-cleanup-${var.environment}"
  container_registry_id = azurerm_container_registry.vsl.id
  enabled               = true

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.registry_cleanup.id]
  }

  platform {
    os = "Linux"
  }

  encoded_step {
    task_content = <<-YAML
      version: v1.1.0
      steps:
        - cmd: acr purge --filter 'vsl-api:.*' --ago 0d --keep 3
    YAML
  }

  timer_trigger {
    name     = "daily"
    schedule = "0 0 * * *"
    enabled  = true
  }

  depends_on = [azurerm_role_assignment.cleanup_delete]
}
