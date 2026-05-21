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

variable "slack_webhook_url" {
  description = "Slack webhook URL passed to Alertmanager through Docker Compose environment."
  type        = string
  default     = ""
  sensitive   = true
}

variable "github_owner" {
  description = "GitHub repository owner used by the DORA exporter."
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository name used by the DORA exporter."
  type        = string
  default     = ""
}

variable "github_token" {
  description = "GitHub token used by the DORA exporter."
  type        = string
  default     = ""
  sensitive   = true
}
