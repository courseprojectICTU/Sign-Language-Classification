variable "subscription_id" {
  description = "Azure subscription ID for this environment."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be a UUID."
  }
}

variable "resource_group_name" {
  description = "Existing Azure Resource Group for this environment."
  type        = string
}

variable "location" {
  description = "Azure region for this environment."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "acr_name" {
  description = "Azure Container Registry name for this environment."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{5,50}$", var.acr_name))
    error_message = "acr_name must contain 5-50 lowercase letters or digits."
  }
}

variable "container_app_name" {
  description = "Container App receiving deployment updates."
  type        = string
}

variable "github_oidc_subject" {
  description = "Exact GitHub Actions subject trusted by the Azure federated credential."
  type        = string

  validation {
    condition = can(regex(
      "^repo:courseprojectICTU(?:@[0-9]+)?/Sign-Language-Classification(?:@[0-9]+)?:",
      var.github_oidc_subject
    ))
    error_message = "github_oidc_subject must belong to the configured GitHub repository."
  }
}

variable "enable_billing_budget" {
  description = "Whether to provision the monthly $5 USD subscription consumption budget."
  type        = bool
  default     = true
}

variable "budget_start_date" {
  description = "First day of the starting billing month in RFC 3339 UTC format (YYYY-MM-01T00:00:00Z)."
  type        = string
  default     = "2026-11-01T00:00:00Z"

  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-01T00:00:00Z$", var.budget_start_date))
    error_message = "budget_start_date must be the first day of a month in YYYY-MM-01T00:00:00Z format."
  }
}

variable "budget_alert_emails" {
  description = "Additional team email addresses to notify at the $1 (20%) and $5 (100%) budget thresholds."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for email in var.budget_alert_emails :
      can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", email))
    ])
    error_message = "Each budget_alert_emails entry must be a valid email address."
  }
}
