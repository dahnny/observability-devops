# Blameless Post-Incident Review

## Summary

Latency injection during Game Day caused `/slow` requests to exceed the 500ms SLO
target. Prometheus detected the SLI degradation, Grafana showed the latency
increase, and Loki logs linked to Tempo traces for the affected endpoint.

## Timeline

- Detection: Blackbox and application latency panels showed degraded service.
- Response: On-call reviewed the Unified Observability dashboard.
- Diagnosis: Logs with `trace_id` linked to slow Tempo spans from `/slow`.
- Resolution: Latency injection was stopped and service metrics recovered.

## Impact

Users of the affected endpoint experienced slow responses during the simulation.
No data loss occurred.

## Root Cause

Intentional latency was introduced to validate SLO monitoring and burn-rate
alerting.

## What Went Well

- Metrics, logs, and traces shared service and trace context.
- Dashboard drill-down reduced time to identify the endpoint.

## What Needs Improvement

- Add automated Game Day scripts for repeatable evidence capture.
- Add production retention and object storage before real deployment.

## Action Items

- Platform owner: automate latency and error injection scripts.
- Service owner: add endpoint-specific SLO panels.
- Release owner: connect DORA exporter to the production GitHub repository.
