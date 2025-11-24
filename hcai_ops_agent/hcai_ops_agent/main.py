"""
Main agent loop using asyncio.
"""
from __future__ import annotations

import asyncio
import argparse
import logging
from pathlib import Path

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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the HCAI OPS agent.")
    parser.add_argument(
        "--api-url",
        dest="api_url",
        help="Backend API root, e.g. https://hcaiops.vicezion.com (defaults to config/env).",
    )
    parser.add_argument("--token", dest="token", help="Bearer token used for Authorization.")
    parser.add_argument("--agent-id", dest="agent_id", help="Explicit agent identifier to report with.")
    parser.add_argument(
        "--config-path",
        dest="config_path",
        help="Path to the agent config file (defaults to HCAI_AGENT_CONFIG_PATH or the OS default).",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        dest="no_save",
        help="Do not persist CLI overrides back to the config file.",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None):
    args = _parse_args(argv)
    cfg_path = Path(args.config_path).expanduser() if args.config_path else None
    config = load_config(cfg_path)

    if args.agent_id:
        config.agent_id = args.agent_id
    if args.api_url:
        config.api_url = args.api_url.rstrip("/")
    if args.token:
        config.token = args.token

    if not args.no_save and (args.agent_id or args.api_url or args.token or args.config_path):
        save_path = cfg_path or None
        config.save(save_path)

    logger.info("Agent %s reporting to %s", config.agent_id, config.api_url)
    try:
        asyncio.run(run_loop(config))
    except KeyboardInterrupt:
        logger.info("Agent stopped")


if __name__ == "__main__":
    run()
