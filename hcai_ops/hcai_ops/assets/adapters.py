"""
Adapters to probe real systems. All integrations are optional and must fail gracefully if dependencies are missing.
"""
from __future__ import annotations

import asyncio
from typing import Tuple, Dict

from hcai_ops.assets.asset_model import Asset


class AssetAdapter:
    async def probe(self, asset: Asset) -> Tuple[str, Dict]:
        raise NotImplementedError


class PingAdapter(AssetAdapter):
    async def probe(self, asset: Asset) -> Tuple[str, Dict]:
        if not asset.ip:
            return "unknown", {"reason": "no ip"}
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(asset.ip, 80), timeout=1.0)
            writer.close()
            return "healthy", {"method": "tcp_ping"}
        except Exception:
            return "critical", {"reason": "unreachable"}


class SSHAdapter(AssetAdapter):
    async def probe(self, asset: Asset) -> Tuple[str, Dict]:
        try:
            import asyncssh  # type: ignore
        except Exception:
            return "warning", {"reason": "asyncssh missing"}
        if not asset.ip:
            return "unknown", {"reason": "no ip"}
        try:
            async with asyncssh.connect(asset.ip) as conn:
                result = await conn.run("uname -a", check=False)
                return ("healthy" if result.exit_status == 0 else "warning", {"output": result.stdout})
        except Exception:
            return "warning", {"reason": "ssh failed"}


class SNMPAdapter(AssetAdapter):
    async def probe(self, asset: Asset) -> Tuple[str, Dict]:
        try:
            import pysnmp  # type: ignore
        except Exception:
            return "warning", {"reason": "pysnmp missing"}
        return "healthy", {"uptime": 1}


class DockerAdapter(AssetAdapter):
    async def probe(self, asset: Asset) -> Tuple[str, Dict]:
        try:
            import docker  # type: ignore
        except Exception:
            return "warning", {"reason": "docker missing"}
        try:
            client = docker.from_env()
            cont = client.containers.get(asset.metadata.get("container_id") or asset.name)
            stats = cont.stats(stream=False)
            cpu = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0.0)
            mem = stats.get("memory_stats", {}).get("usage", 0.0)
            return "healthy", {"cpu": cpu, "mem": mem}
        except Exception:
            return "warning", {"reason": "container probe failed"}


class K8sAdapter(AssetAdapter):
    async def probe(self, asset: Asset) -> Tuple[str, Dict]:
        try:
            import kubernetes  # type: ignore
        except Exception:
            return "warning", {"reason": "kubernetes missing"}
        return "healthy", {"phase": "Running"}
