output "storage_account_name" {
  description = "Storage Account containing Terraform state."
  value       = azurerm_storage_account.terraform_state.name
}

output "container_name" {
  description = "Private Blob container for Terraform state."
  value       = azurerm_storage_container.terraform_state.name
}
