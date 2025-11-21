import asyncio
import os

from hcai_ops.integrations.cloudflare import fetch_cloudflare_events, pull_cloudflare_events


class DummyResp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


class DummyClient:
    last_endpoint = None

    def __init__(self, base_url=None, headers=None, timeout=None):
        self.headers = headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, endpoint):
        DummyClient.last_endpoint = endpoint
        return DummyResp(
            {
                "result": [
                    {
                        "EdgeResponseStatus": 200,
                        "ClientRequestMethod": "GET",
                        "ClientRequestURI": "/",
                        "ClientIP": "1.1.1.1",
                        "ClientRequestUserAgent": "ua",
                    }
                ]
            }
        )


def test_fetch_cloudflare_events(monkeypatch):
    monkeypatch.setenv("HCAI_CLOUDFLARE_ENABLED", "true")
    monkeypatch.setenv("HCAI_CLOUDFLARE_API_TOKEN", "token")
    monkeypatch.setenv("HCAI_CLOUDFLARE_ACCOUNT_ID", "acct")
    monkeypatch.setenv("HCAI_CLOUDFLARE_ZONE_ID", "zone")
    monkeypatch.setenv("HCAI_CLOUDFLARE_LOG_LIMIT", "10")
    monkeypatch.setattr("httpx.AsyncClient", DummyClient)

    events = asyncio.run(fetch_cloudflare_events())
    assert len(events) == 1
    evt = events[0]
    assert evt.source_id == "cloudflare:zone"
    assert evt.log_level == "INFO"
    assert "ip" in evt.extras
    assert DummyClient.last_endpoint.startswith("/zones/zone/logs")


def test_pull_cloudflare_events(monkeypatch):
    monkeypatch.setenv("HCAI_CLOUDFLARE_ENABLED", "true")
    monkeypatch.setenv("HCAI_CLOUDFLARE_API_TOKEN", "token")
    monkeypatch.setenv("HCAI_CLOUDFLARE_ACCOUNT_ID", "acct")
    monkeypatch.setenv("HCAI_CLOUDFLARE_ZONE_ID", "zone")
    monkeypatch.setattr("httpx.AsyncClient", DummyClient)
    events = pull_cloudflare_events()
    assert events
