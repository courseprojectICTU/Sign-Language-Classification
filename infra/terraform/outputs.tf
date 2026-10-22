output "artifact_registry_host" {
  value = "${var.region}-docker.pkg.dev"
}
output "artifact_registry_repository" {
  value = google_artifact_registry_repository.backend.repository_id
}
output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}
output "github_service_account" {
  value = google_service_account.github_ci.email
}
