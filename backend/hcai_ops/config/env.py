import os
from functools import lru_cache


class Settings:
    def __init__(self):
        self.env: str = os.getenv("HCAI_ENV", "development")
        self.log_dir: str = os.getenv("HCAI_LOG_DIR", "data/logs")
        self.storage_dir: str = os.getenv("HCAI_STORAGE_DIR", "data/storage")
        self.api_host: str = os.getenv("HCAI_API_HOST", "0.0.0.0")
        self.api_port: int = int(os.getenv("HCAI_API_PORT", "8000"))


@lru_cache()
def get_settings() -> Settings:
    return Settings()
