#!/bin/bash

echo "Setting environment variables from Terraform outputs..."

export AZURE_SEARCH_API_KEY=$(terraform output -raw search_api_key)
export AZURE_SEARCH_API_URL=$(terraform output -raw search_api_url)
export AZURE_OPENAI_API_KEY=$(terraform output -raw openai_api_key)
export AZURE_OPENAI_ENDPOINT=$(terraform output -raw open_ai_endpoint_url)
export AzureWebJobsStorage=$(terraform output -raw function_storage_account_connection_string)
export UPLOAD_STORAGE_CONNECTION_STRING=$(terraform output -raw upload_storage_account_connection_string)
export UPLOAD_BLOB_PATH="uploads/{name}"
export AZURE_FUNCTION_APP_URL=$(terraform output -raw function_app_url)
export AZURE_FUNCTION_APP_KEY=$(terraform output -raw function_app_key)

echo "Done."
