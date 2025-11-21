from datetime import UTC, datetime
from typing import List

from hcai_ops.assets.asset_model import Asset
from hcai_ops.assets.adapters import AssetAdapter


async def run_asset_probe(asset: Asset, adapters: List[AssetAdapter]) -> Asset:
    statuses = []
    merged_meta = {}
    for adapter in adapters:
        try:
            status, meta = await adapter.probe(asset)
            statuses.append(status)
            merged_meta.update(meta or {})
        except Exception:
            statuses.append("warning")
    final_status = "healthy"
    if "critical" in statuses:
        final_status = "critical"
    elif "warning" in statuses:
        final_status = "warning"
    asset.status = final_status
    asset.last_check = datetime.now(UTC)
    asset.metadata.update(merged_meta)
    asset.updated_at = datetime.now(UTC)
    return asset
