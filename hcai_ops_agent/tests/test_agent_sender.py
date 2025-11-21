import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

from hcai_ops_agent.config import AgentConfig
from hcai_ops_agent.sender import flush_queue, send_event, set_test_client
from hcai_ops.data.schemas import HCaiEvent


@pytest.fixture
def config(tmp_path, monkeypatch):
    cfg = AgentConfig._default()
    cfg.queue_path = tmp_path / "queue.db"
    monkeypatch.setenv("HCAI_AGENT_QUEUE_PATH", str(cfg.queue_path))
    cfg.api_url = "http://testserver"
    return cfg


def test_send_event_offline_queue(config, monkeypatch):
    async def _run():
        set_test_client(None)
        evt = HCaiEvent(timestamp=None, source_id=config.agent_id, event_type="log", log_message="msg", extras={})
        await send_event(config, evt)
    asyncio.run(_run())
    assert config.queue_path.exists()


def test_flush_queue_with_mock_server(config):
    events_received = []
    app = FastAPI()

    @app.post("/events/ingest")
    async def ingest(payload=Body(...)):
        events_received.append(payload)
        return JSONResponse({"status": "ok"})

    async def _run():
        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        set_test_client(client)
        evt = HCaiEvent(timestamp=None, source_id=config.agent_id, event_type="log", log_message="msg", extras={})
        await send_event(config, evt)
        await flush_queue(config)
        await client.aclose()

    asyncio.run(_run())
    assert events_received
