from datetime import datetime
from pathlib import Path
import json
import sqlite3
from typing import List, Optional, Iterable

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


class PersistentEventStore(EventStore):
    """
    Event store that persists events to a JSONL file for reuse across restarts.
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.total_ingested: int = 0
        self.last_error: Optional[str] = None
        self.last_ingest_at: Optional[datetime] = None
        self._load()

    def _serialize(self, event: HCaiEvent) -> dict:
        data = event.__dict__.copy()
        ts = data.get("timestamp")
        if hasattr(ts, "isoformat"):
            data["timestamp"] = ts.isoformat()
        return data

    def _deserialize(self, data: dict) -> Optional[HCaiEvent]:
        try:
            ts = data.get("timestamp")
            if isinstance(ts, str):
                data["timestamp"] = datetime.fromisoformat(ts)
            return HCaiEvent(**data)
        except Exception:
            return None

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    evt = self._deserialize(obj)
                    if evt:
                        self._events.append(evt)
        except Exception:
            # If load fails, keep running with in-memory empty store.
            self._events = []

    def add_events(self, events: List[HCaiEvent]) -> None:
        super().add_events(events)
        self.total_ingested += len(events)
        if events:
            self.last_ingest_at = datetime.utcnow()
        try:
            with self._path.open("a", encoding="utf-8") as f:
                for e in events:
                    json.dump(self._serialize(e), f)
                    f.write("\n")
        except Exception:
            # Ignore persistence failures to avoid breaking ingestion.
            self.last_error = "Failed to append to JSONL"

    def stats(self) -> dict:
        return {
            "total_ingested": self.total_ingested,
            "stored_events": len(self._events),
            "last_ingest_at": self.last_ingest_at.isoformat() if self.last_ingest_at else None,
            "last_error": self.last_error,
            "path": str(self._path),
        }


class SQLiteEventStore(EventStore):
    """
    Event store backed by SQLite for better durability and filtering.
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self._path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                source_id TEXT,
                event_type TEXT,
                payload TEXT
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
        self.conn.commit()
        self._load_all()

    def _serialize(self, event: HCaiEvent) -> dict:
        data = event.__dict__.copy()
        ts = data.get("timestamp")
        if hasattr(ts, "isoformat"):
            data["timestamp"] = ts.isoformat()
        return data

    def _deserialize(self, data: dict) -> Optional[HCaiEvent]:
        try:
            ts = data.get("timestamp")
            if isinstance(ts, str):
                data["timestamp"] = datetime.fromisoformat(ts)
            return HCaiEvent(**data)
        except Exception:
            return None

    def _load_all(self) -> None:
        cur = self.conn.execute("SELECT payload FROM events ORDER BY id ASC")
        for row in cur.fetchall():
            try:
                obj = json.loads(row[0])
            except Exception:
                continue
            evt = self._deserialize(obj)
            if evt:
                self._events.append(evt)

    def add_events(self, events: List[HCaiEvent]) -> None:
        super().add_events(events)
        try:
            to_insert: Iterable[tuple[str, str, str, str]] = []
            for e in events:
                payload = self._serialize(e)
                ts = payload.get("timestamp")
                to_insert = list(to_insert) + [
                    (
                        ts or "",
                        e.source_id,
                        e.event_type,
                        json.dumps(payload),
                    )
                ]
            if to_insert:
                self.conn.executemany(
                    "INSERT INTO events(ts, source_id, event_type, payload) VALUES (?,?,?,?)", to_insert
                )
                self.conn.commit()
        except Exception:
            # swallow DB write issues; keep in-memory
            pass

    def all(self) -> List[HCaiEvent]:
        return list(self._events)

    def since(self, dt: datetime) -> List[HCaiEvent]:
        cutoff = dt.isoformat()
        cur = self.conn.execute("SELECT payload FROM events WHERE ts >= ? ORDER BY ts ASC", (cutoff,))
        out = []
        for row in cur.fetchall():
            try:
                obj = json.loads(row[0])
                evt = self._deserialize(obj)
                if evt:
                    out.append(evt)
            except Exception:
                continue
        return out

    def filter(self, *, source_id: Optional[str] = None, event_type: Optional[str] = None) -> List[HCaiEvent]:
        query = "SELECT payload FROM events"
        params: list[str] = []
        clauses = []
        if source_id is not None:
            clauses.append("source_id = ?")
            params.append(source_id)
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id ASC"
        cur = self.conn.execute(query, tuple(params))
        out = []
        for row in cur.fetchall():
            try:
                obj = json.loads(row[0])
                evt = self._deserialize(obj)
                if evt:
                    out.append(evt)
            except Exception:
                continue
        return out

    def stats(self) -> dict:
        cur = self.conn.execute("SELECT COUNT(*) FROM events")
        stored = cur.fetchone()[0]
        return {
            "backend": "sqlite",
            "path": str(self._path),
            "stored_events": stored,
            "in_memory": len(self._events),
        }
