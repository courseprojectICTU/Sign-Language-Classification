locals {
  server_error_log_query = <<-KQL
    ContainerAppConsoleLogs_CL
    | where ContainerAppName_s == "${var.container_app_name}"
    | extend StatusCode = toint(extract(@"HTTP/[0-9.]+""\s+([0-9][0-9][0-9])\s", 1, Log_s))
    | where StatusCode >= 500 and StatusCode <= 599
    | project TimeGenerated
  KQL
}

resource "azurerm_monitor_action_group" "server_error" {
  count = var.environment == "staging" ? 1 : 0

  name                = "vsl-server-error-${var.environment}"
  resource_group_name = var.resource_group_name
  short_name          = "vsl5xx"
  location            = "global"
  tags                = local.common_tags

  dynamic "email_receiver" {
    for_each = var.server_error_alert_emails

    content {
      name                    = "server-error-${email_receiver.key}"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "server_error" {
  count = var.environment == "staging" ? 1 : 0

  name                = "vsl-server-error-5xx-staging"
  resource_group_name = var.resource_group_name
  location            = var.location

  evaluation_frequency = "PT5M"
  window_duration      = "PT5M"
  scopes               = [azurerm_log_analytics_workspace.vsl.id]
  severity             = 2

  criteria {
    query                   = local.server_error_log_query
    time_aggregation_method = "Count"
    threshold               = 100
    operator                = "GreaterThanOrEqual"
  }

  description             = "Alert when staging vsl-api returns at least 100 HTTP 5xx responses in five minutes."
  display_name            = "VSL staging HTTP 5xx"
  enabled                 = true
  auto_mitigation_enabled = true
  tags                    = local.common_tags

  action {
    action_groups = [azurerm_monitor_action_group.server_error[0].id]
  }
}
