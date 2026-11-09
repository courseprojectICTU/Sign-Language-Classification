data "google_project" "target" {
  project_id = var.project_id
}

resource "google_monitoring_notification_channel" "billing_team" {
  project      = var.project_id
  display_name = "VSL billing alerts to project team"
  type         = "email"
  enabled      = true

  labels = {
    email_address = var.team_alert_email
  }

  user_labels = {
    purpose = "billing-budget-alerts"
  }
}

resource "google_billing_budget" "project_monthly" {
  billing_account = var.billing_account_id
  display_name    = var.budget_display_name

  budget_filter {
    projects               = ["projects/${data.google_project.target.number}"]
    calendar_period        = "MONTH"
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = "5"
    }
  }

  threshold_rules {
    threshold_percent = 0.2
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = [
      google_monitoring_notification_channel.billing_team.id,
    ]
    disable_default_iam_recipients  = false
    enable_project_level_recipients = true
  }

  lifecycle {
    prevent_destroy = true
  }
}
