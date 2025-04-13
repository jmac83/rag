# --- Outputs ---
output "resource_group_name" {
  description = "The name of the resource group."
  value       = azurerm_resource_group.rg.name
}

# output "search_api_key" {
#   value = module.ai_search.search_api_key
#   sensitive = true
# }

# output "search_api_url" {
#   value = module.ai_search.search_api_url
# }

