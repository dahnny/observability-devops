# HNG Observability

Production-style LGTM observability stack for the Stage 6 DevOps task. The repo
provisions metrics, logs, traces, dashboards, alerts, SLOs, runbooks, DORA
metrics, and a sample instrumented FastAPI service.

## One-Command Deployment

Terraform is the required entrypoint for the submission. It provisions the full
Docker Compose stack and all mounted configuration comes from version-controlled
files in this repository.

```sh
terraform -chdir=terraform init && terraform -chdir=terraform apply -auto-approve
```

Optional credentials can be provided through Terraform variables:

```sh
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Then edit `terraform/terraform.tfvars` with `slack_webhook_url`,
`github_owner`, `github_repo`, and `github_token`. The file is ignored by git.

Grafana runs at http://localhost:3000 with `admin` / `admin`.

Linux host-mode deployment with fuller node-exporter visibility:

```sh
terraform -chdir=terraform apply -auto-approve -var='compose_files=["docker-compose.yml","docker-compose.linux.yml"]'
```

To tear down the Terraform-provisioned stack:

```sh
terraform -chdir=terraform destroy -auto-approve
```

`make up` and `make up-linux` are developer shortcuts only; use Terraform for
submission evidence.

## Services

- Sample app: http://localhost:8000
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
- Grafana: http://localhost:3000
- Loki: http://localhost:3100
- Tempo: http://localhost:3200
- Blackbox Exporter: http://localhost:9115
- DORA Exporter: http://localhost:9101/metrics

## Data Flow

- Prometheus scrapes app metrics, node-exporter, blackbox, collector metrics, and
  DORA exporter metrics.
- The sample app sends OpenTelemetry traces and logs to the OTel Collector.
- The collector exports traces to Tempo and logs to Loki.
- Grafana reads Prometheus, Loki, and Tempo using provisioned datasource files.
- Alertmanager routes Prometheus alerts to `#DevOps-Alerts` through
  `SLACK_WEBHOOK_URL`.
- Prometheus scrape configs, alert rules, Alertmanager routing, Loki/Tempo config,
  Grafana datasources, and dashboard JSON are all committed and mounted by the
  Terraform-provisioned Compose stack. No Grafana UI changes are required.

## GitHub DORA Metrics

Set these values in `terraform/terraform.tfvars`:

```hcl
github_owner = "your-org"
github_repo  = "your-repo"
github_token = "github_pat_or_token"
```

The token needs read access to GitHub Actions workflow runs. The exporter exposes
deployment frequency, lead time, change failure rate, MTTR, and deployment
frequency classification.

## Four Golden Signals

- Latency: `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))`
- Traffic: `sum(rate(http_requests_total[5m]))`
- Errors: `sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`
- Saturation: CPU, memory, disk, and load from node-exporter metrics.

## SLOs

- Availability: 99.5% successful HTTP probes over 30 days.
- Latency: 95% of successful requests under 500ms.
- Error rate: 99% of application requests are non-5xx.
- Saturation: CPU and memory should stay below 80% warning thresholds.

## Dashboards

All dashboards are provisioned from `grafana/dashboards`:

- DORA Metrics
- SLO Error Budget
- Node Exporter
- Blackbox Monitoring
- Unified Observability

The Loki datasource has a derived field for `trace_id`, allowing logs emitted by
the sample app to link directly to Tempo traces.

## Validation

The stack was validated on 2026-05-20 using the Terraform entrypoint:

```sh
terraform -chdir=terraform apply -auto-approve
```

Result: Terraform completed with no pending changes and reported the local
service URLs for Grafana, Prometheus, Alertmanager, and the project name.

Static checks run:

```sh
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
docker compose config --no-interpolate
python3 -m py_compile sample-app/app/main.py dora-exporter/app.py
jq empty grafana/dashboards/*.json
docker compose exec -T otel-collector /otelcol-contrib validate --config=/etc/otelcol-contrib/otel-collector-config.yml
```

