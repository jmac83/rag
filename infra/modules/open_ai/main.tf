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

resource "random_pet" "cognitive_account_name" {
  prefix    = "aifitcoach" 
  separator = "-"
  length    = 2
}

resource "azapi_resource" "openai" {
  type                      = "Microsoft.CognitiveServices/accounts@2021-04-30"
  name                      = random_pet.cognitive_account_name.id
  parent_id                 = var.resource_group_id
  body                      = <<JSON
{
  "location": "${var.location}",
  "kind": "OpenAI",
  "sku": {
    "name": "S0"
  },
  "properties": {}
}
JSON
  schema_validation_enabled = false
}

resource "azapi_resource_action" "openai_keys" {
  type                   = "Microsoft.CognitiveServices/accounts@2021-04-30"
  resource_id            = azapi_resource.openai.id
  action                 = "listKeys"
  response_export_values = ["*"]
}

locals {
  openai_endpoint = "https://${azapi_resource.openai.name}.openai.azure.com/"
  openai_key      = jsondecode(azapi_resource_action.openai_keys.output).key1
}

resource "azurerm_cognitive_deployment" "ada_embedding" {
  name                 = "text-embedding-ada-002"
  cognitive_account_id = azapi_resource.openai.id 

  model {
    format  = "OpenAI"
    name    = "text-embedding-ada-002"
    version = "2"
  }
  sku {
    name = "Standard"
  }

  depends_on = [
    azapi_resource.openai
  ]
}

