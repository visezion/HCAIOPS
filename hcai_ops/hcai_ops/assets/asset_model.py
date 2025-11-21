from datetime import UTC, datetime
from typing import List, Optional, Dict

from pydantic import BaseModel, Field, field_validator


ALLOWED_TYPES = {"server", "switch", "router", "container", "cloud"}
ALLOWED_STATUS = {"healthy", "warning", "critical", "unknown"}


class Asset(BaseModel):
    id: str
    name: str
    type: str = Field(..., description="Asset type: server|switch|router|container|cloud")
    ip: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: str = Field(default="unknown")
    last_check: Optional[datetime] = None
    metadata: Dict[str, object] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ALLOWED_TYPES:
            raise ValueError("invalid asset type")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in ALLOWED_STATUS:
            raise ValueError("invalid status")
        return v

    def update_status(self, new_status: str) -> None:
        if new_status not in ALLOWED_STATUS:
            raise ValueError("invalid status")
        self.status = new_status
        self.updated_at = datetime.now(UTC)
