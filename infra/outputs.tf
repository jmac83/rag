output "resource_group_name" {
  description = "The name of the resource group."
  value       = azurerm_resource_group.rg.name
}

 output "search_api_key" {
   value = module.ai_search.search_api_key
   sensitive = true
 }

 output "search_api_url" {
   value = module.ai_search.search_api_url
 }
 output "openai_api_key" {
   value = module.open_ai.open_ai_api_key
   sensitive = true
 }

 output "open_ai_endpoint_url" {
   value = module.open_ai.open_ai_endpoint
 } 

output "upload_storage_account_connection_string" {
  value = module.storage_account.storage_account_primary_connection_string
  sensitive = true
}

output "function_storage_account_connection_string" {
  value = module.function_app.function_storage_account_connection_string
  sensitive = true
}

output "chat_web_ui_url" {
  value = module.web_ui_app.chat_web_ui_url
}

output "function_app_url" {
  value = module.function_app.function_app_url
}

output "function_app_key" {
  value = module.function_app.function_app_key
  sensitive = true
}