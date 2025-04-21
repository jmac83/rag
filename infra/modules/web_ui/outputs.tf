output "chat_web_ui_url" {
  value     = "https://${azurerm_linux_web_app.chat_web_ui_app.default_hostname}"
}
