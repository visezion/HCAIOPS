"""
Configuration loader for the HCAI OPS agent.
"""
from __future__ import annotations

import json
import os
import platform
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any


def _default_config_path() -> Path:
    override = os.getenv("HCAI_AGENT_CONFIG_PATH")
    if override:
        return Path(override).expanduser()
    if platform.system().lower().startswith("win"):
        return Path("C:/ProgramData/HCAI_AGENT/config.json")
    return Path("~/.hcai_agent/config.json").expanduser()


@dataclass
class AgentConfig:
    agent_id: str
    api_url: str
    token: str
    send_intervals: Dict[str, int] = field(default_factory=dict)
    log_paths: Dict[str, Any] = field(default_factory=dict)
    queue_path: Path = field(default_factory=lambda: Path("~/.hcai_agent/queue.db").expanduser())

    @classmethod
    def load(cls, path: Path | None = None) -> "AgentConfig":
        path = path or _default_config_path()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            cfg = cls._default()
            cfg._apply_env_overrides()
            cfg.save(path)
            return cfg
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        cfg = cls(
            agent_id=data.get("agent_id") or str(uuid.uuid4()),
            api_url=data.get("api_url") or "https://hcaiops.vicezion.com",
            token=data.get("token") or "changeme",
            send_intervals=data.get(
                "send_intervals",
                {"heartbeat": 10, "metrics": 15, "logs": 20, "flush": 60},
            ),
            log_paths=data.get(
                "log_paths",
                {
                    "linux": ["/var/log/syslog", "/var/log/messages"],
                    "windows": ["Application", "System"],
                },
            ),
            queue_path=Path(data.get("queue_path") or Path("~/.hcai_agent/queue.db").expanduser()),
        )
        cfg._apply_env_overrides()
        return cfg

    @classmethod
    def _default(cls) -> "AgentConfig":
        return cls(
            agent_id=str(uuid.uuid4()),
            api_url="https://hcaiops.vicezion.com",
            token="changeme",
            send_intervals={"heartbeat": 10, "metrics": 15, "logs": 20, "flush": 60},
            log_paths={
                "linux": ["/var/log/syslog", "/var/log/messages"],
                "windows": ["Application", "System"],
            },
        )

    def _apply_env_overrides(self) -> None:
        env_agent_id = os.getenv("HCAI_AGENT_ID")
        env_api_url = os.getenv("HCAI_AGENT_API_URL")
        env_token = os.getenv("HCAI_AGENT_TOKEN")
        if env_agent_id:
            self.agent_id = env_agent_id
        if env_api_url:
            self.api_url = env_api_url
        if env_token:
            self.token = env_token

    def save(self, path: Path | None = None) -> None:
        path = path or _default_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "agent_id": self.agent_id,
                    "api_url": self.api_url,
                    "token": self.token,
                    "send_intervals": self.send_intervals,
                    "log_paths": self.log_paths,
                    "queue_path": str(self.queue_path),
                },
                fh,
                indent=2,
            )


def load_config(path: Path | None = None) -> AgentConfig:
    return AgentConfig.load(path)
