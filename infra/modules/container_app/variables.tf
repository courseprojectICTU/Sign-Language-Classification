variable "environment" {
  description = "Environment name used for resource tags."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "resource_group_name" {
  description = "Existing resource group for this environment's Container Apps."
  type        = string
}

variable "location" {
  description = "Azure region for this environment."
  type        = string
}

variable "container_app_environment_name" {
  description = "Unique Container Apps environment name."
  type        = string
}

variable "container_app_name" {
  description = "Unique Container App service name."
  type        = string
}

variable "registry_name" {
  description = "Name of the shared Azure Container Registry."
  type        = string
}

variable "registry_resource_group_name" {
  description = "Resource group containing the shared registry."
  type        = string
}

variable "image_repository" {
  description = "Repository path within the shared registry."
  type        = string
}

variable "image_tag" {
  description = "Already-published image tag to deploy."
  type        = string
}

variable "cpu" {
  description = "Container CPU allocation in vCPUs."
  type        = number
}

variable "memory" {
  description = "Container memory allocation, such as 1Gi."
  type        = string
}

variable "min_replicas" {
  description = "Minimum number of Container App replicas."
  type        = number

  validation {
    condition     = var.min_replicas >= 0 && var.min_replicas <= 300
    error_message = "min_replicas must be between 0 and 300."
  }
}

variable "max_replicas" {
  description = "Maximum number of Container App replicas."
  type        = number

  validation {
    condition     = var.max_replicas >= 1 && var.max_replicas <= 300
    error_message = "max_replicas must be between 1 and 300."
  }
}

variable "environment_variables" {
  description = "Non-secret environment variables for the application."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Additional Azure resource tags."
  type        = map(string)
  default     = {}
}
