variable "project_id" {
  description = "The Google Cloud project whose costs this monthly budget tracks."
  type        = string

  validation {
    condition     = length(trimspace(var.project_id)) > 0
    error_message = "project_id must not be empty."
  }
}

variable "billing_account_id" {
  description = "The linked Cloud Billing account ID (for example 000000-000000-000000)."
  type        = string

  validation {
    condition     = length(trimspace(var.billing_account_id)) > 0
    error_message = "billing_account_id must not be empty."
  }
}

variable "team_alert_email" {
  description = "A Google Group email that distributes budget notifications to the project team."
  type        = string

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.team_alert_email))
    error_message = "team_alert_email must be a valid email address or Google Group address."
  }
}

variable "budget_display_name" {
  description = "Display name for the project-scoped monthly alerts-only budget."
  type        = string
  default     = "vsl-project-monthly-cost-guardrail"
}
