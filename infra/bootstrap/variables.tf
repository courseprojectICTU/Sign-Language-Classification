variable "project_id" {
  description = "Google Cloud project ID that owns the Terraform state bucket."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique name for the Terraform state bucket."
  type        = string
}

variable "location" {
  description = "Cloud Storage location for the Terraform state bucket."
  type        = string
  default     = "US"
}
