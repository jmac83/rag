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

data "terraform_remote_state" "search_service" {
  backend = "local"
  config = {
    path = "../terraform.tfstate"
  }
}

provider "restapi" {
  uri = data.terraform_remote_state.search_service.outputs.search_api_url 
  headers = {
    "Content-Type" = "application/json"
    "api-key"      = data.terraform_remote_state.search_service.outputs.search_api_key   
  }
  write_returns_object = true
  debug                = true
}

resource "restapi_object" "search_index" {
  path         = "/indexes"
  query_string = "api-version=2023-10-01-Preview"
  data         = file("${path.module}/rag-index.json")
  id_attribute = "name"
}

