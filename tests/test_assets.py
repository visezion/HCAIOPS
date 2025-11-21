from datetime import UTC, datetime
import asyncio

from hcai_ops.assets.asset_model import Asset
from hcai_ops.assets.asset_registry import AssetRegistry
from hcai_ops.assets.probes import run_asset_probe


def test_asset_model():
    a = Asset(id="1", name="srv1", type="server", status="unknown", ip="1.1.1.1")
    a.update_status("healthy")
    assert a.status == "healthy"


def test_registry_register_get():
    reg = AssetRegistry()
    a = Asset(id="1", name="srv1", type="server", status="unknown")
    reg.register(a)
    assert reg.get("1") == a
    assert reg.find_by_type("server") == [a]
    a.tags.append("prod")
    assert reg.find_by_tag("prod") == [a]
    reg.update_status("1", "warning")
    assert reg.get("1").status == "warning"
    reg.remove("1")
    assert reg.get("1") is None


def test_probe_merge_logic():
    class MockAdapter:
        async def probe(self, asset):
            return "warning", {"k": "v"}

    a = Asset(id="1", name="srv1", type="server", status="unknown")
    updated = asyncio.run(run_asset_probe(a, [MockAdapter()]))
    assert updated.status == "warning"
    assert updated.metadata["k"] == "v"

