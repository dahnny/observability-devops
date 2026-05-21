locals {
  repo_root = abspath("${path.module}/..")

  managed_files = concat(
    var.compose_files,
    [
      "alertmanager/alertmanager.yml",
      "alertmanager/templates/slack.tmpl",
      "blackbox/blackbox.yml",
      "grafana/provisioning/dashboards/dashboards.yml",
      "grafana/provisioning/datasources/datasources.yml",
      "loki/loki-config.yml",
      "otel-collector/otel-collector-config.yml",
      "prometheus/prometheus.yml",
      "prometheus/alerts/cicd.yml",
      "prometheus/alerts/infrastructure.yml",
      "prometheus/alerts/slo-burn-rate.yml",
      "tempo/tempo.yml",
    ]
  )

  compose_args = join(" ", [for file in var.compose_files : "-f ${file}"])
  config_hash  = sha256(join("", [for file in local.managed_files : filesha256("${local.repo_root}/${file}")]))
  runtime_config_hash = sha256(jsonencode({
    slack_webhook_url = nonsensitive(sha256(var.slack_webhook_url))
    github_owner      = sha256(var.github_owner)
    github_repo       = sha256(var.github_repo)
    github_token      = nonsensitive(sha256(var.github_token))
  }))
}

resource "terraform_data" "observability_stack" {
  input = {
    project      = var.project_name
    compose_args = local.compose_args
    config_hash  = local.config_hash
    repo_root    = local.repo_root
  }

  triggers_replace = [
    join(",", var.compose_files),
    local.config_hash,
    local.runtime_config_hash,
  ]

  provisioner "local-exec" {
    command     = "docker compose ${self.input.compose_args} up -d --build"
    working_dir = self.input.repo_root
    environment = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
      GITHUB_OWNER      = var.github_owner
      GITHUB_REPO       = var.github_repo
      GITHUB_TOKEN      = var.github_token
    }
  }

  provisioner "local-exec" {
    when        = destroy
    command     = "docker compose ${self.input.compose_args} down"
    working_dir = self.input.repo_root
    on_failure  = continue
  }
}
