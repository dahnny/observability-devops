# Error Budget Policy

## SLO Targets

- Availability: 99.5% successful blackbox probes.
- Latency: 95% of successful requests complete below 500ms.
- Error rate: 99% of requests return non-5xx responses.

For a 30-day window, a 99% success SLO allows 1% bad events. Burn-rate alerts
detect when that budget is being consumed too quickly.

## Policy

- 50% consumed: service owner reviews recent changes and opens mitigation tasks.
- 75% consumed: non-critical feature releases require service-owner approval.
- 100% consumed: feature freeze until reliability is restored or leadership signs off.

## Ownership

The service owner owns SLO health. Platform engineering owns observability
tooling, alert routing, and dashboard correctness.

## Review Cadence

Review SLO targets, alert thresholds, and burn-rate noise every two weeks or
after every significant incident.
