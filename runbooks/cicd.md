# CI/CD Reliability Runbook

## What This Alert Means

The delivery pipeline is either missing DORA telemetry, producing too many failed
changes, or taking too long to restore service after failed deployments.

## Likely Causes

- GitHub token, owner, or repository values are missing.
- A deployment workflow is repeatedly failing.
- A rollback, hotfix, or recovery workflow is taking longer than the agreed MTTR.

## First Investigation Steps

1. Open the DORA dashboard and identify whether DF, CFR, LTC, or MTTR is degraded.
2. Check the latest GitHub Actions runs for failed deploy or release workflows.
3. Compare the failed change with the latest production incident or rollback.

## Resolution

- Fix exporter configuration if telemetry is missing.
- Roll back or hotfix the failed deployment if user impact is active.
- Pause non-critical releases if CFR remains above threshold.

## Escalation

Escalate to the release owner and platform lead if CFR remains high for more than
30 minutes or MTTR exceeds one hour.
