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

resource "azurerm_application_insights" "web_ui_insights" {
  name                = "web-ui-insights"
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
  retention_in_days   = 30
  workspace_id = var.log_analytics_workspace_id
}


data "archive_file" "web_ui_app_zip" {
  type        = "zip"
  source_dir  = var.web_ui_code_directory
  output_path = "${path.module}/web_ui_app.zip"

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

resource "azurerm_service_plan" "chat_ui_plan" {
  name                = "chat-web-ui-plan"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "S1" 
}

resource "azurerm_linux_web_app" "chat_web_ui_app" {
  name                = "chat-web-ui"
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.chat_ui_plan.id

  site_config {
    always_on         = true
    application_stack {
       python_version = "3.9"
    }
    app_command_line = "python -m streamlit run app.py --server.port $PORT --server.address 0.0.0.0"
    ftps_state        = "FtpsOnly" 
  }

  app_settings = {
    APPINSIGHTS_INSTRUMENTATIONKEY       = azurerm_application_insights.web_ui_insights.instrumentation_key
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.web_ui_insights.connection_string
    
    "AZURE_OPENAI_API_KEY" = var.open_ai_api_key
    "AZURE_OPENAI_ENDPOINT" = var.open_ai_endpoint
    "AZURE_SEARCH_API_URL" = var.ai_search_url
    "AZURE_SEARCH_API_KEY" = var.ai_search_key
    "WEBSITES_PORT"                       = "8000" 
    
    "APP_ZIP_HASH"         = data.archive_file.web_ui_app_zip.output_base64sha256
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
  }

  identity {
    type = "SystemAssigned"
  }
}

resource "null_resource" "webapp_deploy" {
  triggers = {
    zip_hash = data.archive_file.web_ui_app_zip.output_base64sha256
  }


  provisioner "local-exec" {
    command = <<-EOT
      az webapp deploy \
        --resource-group ${var.resource_group_name} \
        --name ${azurerm_linux_web_app.chat_web_ui_app.name} \
        --src-path "${path.module}/web_ui_app.zip" \
        --type zip \
        --timeout 900
    EOT
  }
  depends_on = [azurerm_linux_web_app.chat_web_ui_app]
}

