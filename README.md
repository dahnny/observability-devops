# HNG Observability

Production-style LGTM observability stack for the Stage 6 DevOps task. The repo
provisions metrics, logs, traces, dashboards, alerts, SLOs, runbooks, DORA
metrics, and a sample instrumented FastAPI service.

## One-Command Deployment

```sh
cp .env.example .env
make up
```

Grafana runs at http://localhost:3000 with `admin` / `admin` unless changed in
`.env`.

Linux host-mode deployment with fuller node-exporter visibility:

```sh
make up-linux
```

Terraform wrapper:

```sh
cd terraform
terraform init
terraform apply
```

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

## GitHub DORA Metrics

Set these values in `.env`:

```sh
GITHUB_OWNER=your-org
GITHUB_REPO=your-repo
GITHUB_TOKEN=github_pat_or_token
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

```sh
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
