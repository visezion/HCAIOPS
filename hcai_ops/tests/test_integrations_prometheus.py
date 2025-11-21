import os

import httpx

from hcai_ops.integrations.prometheus_scraper import scrape_all_prometheus_targets, scrape_prometheus_target


class DummyResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def test_scrape_prometheus_target(monkeypatch):
    sample = "cpu_usage 0.5\nmemory_usage 0.8\n"

    monkeypatch.setattr(httpx, "get", lambda url, timeout=10.0: DummyResponse(sample))
    events = scrape_prometheus_target("http://host:9100/metrics")
    assert len(events) == 2
    names = {e.metric_name for e in events}
    assert "cpu_usage" in names
    assert "memory_usage" in names


def test_scrape_all_prometheus_targets(monkeypatch):
    monkeypatch.setenv("HCAI_PROMETHEUS_ENABLED", "true")
    monkeypatch.setenv("HCAI_PROMETHEUS_TARGETS", "http://host:9100/metrics")
    sample = "cpu_usage 0.5\n"
    monkeypatch.setattr(httpx, "get", lambda url, timeout=10.0: DummyResponse(sample))
    events = scrape_all_prometheus_targets()
    assert events
