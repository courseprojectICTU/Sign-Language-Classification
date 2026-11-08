variable "subscription_id" {
  description = "Azure subscription ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be a UUID."
  }
}

variable "resource_group_name" {
  description = "Existing Resource Group for the Terraform state resources."
  type        = string
}

variable "location" {
  description = "Azure region for the Terraform state resources."
  type        = string
}

variable "storage_account_name" {
  description = "Globally unique Storage Account name (3-24 lowercase letters or digits)."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "storage_account_name must contain 3-24 lowercase letters or digits."
  }
}

variable "container_name" {
  description = "Private Blob container name for Terraform state."
  type        = string
  default     = "tfstate"

  validation {
    condition = (
      length(var.container_name) >= 3 &&
      length(var.container_name) <= 63 &&
      can(regex("^[a-z0-9]+(-[a-z0-9]+)*$", var.container_name))
    )
    error_message = "container_name must be 3-63 characters using lowercase letters, digits, and non-adjacent hyphens."
  }
}
