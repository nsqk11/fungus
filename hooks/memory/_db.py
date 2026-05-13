"""Shared DB helpers. Not a hook itself (underscore prefix).

Two databases:
- events.db: router writes raw hook events (append-only)
- memory.db: memory pipeline manages memories + meta
"""

import os
import sqlite3
import time
from pathlib import Path

FUNGUS_ROOT = Path(os.environ.get("FUNGUS_ROOT", Path(__file__).resolve().parent.parent))
DATA_DIR = FUNGUS_ROOT / "data"
EVENTS_DB = DATA_DIR / "events.db"
MEMORY_DB = DATA_DIR / "memory.db"
SESSION_ID = os.environ.get("KIRO_SESSION_ID", "default")

NOISE_TOOLS = frozenset({"fs_read", "grep", "glob"})
MIN_PROMPT_LEN = 5
FAILURE_THRESHOLD = 3
DISTILL_THRESHOLD = 200

_EVENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    hook TEXT NOT NULL,
    cwd TEXT,
    prompt TEXT,
    tool_name TEXT,
    tool_success INTEGER,
    tool_error TEXT,
    response TEXT
);
"""

_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY,
    summary TEXT NOT NULL,
    detail TEXT,
    tags TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    source_event_id INTEGER
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_events_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(EVENTS_DB), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_EVENTS_SCHEMA)
    return conn


def get_memory_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(MEMORY_DB), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_MEMORY_SCHEMA)
    return conn


def insert_event(hook: str, payload: dict) -> int:
    """Insert a raw hook event into events.db. Called by router."""
    eid = time.time_ns()
    conn = get_events_conn()
    conn.execute(
        "INSERT INTO events (id, session_id, hook, cwd, prompt, tool_name, tool_success, tool_error, response) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            eid,
            SESSION_ID,
            hook,
            payload.get("cwd"),
            payload.get("prompt"),
            payload.get("tool_name"),
            0 if payload.get("tool_response", {}).get("success") is False else (1 if "tool_response" in payload else None),
            str(payload.get("tool_response", {}).get("error", "")).strip() or None if payload.get("tool_response", {}).get("success") is False else None,
            payload.get("assistant_response"),
        ),
    )
    conn.commit()
    conn.close()
    return eid
