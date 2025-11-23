"""
HTTP sender with offline queue persistence.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path
from datetime import datetime
from typing import Optional

import httpx

from hcai_ops.data.schemas import HCaiEvent
from .config import AgentConfig

logger = logging.getLogger(__name__)

_TEST_CLIENT: Optional[httpx.AsyncClient] = None


def set_test_client(client: httpx.AsyncClient | None) -> None:
    global _TEST_CLIENT
    _TEST_CLIENT = client


def _get_queue_path(config: AgentConfig) -> Path:
    return Path(os.getenv("HCAI_AGENT_QUEUE_PATH", config.queue_path)).expanduser()


def _ensure_queue(config: AgentConfig) -> None:
    path = _get_queue_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL)"
        )
        conn.commit()
    finally:
        conn.close()


async def _post_event(config: AgentConfig, event: HCaiEvent) -> bool:
    payload = asdict(event)
    ts = payload.get("timestamp")
    if ts:
        try:
            payload["timestamp"] = ts.isoformat()
        except Exception:
            payload["timestamp"] = None
    headers = {"Authorization": f"Bearer {config.token}"}
    client = _TEST_CLIENT or httpx.AsyncClient()
    try:
        for attempt in range(3):
            try:
                resp = await client.post(
                    f"{config.api_url}/events/ingest",
                    json=payload,
                    timeout=10.0,
                    headers=headers,
                )
                if resp.status_code < 500:
                    return 200 <= resp.status_code < 300
            except Exception as exc:
                logger.warning("Send attempt %s failed: %s", attempt + 1, exc)
            await asyncio.sleep(1.0)
    finally:
        if not _TEST_CLIENT:
            await client.aclose()
    return False


async def send_event(config: AgentConfig, event: HCaiEvent) -> None:
    _ensure_queue(config)
    ok = await _post_event(config, event)
    if ok:
        return
    # enqueue
    path = _get_queue_path(config)
    conn = sqlite3.connect(path)
    try:
        conn.execute("INSERT INTO queue(payload) VALUES(?)", (json.dumps(asdict(event)),))
        conn.commit()
    finally:
        conn.close()


async def flush_queue(config: AgentConfig) -> None:
    _ensure_queue(config)
    path = _get_queue_path(config)
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT id, payload FROM queue ORDER BY id ASC").fetchall()
        for row_id, payload in rows:
            try:
                obj = json.loads(payload)
                ts = obj.get("timestamp")
                if isinstance(ts, str):
                    try:
                        obj["timestamp"] = datetime.fromisoformat(ts)
                    except Exception:
                        obj["timestamp"] = None
                evt = HCaiEvent(**obj)
            except Exception as exc:
                logger.error("Corrupt queued event: %s", exc)
                conn.execute("DELETE FROM queue WHERE id=?", (row_id,))
                conn.commit()
                continue
            ok = await _post_event(config, evt)
            if ok:
                conn.execute("DELETE FROM queue WHERE id=?", (row_id,))
                conn.commit()
            else:
                break
    finally:
        conn.close()
