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
    "requirements-dev.txt",
    "tests"
  ])
}

resource "random_pet" "storage_account_name" {
  prefix    = "func"
  separator = "x"
  length    = 1
}

resource "random_pet" "index_function_name" {
  prefix    = "index-function" 
  length    = 2
}

resource "azurerm_storage_account" "storage_account" {
  name                     = random_pet.storage_account_name.id 
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_service_plan" "function_plan" {
  name                = "index-function-plan"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "EP2"
}

resource "azurerm_application_insights" "function_insights" {
  name                = "index-function-insights"
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
  retention_in_days   = 30
  workspace_id = var.log_analytics_workspace_id
}

resource "azurerm_linux_function_app" "index_function" {
  name                       = random_pet.index_function_name.id 
  location                   = var.location
  resource_group_name        = var.resource_group_name
  service_plan_id            = azurerm_service_plan.function_plan.id
  storage_account_name       = azurerm_storage_account.storage_account.name
  storage_account_access_key = azurerm_storage_account.storage_account.primary_access_key

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME = "python"
    APPINSIGHTS_INSTRUMENTATIONKEY       = azurerm_application_insights.function_insights.instrumentation_key
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.function_insights.connection_string
    
    UPLOAD_BLOB_PATH = "${var.uploads_container_name}/{name}"
    UPLOAD_STORAGE_CONNECTION_STRING = var.storage_account_connection_string

    "HASH" = data.archive_file.function_app_zip.output_base64sha256
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    "AZURE_OPENAI_API_KEY" = var.open_ai_api_key
    "AZURE_OPENAI_ENDPOINT" = var.open_ai_endpoint
    "AZURE_SEARCH_API_URL" = var.ai_search_url
    "AZURE_SEARCH_API_KEY" = var.ai_search_key
  }
  identity {
    type = "SystemAssigned"
  }
  site_config {
    application_stack {
       python_version = "3.9"
    }
    always_on = true
    cors {
      allowed_origins     = [
        "https://portal.azure.com"
      ]
      support_credentials = true 
    }
  }
}

resource "null_resource" "function_app_deploy" {
  triggers = {
    zip_hash = data.archive_file.function_app_zip.output_base64sha256
  }

  provisioner "local-exec" {
    command = <<-EOT
      az functionapp deployment source config-zip \
        --resource-group ${azurerm_linux_function_app.index_function.resource_group_name} \
        --name ${azurerm_linux_function_app.index_function.name} \
        --src "${data.archive_file.function_app_zip.output_path}" \
        --build-remote true \
        --timeout 900
    EOT
  }
  depends_on = [azurerm_linux_function_app.index_function]
}

data "azurerm_function_app_host_keys" "host_keys" {
  name                = azurerm_linux_function_app.index_function.name
  resource_group_name = azurerm_linux_function_app.index_function.resource_group_name
}
