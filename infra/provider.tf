provider "azurerm" {
  features {}

  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none"
}

provider "azurerm" {
  alias = "registry"

  features {}

  subscription_id                 = coalesce(trimspace(var.registry_subscription_id), var.subscription_id)
  resource_provider_registrations = "none"
}

provider "azuread" {}
