output "state_bucket_name" {
  description = "Name of the protected Cloud Storage bucket used for Terraform state."
  value       = google_storage_bucket.terraform_state.name
}
