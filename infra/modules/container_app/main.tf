data "azurerm_container_registry" "shared" {
  provider            = azurerm.registry
  name                = var.registry_name
  resource_group_name = var.registry_resource_group_name
}

resource "azurerm_user_assigned_identity" "acr_pull" {
  name                = "id-${var.environment}-acr-pull"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  provider                         = azurerm.registry
  scope                            = data.azurerm_container_registry.shared.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_user_assigned_identity.acr_pull.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_container_app_environment" "this" {
  name                = var.container_app_environment_name
  resource_group_name = var.resource_group_name
  location            = var.location
  logs_destination    = "azure-monitor"
  tags                = local.tags
}

resource "azurerm_container_app" "this" {
  name                         = var.container_app_name
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.acr_pull.id]
  }

  registry {
    server   = data.azurerm_container_registry.shared.login_server
    identity = azurerm_user_assigned_identity.acr_pull.id
  }

  ingress {
    external_enabled = true
    target_port      = 8080
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = var.container_app_name
      image  = "${data.azurerm_container_registry.shared.login_server}/${var.image_repository}:${var.image_tag}"
      cpu    = var.cpu
      memory = var.memory

      dynamic "env" {
        for_each = var.environment_variables

        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  depends_on = [azurerm_role_assignment.acr_pull]

  lifecycle {
    precondition {
      condition     = var.max_replicas >= var.min_replicas
      error_message = "max_replicas must be greater than or equal to min_replicas."
    }
  }
}

locals {
  tags = merge(var.tags, {
    environment = var.environment
    managed_by  = "terraform"
  })
}
