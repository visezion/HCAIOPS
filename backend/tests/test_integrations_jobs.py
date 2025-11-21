from hcai_ops.analytics import event_store
from hcai_ops.automation.jobs import (
    cloudflare_pull_job,
    prometheus_scrape_job,
    docker_metrics_job,
    k8s_events_job,
)


def _reset_store():
    event_store._events = []  # type: ignore[attr-defined]


def test_jobs_disabled(monkeypatch):
    _reset_store()
    monkeypatch.setenv("HCAI_CLOUDFLARE_ENABLED", "false")
    monkeypatch.setenv("HCAI_PROMETHEUS_ENABLED", "false")
    monkeypatch.setenv("HCAI_DOCKER_ENABLED", "false")
    monkeypatch.setenv("HCAI_K8S_ENABLED", "false")
    assert cloudflare_pull_job() == []
    assert prometheus_scrape_job() == []
    assert docker_metrics_job() == []
    assert k8s_events_job() == []


def test_jobs_enabled(monkeypatch):
    _reset_store()
    monkeypatch.setenv("HCAI_CLOUDFLARE_ENABLED", "true")
    monkeypatch.setenv("HCAI_CLOUDFLARE_API_TOKEN", "token")
    monkeypatch.setenv("HCAI_CLOUDFLARE_ZONE_ID", "zone")
    monkeypatch.setenv("HCAI_CLOUDFLARE_ACCOUNT_ID", "acct")
    monkeypatch.setattr("hcai_ops.integrations.cloudflare.pull_cloudflare_events", lambda limit=None: [])
    monkeypatch.setenv("HCAI_PROMETHEUS_ENABLED", "true")
    monkeypatch.setenv("HCAI_PROMETHEUS_TARGETS", "")
    monkeypatch.setenv("HCAI_DOCKER_ENABLED", "true")
    monkeypatch.setenv("HCAI_K8S_ENABLED", "true")
    monkeypatch.setattr("hcai_ops.integrations.prometheus_scraper.scrape_all_prometheus_targets", lambda: [])
    monkeypatch.setattr("hcai_ops.automation.jobs.collect_docker_metrics", lambda: [])
    monkeypatch.setattr("hcai_ops.automation.jobs.fetch_recent_k8s_events", lambda limit=100: [])
    assert cloudflare_pull_job() == []
    assert prometheus_scrape_job() == []
    assert docker_metrics_job() == []
    assert k8s_events_job() == []
