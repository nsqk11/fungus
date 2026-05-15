#!/usr/bin/env python3
"""Event store: SQLite persistence for hook events.

Provides insert, read-marking, and cleanup for the events.db database.
"""

import os
import sqlite3
import time
from pathlib import Path

_ROOT = Path(os.environ.get("FUNGUS_ROOT", Path(__file__).resolve().parent.parent))
EVENTS_DB = _ROOT / ".events.db"

SESSION_ID = os.environ.get("KIRO_SESSION_ID", "default")

_RETENTION_NS = 86_400_000_000_000  # 1 day
_MAX_RETENTION_NS = 604_800_000_000_000  # 7 days

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    hook TEXT NOT NULL,
    cwd TEXT,
    prompt TEXT,
    tool_name TEXT,
    tool_success INTEGER,
    tool_error TEXT,
    response TEXT,
    read INTEGER NOT NULL DEFAULT 0
);
"""


def get_conn() -> sqlite3.Connection:
    """Open a connection to events.db, creating schema if needed."""
    conn = sqlite3.connect(str(EVENTS_DB), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn


def insert_event(hook: str, payload: dict) -> int:
    """Insert a raw hook event. Returns the event ID (nanosecond timestamp)."""
    event_id = time.time_ns()
    conn = get_conn()
    conn.execute(
        "INSERT INTO events"
        " (id, session_id, hook, cwd, prompt, tool_name, tool_success, tool_error, response)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event_id,
            SESSION_ID,
            hook,
            payload.get("cwd"),
            payload.get("prompt"),
            payload.get("tool_name"),
            _tool_success(payload),
            _tool_error(payload),
            payload.get("assistant_response"),
        ),
    )
    conn.commit()
    conn.close()
    return event_id


def mark_read(event_id: int) -> None:
    """Mark an event as read."""
    conn = get_conn()
    conn.execute("UPDATE events SET read = 1 WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()


def cleanup() -> None:
    """Delete stale events.

    - Older than 7 days: delete unconditionally.
    - Older than 1 day and read: delete.
    """
    now = time.time_ns()
    conn = get_conn()
    conn.execute(
        "DELETE FROM events WHERE id < ? OR (id < ? AND read = 1)",
        (now - _MAX_RETENTION_NS, now - _RETENTION_NS),
    )
    deleted = conn.execute("SELECT changes()").fetchone()[0]
    conn.commit()
    if deleted:
        conn.execute("VACUUM")
    conn.close()


def _tool_success(payload: dict) -> int | None:
    tr = payload.get("tool_response")
    if tr is None:
        return None
    return 0 if tr.get("success") is False else 1


def _tool_error(payload: dict) -> str | None:
    tr = payload.get("tool_response")
    if tr is None or tr.get("success") is not False:
        return None
    return str(tr.get("error", "")).strip() or None
