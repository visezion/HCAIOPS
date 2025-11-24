import os
import os
import shutil
from pathlib import Path

from hcai_ops.analytics.store import EventStore, PersistentEventStore, SQLiteEventStore

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = Path(os.getenv("HCAI_STORAGE_DIR", "")) if os.getenv("HCAI_STORAGE_DIR") else (Path.home() / ".hcai_ops_storage")


def _sqlite_row_count(path: Path) -> int:
    if not path or not path.exists():
        return 0
    try:
        import sqlite3

        conn = sqlite3.connect(path)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
        has_table = cur.fetchone() is not None
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] if has_table else 0
        conn.close()
        return count
    except Exception:
        return 0


def _ensure_dir(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _choose_sqlite_path() -> Path:
    """
    Choose a durable SQLite path:
    1. If HCAI_STORAGE_DIR is set, use it (create if needed).
    2. Otherwise use ~/.hcai_ops_storage/events.db
    3. If repo storage files have more rows, migrate them into the primary.
    """
    primary = DEFAULT_DATA_DIR
    if primary.suffix != ".db":
        primary = primary / "events.db"
    _ensure_dir(primary)

    candidates = [
        primary,
        ROOT_DIR / "storage" / "events.db",
        ROOT_DIR / "backend" / "storage" / "events.db",
    ]
    # Pick the candidate with the most rows.
    row_counts = {p: _sqlite_row_count(p) for p in candidates}
    best_path = max(row_counts, key=row_counts.get)
    if best_path != primary and row_counts[best_path] > row_counts.get(primary, 0):
        try:
            shutil.copy2(best_path, primary)
        except Exception:
            # If copy fails, fall back to primary (may be empty).
            pass
    return primary


def _choose_jsonl_path() -> Path:
    primary = DEFAULT_DATA_DIR
    if primary.suffix != ".jsonl":
        primary = primary / "events.jsonl"
    return _ensure_dir(primary)


SQLITE_PATH = _ensure_dir(_choose_sqlite_path())
JSONL_PATH = _choose_jsonl_path()

# Prefer SQLite for durability and querying; fall back gracefully to JSONL or in-memory.
try:
    event_store = SQLiteEventStore(SQLITE_PATH)
except Exception:  # pragma: no cover
    try:
        event_store = PersistentEventStore(JSONL_PATH)
    except Exception:
        event_store = EventStore()

__all__ = [
    "event_store",
    "EventStore",
    "PersistentEventStore",
    "SQLiteEventStore",
    "SQLITE_PATH",
    "JSONL_PATH",
]