Result: all checks passed. `docker compose config --no-interpolate` is used so
the generated Compose configuration can be checked without printing secret
values from `.env` or Terraform variables.

Runtime service checks run:

```sh
docker compose ps
curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health
curl -s -o /dev/null -w '%{http_code}' http://localhost:9090/-/ready
curl -s -o /dev/null -w '%{http_code}' http://localhost:9093/-/ready
curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/health
curl -s -o /dev/null -w '%{http_code}' http://localhost:3100/ready
curl -s -o /dev/null -w '%{http_code}' http://localhost:3200/ready
curl -s -o /dev/null -w '%{http_code}' http://localhost:9115/-/healthy
curl -s -o /dev/null -w '%{http_code}' http://localhost:9101/metrics
curl -s -o /dev/null -w '%{http_code}' http://localhost:8889/metrics
```

Result: all containers were up. HTTP checks returned 200 for the sample app,
Prometheus, Alertmanager, Grafana, Loki, Tempo, Blackbox Exporter, DORA Exporter,
and the OTel Collector Prometheus exporter.

Mounted configuration paths checked inside containers:

```text
prometheus:/etc/prometheus/prometheus.yml
alertmanager:/etc/alertmanager/alertmanager.yml
grafana:/etc/grafana/provisioning/datasources/datasources.yml
grafana:/var/lib/grafana/dashboards/unified-observability.json
loki:/etc/loki/loki-config.yml
tempo:/etc/tempo/tempo.yml
otel-collector:/etc/otelcol-contrib/otel-collector-config.yml
blackbox:/etc/blackbox_exporter/blackbox.yml
```

Result: all required mounted paths were present and readable by their services.

Telemetry checks run:

```sh
curl -s -G http://localhost:9090/api/v1/query --data-urlencode 'query=up'
curl -s -G http://localhost:9090/api/v1/query --data-urlencode 'query=http_requests_total{job="sample-app"}'
curl -s -G 'http://localhost:3100/loki/api/v1/query' --data-urlencode 'query={service_name="sample-app"}'
curl -s -G http://localhost:3200/api/search --data-urlencode 'tags=service.name=sample-app'
curl -s http://localhost:9101/metrics
```

Result: Prometheus reported all scrape targets as `up == 1`, the sample app
exported request metrics, Loki returned `sample-app` log streams with `trace_id`
labels, and Tempo returned searchable `sample-app` traces. The DORA exporter was
reachable; it reports `dora_exporter_configured 0` until `github_owner`,
`github_repo`, and `github_token` are supplied through Terraform variables.

Reusable local validation commands:

```sh
terraform -chdir=terraform validate
make validate
python3 -m py_compile sample-app/app/main.py dora-exporter/app.py
jq empty grafana/dashboards/*.json
```

If `promtool` or `amtool` are installed:

```sh
promtool check rules prometheus/alerts/*.yml
amtool check-config alertmanager/alertmanager.yml
```

Runtime checks:

```sh
curl http://localhost:8000/
curl http://localhost:8000/checkout
curl http://localhost:8000/slow
curl http://localhost:8000/error
```

Grafana Explore queries:

```logql
{service_name="sample-app"} | json
```

```promql
sum(rate(http_requests_total[5m]))
```

## Game Day Scenarios

- Deployment failure: force a failed GitHub Actions deployment and verify DORA
  CFR/MTTR panels and alerts.
- Latency injection: call `/slow` repeatedly and verify latency SLI degradation,
  logs, traces, and burn-rate behavior.
- Resource pressure: on Linux profile, run CPU or memory pressure and confirm
  warning alerts fire before critical alerts and recovery notifications are sent.

## Evidence Checklist

- LGTM services running in Docker Compose.
- Screenshots of all five Grafana dashboards.
- Loki log query with clickable `trace_id` to Tempo.
- Prometheus alert rule files and Alertmanager Slack route.
- Firing and resolved Slack alerts.
- Game Day trigger, degradation, alert, trace, and recovery screenshots.
- Runbook and post-incident review documents.
