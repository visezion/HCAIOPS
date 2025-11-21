from datetime import datetime
from typing import List, Optional

from hcai_ops.data.schemas import HCaiEvent


class EventStore:
    """
    In-memory store for HCaiEvent objects.
    """

    def __init__(self) -> None:
        self._events: List[HCaiEvent] = []

    def add_events(self, events: List[HCaiEvent]) -> None:
        """Append events to the store."""
        self._events.extend(events)

    def all(self) -> List[HCaiEvent]:
        """Return a copy of all events."""
        return list(self._events)

    def since(self, dt: datetime) -> List[HCaiEvent]:
        """Return events occurring at or after the provided datetime."""
        return [event for event in self._events if event.timestamp >= dt]

    def filter(self, *, source_id: Optional[str] = None, event_type: Optional[str] = None) -> List[HCaiEvent]:
        """Filter events by optional source_id and event_type."""
        events = self._events
        if source_id is not None:
            events = [e for e in events if e.source_id == source_id]
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        return list(events)
