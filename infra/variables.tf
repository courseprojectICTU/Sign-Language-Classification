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

variable "log_analytics_workspace_name" {
  description = "Log Analytics Workspace name for Container Apps logs."
  type        = string
}

variable "container_app_environment_name" {
  description = "Azure Container Apps Environment name."
  type        = string
}

variable "image_repository" {
  description = "ACR repository name for the backend API image."
  type        = string
  default     = "vsl-api"
}

variable "image_tag" {
  description = "Immutable container image tag deployed to the Container App."
  type        = string

  validation {
    condition = (
      length(trimspace(var.image_tag)) > 0
      && lower(trimspace(var.image_tag)) != "latest"
    )
    error_message = "image_tag must be non-empty and must not use the mutable 'latest' tag."
  }
}

variable "container_cpu" {
  description = "vCPU allocated to each Container App replica."
  type        = number
  default     = 1

  validation {
    condition     = contains([0.5, 0.75, 1], var.container_cpu)
    error_message = "container_cpu must be one of 0.5, 0.75, or 1."
  }
}

variable "container_memory" {
  description = "Memory allocated to each Container App replica (1Gi-2Gi range)."
  type        = string
  default     = "2Gi"

  validation {
    condition     = contains(["1Gi", "1.5Gi", "2Gi"], var.container_memory)
    error_message = "container_memory must be one of 1Gi, 1.5Gi, or 2Gi."
  }
}

variable "container_min_replicas" {
  description = "Minimum replica count (must stay 0 on staging per BR-016)."
  type        = number
  default     = 0

  validation {
    condition     = var.container_min_replicas >= 0 && floor(var.container_min_replicas) == var.container_min_replicas
    error_message = "container_min_replicas must be a non-negative integer."
  }
}

variable "container_max_replicas" {
  description = "Maximum replica count for Container App autoscaling."
  type        = number
  default     = 3

  validation {
    condition     = var.container_max_replicas >= 1 && var.container_max_replicas <= 10 && floor(var.container_max_replicas) == var.container_max_replicas
    error_message = "container_max_replicas must be an integer between 1 and 10."
  }
}

variable "container_termination_grace_period_seconds" {
  description = "Grace period in seconds before forcing container termination."
  type        = number
  default     = 60

  validation {
    condition = (
      var.container_termination_grace_period_seconds >= 1
      && var.container_termination_grace_period_seconds <= 600
      && floor(var.container_termination_grace_period_seconds) == var.container_termination_grace_period_seconds
    )
    error_message = "container_termination_grace_period_seconds must be an integer between 1 and 600."
  }
}

variable "scale_cooldown_seconds" {
  description = "Cooldown window in seconds before scaling replicas down to min_replicas."
  type        = number
  default     = 300

  validation {
    condition = (
      var.scale_cooldown_seconds >= 60
      && var.scale_cooldown_seconds <= 3600
      && floor(var.scale_cooldown_seconds) == var.scale_cooldown_seconds
    )
    error_message = "scale_cooldown_seconds must be an integer between 60 and 3600."
  }
}

variable "http_scale_concurrent_requests" {
  description = "Concurrent HTTP requests per replica before scaling out."
  type        = number
  default     = 10

  validation {
    condition = (
      var.http_scale_concurrent_requests >= 1
      && floor(var.http_scale_concurrent_requests) == var.http_scale_concurrent_requests
    )
    error_message = "http_scale_concurrent_requests must be a positive integer."
  }
}

variable "allowed_origins" {
  description = "Comma-separated exact CORS origin allowlist for VSL_ALLOWED_ORIGINS."
  type        = string
  default     = ""
}
