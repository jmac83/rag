output "function_storage_account_connection_string" {
  value = azurerm_storage_account.storage_account.primary_connection_string
  sensitive = true
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.index_function.default_hostname}"
}

output "function_app_key" {
  value       = data.azurerm_function_app_host_keys.host_keys.default_function_key
  sensitive   = true
}