from click.testing import CliRunner

from hcai_ops.console import cli
from hcai_ops.analytics import event_store


def _reset_store():
    event_store._events = []  # type: ignore[attr-defined]


def test_cli_pull_cloudflare(monkeypatch):
    _reset_store()
    monkeypatch.setattr("hcai_ops.integrations.cloudflare.pull_cloudflare_events", lambda limit=None: [])
    captured = []
    monkeypatch.setattr(event_store, "add_events", lambda events: captured.extend(events))
    runner = CliRunner()
    result = runner.invoke(cli, ["pull-cloudflare"])
    assert result.exit_code == 0


def test_cli_scrape_prometheus(monkeypatch):
    _reset_store()
    monkeypatch.setattr("hcai_ops.integrations.prometheus_scraper.scrape_all_prometheus_targets", lambda: [])
    captured = []
    monkeypatch.setattr(event_store, "add_events", lambda events: captured.extend(events))
    runner = CliRunner()
    res = runner.invoke(cli, ["scrape-prometheus"])
    assert res.exit_code == 0
