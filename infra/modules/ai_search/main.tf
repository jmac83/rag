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
    restapi = {
      source  = "Mastercard/restapi"
      version = "~> 1.18.2"
    }
  }
}

resource "random_pet" "search_service_name" {
  prefix    = "aifitsearch" # Prefix for Search service
  separator = "-"
  length    = 2
}

resource "azurerm_search_service" "search_service" {
  name                = random_pet.search_service_name.id
  resource_group_name = var.resource_group_name 
  location            = var.location
  sku = "standard"

  replica_count   = 1
  partition_count = 1

  public_network_access_enabled = true

  tags = {
    environment = "poc-rag"
  }
}


#provider "restapi" {
#  uri = "https://${random_pet.search_service_name.id}.search.windows.net"
#  #uri = "http://google.com"
#  headers = {
#    "Content-Type" = "application/json"
#    "api-key"      = sensitive(azurerm_search_service.search_service.primary_key)
#  }
#  write_returns_object = true
#  debug                = true
#}
#
#resource "restapi_object" "search_index" {
#  path         = "/indexs"
#  query_string = "api-version=2023-10-01-Preview"
#  data         = file("${path.module}/rag-index.json")
#  id_attribute = "name"
#  depends_on   = [azurerm_search_service.search_service]
#}

