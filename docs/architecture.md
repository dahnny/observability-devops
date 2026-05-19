# Architecture

The stack is a Docker Compose LGTM deployment with Prometheus, Loki, Tempo,
Grafana, OpenTelemetry Collector, Alertmanager, node-exporter, blackbox-exporter,
a DORA exporter, and an instrumented FastAPI sample service.

## Flow

1. Prometheus scrapes metrics from the app, exporters, collector, and DORA exporter.
2. The sample app sends OTLP traces and logs to the OpenTelemetry Collector.
3. The collector exports traces to Tempo and logs to Loki.
4. Grafana reads all three backends through provisioned datasources.
5. Prometheus evaluates version-controlled alert rules and sends alerts to Alertmanager.
6. Alertmanager groups, inhibits, and routes alerts to `#DevOps-Alerts`.

## Mac and Linux Modes

The default Compose stack avoids Docker Desktop hidden host paths and uses OTLP
application logs. The Linux override enables deeper host visibility for
node-exporter with a root filesystem mount.

## Retention

Local storage is filesystem-backed and intended for demo/submission evidence.
For production, move Loki and Tempo storage to object storage and set explicit
retention policies by environment.
