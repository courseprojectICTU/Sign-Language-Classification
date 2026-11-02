variable "project_id" {
  description = "Google Cloud project ID for this environment."
  type        = string
}

variable "region" {
  description = "Default Google Cloud region for this environment."
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
