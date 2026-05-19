variable "project_name" {
  description = "Name used to identify the observability stack."
  type        = string
  default     = "hng-observability"
}

variable "compose_files" {
  description = "Compose files Terraform should use to start the stack."
  type        = list(string)
  default     = ["docker-compose.yml"]
}
