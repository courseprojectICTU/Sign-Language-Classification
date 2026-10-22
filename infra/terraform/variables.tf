variable "project_id" {
  description = "Existing GCP project with billing enabled."
  type        = string
}
variable "region" {
  type    = string
  default = "asia-southeast1"
}
variable "github_repository" {
  description = "Full GitHub owner/repo allowed to authenticate."
  type        = string
  default     = "courseprojectICTU/Sign-Language-Classification"
}
