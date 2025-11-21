"""
Cloudflare HTTP events integration.
"""
from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import List, Optional

import httpx

from hcai_ops.data.schemas import HCaiEvent


def _config() -> dict:
    return {
        "enabled": os.getenv("HCAI_CLOUDFLARE_ENABLED", "false").lower() == "true",
        "api_token": os.getenv("HCAI_CLOUDFLARE_API_TOKEN"),
        "account_id": os.getenv("HCAI_CLOUDFLARE_ACCOUNT_ID"),
        "zone_id": os.getenv("HCAI_CLOUDFLARE_ZONE_ID"),
        "limit": int(os.getenv("HCAI_CLOUDFLARE_LOG_LIMIT", "100")),
    }


async def fetch_cloudflare_events(limit: Optional[int] = None) -> List[HCaiEvent]:
    cfg = _config()
    limit = limit or cfg["limit"]
    token = cfg["api_token"]
    zone_id = cfg["zone_id"]
    if not (cfg["enabled"] and token and zone_id):
        return []

    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.cloudflare.com/client/v4"
    endpoint = f"/zones/{zone_id}/logs/received?limit={limit}"

    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=10.0) as client:
        resp = await client.get(endpoint)
        resp.raise_for_status()
        data = resp.json()

    records = data.get("result") or data.get("logs") or data.get("data") or []
    events: List[HCaiEvent] = []
    now = datetime.now(UTC)
    for rec in records:
        status = rec.get("EdgeResponseStatus") or rec.get("status") or 200
        method = rec.get("ClientRequestMethod") or rec.get("method") or ""
        uri = rec.get("ClientRequestURI") or rec.get("path") or ""
        ip = rec.get("ClientIP") or rec.get("ip")
        ua = rec.get("ClientRequestUserAgent") or rec.get("user_agent")
        level = "INFO"
        if status and int(status) >= 500:
            level = "ERROR"
        elif status and int(status) >= 400:
            level = "WARNING"
        msg = f"{method} {uri} status={status}"
        evt = HCaiEvent(
            timestamp=now,
            source_id=f"cloudflare:{zone_id}",
            event_type="log",
            log_level=level,
            log_message=msg,
            extras={
                "ip": ip,
                "country": rec.get("EdgeResponseCountry") or rec.get("country"),
                "uri": uri,
                "user_agent": ua,
                "raw": rec,
            },
        )
        events.append(evt)
    return events


def pull_cloudflare_events(limit: Optional[int] = None) -> List[HCaiEvent]:
    """Sync wrapper for async fetch."""
    return asyncio.run(fetch_cloudflare_events(limit))
