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

  required_version = ">= 1.1.0"
}

provider "azapi" {
}

provider "azurerm" {
  subscription_id = var.subscription_id
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

provider "random" {}


resource "random_pet" "rg_name" {
  prefix    = "rg-aifitcoach"
  separator = "-"
  length    = 2
}

resource "azurerm_resource_group" "rg" {
  name     = random_pet.rg_name.id
  location = "westus"
}

module "monitor" {
  source = "./modules/monitor"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  providers = {
    azurerm = azurerm
    random = random
  }
}

module "storage_account" {
  source = "./modules/storage"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  providers = {
    azurerm = azurerm
    random = random
  }
}

 module "ai_search" {
   source = "./modules/ai_search"

   resource_group_name = azurerm_resource_group.rg.name
   location            = azurerm_resource_group.rg.location

   providers = {
     azurerm = azurerm
     random = random
   }
 }

 module "open_ai" {
   source = "./modules/open_ai"

   resource_group_id   = azurerm_resource_group.rg.id
   location            = azurerm_resource_group.rg.location

   providers = {
     azurerm = azurerm
     random = random
   }
 }

module "function_app" {
  source = "./modules/functions/"
  resource_group_name   = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  function_code_directory = "${path.module}/../function-app/"
  storage_account_connection_string = module.storage_account.storage_account_primary_connection_string
  uploads_container_name = module.storage_account.uploads_container_name
  open_ai_api_key = module.open_ai.open_ai_api_key
  open_ai_endpoint = module.open_ai.open_ai_endpoint
  ai_search_url = module.ai_search.search_api_url
  ai_search_key = module.ai_search.search_api_key
  log_analytics_workspace_id = module.monitor.log_analytics_workspace_id

  providers = {
    azurerm = azurerm
    random = random
  }
}

module "web_ui_app" {
  source = "./modules/web_ui/"
  resource_group_name   = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  web_ui_code_directory = "${path.module}/../chat-ui/"
  open_ai_api_key = module.open_ai.open_ai_api_key
  open_ai_endpoint = module.open_ai.open_ai_endpoint
  ai_search_url = module.ai_search.search_api_url
  ai_search_key = module.ai_search.search_api_key
  log_analytics_workspace_id = module.monitor.log_analytics_workspace_id
  function_app_url = module.function_app.function_app_url
  function_app_key = module.function_app.function_app_key

  providers = {
    azurerm = azurerm
    random = random
  }
}