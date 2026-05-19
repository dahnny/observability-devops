output "project_name" {
  description = "The configured project name."
  value       = var.project_name
}

output "grafana_url" {
  description = "Local Grafana URL."
  value       = "http://localhost:3000"
}

output "prometheus_url" {
  description = "Local Prometheus URL."
  value       = "http://localhost:9090"
}
