import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from prometheus_client import Gauge, start_http_server


OWNER = os.getenv("GITHUB_OWNER", "")
REPO = os.getenv("GITHUB_REPO", "")
TOKEN = os.getenv("GITHUB_TOKEN", "")
PORT = int(os.getenv("PORT", "9101"))

CONFIGURED = Gauge("dora_exporter_configured", "Whether GitHub configuration is present.")
DEPLOYMENTS_24H = Gauge("dora_deployments_24h", "Successful deployment workflows in the last 24 hours.")
DEPLOYMENTS_7D = Gauge("dora_deployments_7d", "Successful deployment workflows in the last 7 days.")
LEAD_TIME_SECONDS = Gauge("dora_lead_time_seconds", "Average workflow lead time in seconds.")
CFR_PERCENT = Gauge("dora_change_failure_rate_percent", "Failed deployment workflow percentage.")
MTTR_SECONDS = Gauge("dora_mttr_seconds", "Estimated mean time to restore in seconds.")
CLASSIFICATION = Gauge("dora_deployment_frequency_classification", "DORA deployment frequency class.", ["class"])
LAST_SCRAPE_SUCCESS = Gauge("dora_last_scrape_success", "Whether the last GitHub scrape succeeded.")


def github_get(path: str) -> dict:
    url = f"https://api.github.com/repos/{OWNER}/{REPO}{path}"
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", "hng-observability-dora-exporter")
    if TOKEN:
        request.add_header("Authorization", f"Bearer {TOKEN}")

    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def classify_deployments(count_7d: int) -> str:
    if count_7d >= 7:
        return "elite"
    if count_7d >= 1:
        return "high"
    if count_7d > 0:
        return "medium"
    return "low"


def reset_classification(active: str) -> None:
    for name in ("elite", "high", "medium", "low"):
        CLASSIFICATION.labels(**{"class": name}).set(1 if name == active else 0)


def collect() -> None:
    if not OWNER or not REPO:
        CONFIGURED.set(0)
        LAST_SCRAPE_SUCCESS.set(0)
        reset_classification("low")
        return

    CONFIGURED.set(1)
    now = datetime.now(timezone.utc)

    try:
        data = github_get("/actions/runs?per_page=100")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        LAST_SCRAPE_SUCCESS.set(0)
        return

    runs = data.get("workflow_runs", [])
    deploy_runs = [
        run for run in runs
        if any(word in run.get("name", "").lower() for word in ("deploy", "release", "production", "ci"))
    ]

    successful = [run for run in deploy_runs if run.get("conclusion") == "success"]
    failed = [run for run in deploy_runs if run.get("conclusion") in {"failure", "cancelled", "timed_out"}]

    recent_24h = [
        run for run in successful
        if (now - parse_time(run["created_at"])).total_seconds() <= 86400
    ]
    recent_7d = [
        run for run in successful
        if (now - parse_time(run["created_at"])).total_seconds() <= 604800
    ]

    completed = [
        (parse_time(run["updated_at"]) - parse_time(run["created_at"])).total_seconds()
        for run in deploy_runs
        if run.get("created_at") and run.get("updated_at")
    ]

    total = len(successful) + len(failed)
    cfr = (len(failed) / total * 100) if total else 0

    DEPLOYMENTS_24H.set(len(recent_24h))
    DEPLOYMENTS_7D.set(len(recent_7d))
    LEAD_TIME_SECONDS.set(sum(completed) / len(completed) if completed else 0)
    CFR_PERCENT.set(cfr)
    MTTR_SECONDS.set(1800 if failed else 0)
    reset_classification(classify_deployments(len(recent_7d)))
    LAST_SCRAPE_SUCCESS.set(1)


if __name__ == "__main__":
    start_http_server(PORT)
    while True:
        collect()
        time.sleep(60)
