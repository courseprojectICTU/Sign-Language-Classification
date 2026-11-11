resource "azurerm_log_analytics_workspace" "vsl" {
  name                = var.log_analytics_workspace_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "vsl" {
  name                       = var.container_app_environment_name
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.vsl.id
  logs_destination           = "log-analytics"

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

resource "azurerm_user_assigned_identity" "vsl_api_pull" {
  name                = "id-${var.container_app_name}-pull"
  resource_group_name = var.resource_group_name
  location            = var.location
}

resource "azurerm_role_assignment" "vsl_api_acr_pull" {
  scope                            = azurerm_container_registry.vsl.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_user_assigned_identity.vsl_api_pull.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_container_app" "vsl_api" {
  name                         = var.container_app_name
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.vsl.id
  revision_mode                = "Multiple"
  workload_profile_name        = "Consumption"
  max_inactive_revisions       = 100

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.vsl_api_pull.id]
  }

  registry {
    server   = azurerm_container_registry.vsl.login_server
    identity = azurerm_user_assigned_identity.vsl_api_pull.id
  }

  ingress {
    external_enabled           = true
    allow_insecure_connections = false
    target_port                = 8080
    transport                  = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas                     = var.container_min_replicas
    max_replicas                     = var.container_max_replicas
    cooldown_period_in_seconds       = var.scale_cooldown_seconds
    polling_interval_in_seconds      = 30
    termination_grace_period_seconds = var.container_termination_grace_period_seconds

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = tostring(var.http_scale_concurrent_requests)
    }

    container {
      name   = var.container_app_name
      image  = "${azurerm_container_registry.vsl.login_server}/${var.image_repository}:${var.image_tag}"
      cpu    = var.container_cpu
      memory = var.container_memory
    }
  }

  depends_on = [azurerm_role_assignment.vsl_api_acr_pull]

  lifecycle {
    precondition {
      condition     = var.container_max_replicas >= var.container_min_replicas
      error_message = "container_max_replicas must be greater than or equal to container_min_replicas."
    }

    precondition {
      condition     = var.environment != "staging" || var.container_min_replicas == 0
      error_message = "Staging Container App must set container_min_replicas = 0 to comply with BR-016."
    }

    precondition {
      condition     = var.container_cpu != 1 || var.container_memory == "2Gi"
      error_message = "Azure Container Apps Consumption pairs 1 vCPU with 2Gi memory."
    }
  }
}
