from hcai_ops.config import HCAIConfig


def test_config_defaults():
    cfg = HCAIConfig()
    assert cfg.storage_path == "storage"
    assert cfg.risk_threshold_high == 0.8
    assert cfg.risk_threshold_medium == 0.4


def test_config_overrides():
    cfg = HCAIConfig(
        {
            "storage_path": "custom",
            "risk_threshold_high": 0.9,
            "risk_threshold_medium": 0.5,
        }
    )
    assert cfg.storage_path == "custom"
    assert cfg.risk_threshold_high == 0.9
    assert cfg.risk_threshold_medium == 0.5
