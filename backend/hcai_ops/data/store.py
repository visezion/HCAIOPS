from dataclasses import asdict
from datetime import datetime
from typing import List, Optional

from hcai_ops.data.schemas import HCaiEvent
from hcai_ops.storage.base import StorageBackend


class EventStore:
    """
    In-memory event store with optional persistent storage backend.
    """

    def __init__(self, storage: Optional[StorageBackend] = None) -> None:
        self._events: List[HCaiEvent] = []
        self.storage = storage

    def add_event(self, event: HCaiEvent) -> None:
        self._events.append(event)
        if self.storage:
            self.storage.append("events", asdict(event))

    def add_events(self, events: List[HCaiEvent]) -> None:
        for event in events:
            self.add_event(event)

    def get_all(self) -> List[HCaiEvent]:
        return list(self._events)

    def all(self) -> List[HCaiEvent]:
        return list(self._events)

    def since(self, dt: datetime) -> List[HCaiEvent]:
        return [event for event in self._events if event.timestamp >= dt]

    def filter(self, *, source_id: Optional[str] = None, event_type: Optional[str] = None) -> List[HCaiEvent]:
        events = self._events
        if source_id is not None:
            events = [e for e in events if e.source_id == source_id]
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        return list(events)
