import random
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd

from .schemas import HCaiEvent


def _to_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return pd.to_datetime(value)


def generate_synthetic_operator_actions(alerts: List[Dict]) -> List[HCaiEvent]:
    """Generate synthetic operator actions in response to alert dictionaries."""
    actions: List[HCaiEvent] = []
    action_choices = [
        ("acknowledge", "acknowledged alert"),
        ("scale", "scaled service"),
        ("restart_service", "restarted service"),
        ("noop", "observed only"),
    ]

    for alert in alerts:
        ts = _to_datetime(alert.get("timestamp"))
        severity = alert.get("severity", 0) or 0
        source_id = str(alert.get("source_id", "unknown"))
        alert_id = alert.get("alert_id")

        if isinstance(severity, (int, float)):
            if severity >= 0.8:
                ack_prob = 0.85
            elif severity >= 0.5:
                ack_prob = 0.6
            else:
                ack_prob = 0.3
        else:
            ack_prob = 0.4

        acknowledged = random.random() < ack_prob
        delay_minutes = random.uniform(0.1, 5.0 if acknowledged else 12.0)
        action_time = ts + timedelta(minutes=delay_minutes)
        op_user_id = f"op-{random.randint(100, 999)}"

        if acknowledged:
            action_type, applied_action = random.choices(
                population=action_choices,
                weights=[0.4, 0.25, 0.25, 0.1],
                k=1,
            )[0]
            resolve_prob = 0.7 if severity >= 0.7 else 0.5
            outcome = "resolved" if random.random() < resolve_prob else "mitigated"
        else:
            action_type = "ignored"
            applied_action = "none"
            outcome = "unresolved"

        actions.append(
            HCaiEvent(
                timestamp=action_time,
                source_id=source_id,
                event_type="operator_action",
                alert_id=alert_id,
                op_user_id=op_user_id,
                op_action_type=action_type,
                applied_action=applied_action,
                outcome_label=outcome,
                extras={"severity": severity, "acknowledged": acknowledged},
            )
        )

    return actions
