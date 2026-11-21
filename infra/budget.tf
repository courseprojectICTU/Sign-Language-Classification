resource "azurerm_consumption_budget_subscription" "monthly" {
  count = var.enable_billing_budget ? 1 : 0

  name            = "vsl-monthly-cost-guardrail-${var.environment}"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = 5
  time_grain      = "Monthly"

  time_period {
    start_date = var.budget_start_date
  }

  notification {
    enabled        = true
    threshold      = 20
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = length(var.budget_alert_emails) > 0 ? var.budget_alert_emails : null
    contact_roles  = ["Owner"]
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = length(var.budget_alert_emails) > 0 ? var.budget_alert_emails : null
    contact_roles  = ["Owner"]
  }

  lifecycle {
    ignore_changes = [time_period]
  }
}
