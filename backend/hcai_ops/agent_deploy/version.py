from __future__ import annotations

from pathlib import Path
from typing import Optional

VERSION_FILE = Path(__file__).resolve().parent / "agent_version.txt"


def get_current_agent_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "0.0.0"


def compare_versions(v1: str, v2: str) -> int:
    def _to_parts(v: str):
        return [int(x) for x in v.split(".")]

    p1 = _to_parts(v1)
    p2 = _to_parts(v2)
    for a, b in zip(p1, p2):
        if a < b:
            return -1
        if a > b:
            return 1
    if len(p1) != len(p2):
        return -1 if len(p1) < len(p2) else 1
    return 0


def increment_version(major: int, minor: int, patch: int) -> str:
    return f"{major}.{minor}.{patch}"
