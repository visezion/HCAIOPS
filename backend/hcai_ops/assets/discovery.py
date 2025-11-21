from typing import List
from ipaddress import ip_network

from hcai_ops.assets.asset_model import Asset


def discover_docker() -> List[Asset]:
    assets: List[Asset] = []
    try:
        import docker  # type: ignore

        client = docker.from_env()
        for cont in client.containers.list():
            assets.append(
                Asset(
                    id=cont.id,
                    name=cont.name,
                    type="container",
                    ip=None,
                    tags=["docker"],
                    metadata={"container_id": cont.id},
                )
            )
    except Exception:
        return []
    return assets


def discover_network(subnet: str) -> List[Asset]:
    assets: List[Asset] = []
    try:
        net = ip_network(subnet, strict=False)
    except Exception:
        return []
    # Passive discovery placeholder: generate assets without probing
    for idx, host in enumerate(net.hosts()):
        if idx >= 5:
            break
        assets.append(
            Asset(
                id=str(host),
                name=f"host-{host}",
                type="server",
                ip=str(host),
                tags=["discovered"],
            )
        )
    return assets


def discover_k8s() -> List[Asset]:
    assets: List[Asset] = []
    try:
        import kubernetes  # type: ignore
    except Exception:
        return []
    # Without actual cluster, return empty; real impl would list pods/nodes
    return assets
