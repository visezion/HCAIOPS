import asyncio
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

from hcai_ops_agent.config import AgentConfig
from hcai_ops_agent.main import run_loop
from hcai_ops_agent.sender import set_test_client


def test_agent_integration_short_run():
    received = []
    app = FastAPI()

    @app.post("/events/ingest")
    async def ingest(payload=Body(...)):
        received.append(payload)
        return JSONResponse({"ok": True})

    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    set_test_client(client)

    cfg = AgentConfig._default()
    cfg.api_url = "http://testserver"
    cfg.send_intervals = {"heartbeat": 0.1, "metrics": 0.2, "logs": 0.3, "flush": 0.2}

    async def runner():
        task = asyncio.create_task(run_loop(cfg))
        await asyncio.sleep(0.6)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(runner())
    asyncio.run(client.aclose())
    assert any(item.get("event_type") == "heartbeat" for item in received)
