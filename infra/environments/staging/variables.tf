variable "environment" {
  description = "Environment name."
  type        = string

  validation {
    condition     = var.environment == "staging"
    error_message = "The staging root only accepts environment = staging."
  }
}

variable "subscription_id" {
  description = "Subscription containing the staging Container App resources."
  type        = string
}

variable "registry_subscription_id" {
  description = "Subscription containing the shared Azure Container Registry."
  type        = string
}

variable "resource_group_name" {
  description = "Existing staging resource group."
  type        = string
}

variable "location" {
  description = "Azure region for staging."
  type        = string
}

variable "container_app_environment_name" {
  description = "Staging Container Apps environment name."
  type        = string
}

variable "container_app_name" {
  description = "Staging Container App service name."
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
  description = "Container memory allocation."
  type        = string
}

variable "min_replicas" {
  description = "Minimum number of staging replicas."
  type        = number
}

variable "max_replicas" {
  description = "Maximum number of staging replicas."
  type        = number
}

variable "environment_variables" {
  description = "Non-secret application environment variables."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Additional Azure resource tags."
  type        = map(string)
  default     = {}
}
