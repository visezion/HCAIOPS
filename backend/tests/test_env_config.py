from hcai_ops.config.env import get_settings, Settings


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("HCAI_ENV", raising=False)
    monkeypatch.delenv("HCAI_LOG_DIR", raising=False)
    settings = get_settings()
    assert settings.env == "development"
    assert settings.log_dir == "data/logs"
    assert settings.storage_dir == "data/storage"


def test_settings_overrides(monkeypatch):
    monkeypatch.setenv("HCAI_ENV", "production")
    monkeypatch.setenv("HCAI_LOG_DIR", "/tmp/logs")
    monkeypatch.setenv("HCAI_STORAGE_DIR", "/tmp/storage")
    # clear cache
    from functools import lru_cache
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.env == "production"
    assert settings.log_dir == "/tmp/logs"
    assert settings.storage_dir == "/tmp/storage"
