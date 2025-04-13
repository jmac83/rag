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

data "archive_file" "function_app_zip" {
  type        = "zip"
  source_dir  = var.function_code_directory
  output_path = "${path.module}/function_app_code.zip"

  excludes = toset([
    ".venv",
    ".vscode",
    "__pycache__",
    "local.settings.json",
    ".funcignore",
    ".gitignore",
  ])
}

resource "random_pet" "storage_account_name" {
  prefix    = "func"
  separator = "x"
  length    = 1
}

resource "azurerm_storage_account" "storage_account" {
  name                     = random_pet.storage_account_name.id 
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_blob" "function_blob" {
  name                   = "index_function_app_code.zip"
  storage_account_name   = var.storage_account_name
  storage_container_name = var.functions_container_name 
  type                   = "Block"
  source                 = data.archive_file.function_app_zip.output_path
}


data "azurerm_storage_account_sas" "function_sas" {
  connection_string = var.storage_account_connection_string
  https_only        = true

  resource_types {
    service   = true
    container = true
    object    = true
  }

  services {
    blob  = true
    queue = false
    table = false
    file  = false
  }

  start  = "2025-01-01T00:00:00Z"
  expiry = "2030-01-01T00:00:00Z"

  permissions {
    read    = true
    write   = false
    delete  = false
    list    = false
    add     = false
    create  = false
    update  = false
    process = false
    tag     = false
    filter  = false
  }
}

resource "azurerm_service_plan" "function_plan" {
  name                = "index-function-plan"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "EP1"
}

resource "random_pet" "workspace_name" {
  prefix    = "la-workspace"
  length    = 2
}

resource "azurerm_log_analytics_workspace" "workspace" {
  name                = random_pet.workspace_name.id
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "function_insights" {
  name                = "index-function-insights"
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
  retention_in_days   = 30
  workspace_id = azurerm_log_analytics_workspace.workspace.id
}

resource "azurerm_linux_function_app" "example" {
  name                       = "index-function-app"
  location                   = var.location
  resource_group_name        = var.resource_group_name

  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_access_key
  service_plan_id            = azurerm_service_plan.function_plan.id
  app_settings = {
    FUNCTIONS_WORKER_RUNTIME = "python"
    WEBSITE_RUN_FROM_PACKAGE = "https://${var.storage_account_name}.blob.core.windows.net/${var.functions_container_name}/${azurerm_storage_blob.function_blob.name}?${data.azurerm_storage_account_sas.function_sas.sas}"
    APPINSIGHTS_INSTRUMENTATIONKEY       = azurerm_application_insights.function_insights.instrumentation_key
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.function_insights.connection_string
    AZURE_STORAGE_CONNECTION_STRING = var.storage_account_connection_string
    "AzureWebJobsStorage": var.storage_account_connection_string

    "AzureWebJobsStorageType": "Files"
    BLOB_PATH = "${var.uploads_container_name}/{name}"
    STORAGE_CONNECTION_STRING = var.storage_account_connection_string
  }
  identity {
    type = "SystemAssigned"
  }
  site_config {
    application_stack {
       python_version = "3.9"
    }
    always_on = true
  }
}
