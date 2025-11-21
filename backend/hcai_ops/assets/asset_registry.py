from typing import Dict, List, Optional

from hcai_ops.assets.asset_model import Asset


class AssetRegistry:
    def __init__(self, storage=None):
        self._assets: Dict[str, Asset] = {}
        self.storage = storage

    def register(self, asset: Asset) -> None:
        self._assets[asset.id] = asset
        self._persist_all()

    def get(self, asset_id: str) -> Optional[Asset]:
        return self._assets.get(asset_id)

    def list(self) -> List[Asset]:
        return list(self._assets.values())

    def find_by_type(self, asset_type: str) -> List[Asset]:
        return [a for a in self._assets.values() if a.type == asset_type]

    def find_by_tag(self, tag: str) -> List[Asset]:
        return [a for a in self._assets.values() if tag in a.tags]

    def update_status(self, asset_id: str, status: str) -> Optional[Asset]:
        asset = self._assets.get(asset_id)
        if not asset:
            return None
        asset.update_status(status)
        self._persist_all()
        return asset

    def remove(self, asset_id: str) -> None:
        if asset_id in self._assets:
            del self._assets[asset_id]
            self._persist_all()

    def _persist_all(self) -> None:
        if not self.storage:
            return
        try:
            for asset in self._assets.values():
                self.storage.append("assets", asset.dict())
        except Exception:
            pass
