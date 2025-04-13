# Configure the Azure provider
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0.1"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 1.0.0"
    }
 }
}

resource "random_pet" "storage_account_name" {
  prefix    = "ragstac" # Prefix for Search service
  separator = "x"
  length    = 1
}

resource "azurerm_storage_account" "storage_account" {
  name                     = random_pet.storage_account_name.id 
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = {
    environment = "poc-rag"
  }
}

resource "azurerm_storage_container" "uploads_container" {
  name                  = "uploads"
  storage_account_name  = azurerm_storage_account.storage_account.name
  container_access_type = "private"
  depends_on = [azurerm_storage_account.storage_account]
}

resource "azurerm_storage_container" "functions_container" {
  name                  = "functions"
  storage_account_name  = azurerm_storage_account.storage_account.name
  container_access_type = "private"
  depends_on = [azurerm_storage_account.storage_account]
}
