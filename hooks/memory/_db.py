"""SQLite helper for memory hooks. Not a hook itself (underscore prefix)."""

import os
import sqlite3
from pathlib import Path

FUNGUS_ROOT = Path(os.environ.get("FUNGUS_ROOT", Path(__file__).resolve().parent.parent))
DATA_DIR = FUNGUS_ROOT / "data"
DB_PATH = DATA_DIR / "memory.db"
SESSION_ID = os.environ.get("KIRO_SESSION_ID", "default")

NOISE_TOOLS = frozenset({"fs_read", "grep", "glob"})
MIN_PROMPT_LEN = 5

_SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    prompt TEXT,
    tools TEXT DEFAULT '',
    response TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now'))
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY,
    summary TEXT NOT NULL,
    detail TEXT,
    tags TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
    source_turn_id INTEGER REFERENCES turns(id)
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn
