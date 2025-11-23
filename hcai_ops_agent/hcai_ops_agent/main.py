"""
Main agent loop using asyncio.
"""
from __future__ import annotations

import asyncio
import logging

from hcai_ops.data.schemas import HCaiEvent
from .config import load_config, AgentConfig
from .heartbeat import build_heartbeat
from .logs import collect_logs
from .metrics import build_metric_events
from .sender import flush_queue, send_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def _send_many(config: AgentConfig, events: list[HCaiEvent]) -> None:
    for evt in events:
        await send_event(config, evt)


async def run_loop(config: AgentConfig) -> None:
    intervals = config.send_intervals

    async def heartbeat_task():
        while True:
            hb = build_heartbeat(config)
            await send_event(config, hb)
            await asyncio.sleep(intervals.get("heartbeat", 10))

    async def metrics_task():
        while True:
            metrics = build_metric_events(config)
            await _send_many(config, metrics)
            await asyncio.sleep(intervals.get("metrics", 15))

    async def logs_task():
        while True:
            logs = collect_logs(config)
            await _send_many(config, logs)
            await asyncio.sleep(intervals.get("logs", 20))

    async def flush_task():
        while True:
            await flush_queue(config)
            await asyncio.sleep(intervals.get("flush", 60))

    await asyncio.gather(
        heartbeat_task(),
        metrics_task(),
        logs_task(),
        flush_task(),
    )


def run():
    config = load_config()
    try:
        asyncio.run(run_loop(config))
    except KeyboardInterrupt:
        logger.info("Agent stopped")


if __name__ == "__main__":
    run()
