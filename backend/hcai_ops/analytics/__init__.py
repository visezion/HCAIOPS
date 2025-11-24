from pathlib import Path

from hcai_ops.analytics.store import EventStore, PersistentEventStore, SQLiteEventStore

# Prefer SQLite for durability and querying; fall back gracefully.
try:
    event_store = SQLiteEventStore(Path("storage/events.db"))
except Exception:  # pragma: no cover
    try:
        event_store = PersistentEventStore(Path("storage/events.jsonl"))
    except Exception:
        event_store = EventStore()

__all__ = ["event_store", "EventStore", "PersistentEventStore", "SQLiteEventStore"]
