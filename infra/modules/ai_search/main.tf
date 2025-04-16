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
    null = {
      source  = "hashicorp/null"
      version = ">= 3.0"
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

resource "null_resource" "create_search_index_via_post" {
  
  provisioner "local-exec" {
    command = <<-EOT
      # Inlined API version string here
      curl -f -v -X POST "https://${random_pet.search_service_name.id}.search.windows.net/indexes?api-version=2023-10-01-Preview" \
      -H "Content-Type: application/json" \
      -H "api-key: ${azurerm_search_service.search_service.primary_key}" \
      -d "@${path.module}/rag-index.json"
    EOT
  }

  depends_on = [
    azurerm_search_service.search_service
  ]
}
