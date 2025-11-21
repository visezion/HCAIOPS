import os
from typing import Any, Dict


class HCAIConfig:
    """
    Central configuration for the whole project.
    """

    def __init__(self, overrides: Dict[str, Any] = None):
        overrides = overrides or {}
        self.storage_path = overrides.get("storage_path", os.getenv("HCAI_STORAGE", "storage"))
        self.risk_threshold_high = overrides.get("risk_threshold_high", 0.8)
        self.risk_threshold_medium = overrides.get("risk_threshold_medium", 0.4)

    def as_dict(self):
        return {
            "storage_path": self.storage_path,
            "risk_threshold_high": self.risk_threshold_high,
            "risk_threshold_medium": self.risk_threshold_medium,
        }
