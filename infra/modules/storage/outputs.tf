output "storage_account_name" {
  value = azurerm_storage_account.storage_account.name
}

output "storage_account_primary_connection_string" {
  value     = azurerm_storage_account.storage_account.primary_connection_string
  sensitive = true
}

output "storage_account_primary_access_key" {
  value     = azurerm_storage_account.storage_account.primary_access_key
  sensitive = true
}

output "uploads_container_name" {
  value = azurerm_storage_container.uploads_container.name
}

output "functions_container_name" {
  value = azurerm_storage_container.functions_container.name
}
