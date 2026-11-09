output "budget_name" {
  description = "Full resource name of the monthly project-scoped billing budget."
  value       = google_billing_budget.project_monthly.name
}

output "notification_channel_name" {
  description = "Monitoring email notification channel used by the budget."
  value       = google_monitoring_notification_channel.billing_team.name
}
