from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class HCaiEvent:
    """Dataclass representing a unified operational event used within HCAI OPS."""

    timestamp: datetime
    source_id: str
    event_type: str
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    log_message: Optional[str] = None
    log_level: Optional[str] = None
    incident_label: Optional[str] = None
    op_user_id: Optional[str] = None
    op_action_type: Optional[str] = None
    alert_id: Optional[str] = None
    recommended_action: Optional[str] = None
    applied_action: Optional[str] = None
    outcome_label: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)
