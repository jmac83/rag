output "open_ai_endpoint" {
    value     = local.openai_endpoint
}

output "open_ai_api_key" {
  value       = local.openai_key
  sensitive   = true 
}
