variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "function_code_directory" {
  type        = string
}

variable "storage_account_connection_string" {
  type        = string
}

variable "uploads_container_name" {
  type = string
}

variable "open_ai_api_key" {
  type = string
}

variable "open_ai_endpoint" {
  type        = string
}

variable "ai_search_url" {
  type        = string  
}

variable "ai_search_key" {
  type        = string
}