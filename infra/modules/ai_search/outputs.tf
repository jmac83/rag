output search_api_url {
    value = "https://${random_pet.search_service_name.id}.search.windows.net"
}

output search_api_key {
    value = azurerm_search_service.search_service.primary_key
    sensitive = true
}


