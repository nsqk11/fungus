#!/usr/bin/env python3
"""Memory store: SQLite persistence for extracted memories.

Provides save, export, and session-processing tracking.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(os.environ.get("FUNGUS_ROOT", Path(__file__).resolve().parent.parent.parent))
_PROP_DIR = Path(__file__).resolve().parent
MEMORY_DB = _PROP_DIR / "memory.db"
_MEMORY_DIR = _PROP_DIR / "data"

CATEGORIES = ("correction", "preference", "discovery", "decision")

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY,
    summary TEXT NOT NULL,
    detail TEXT,
    trigger TEXT,
    tags TEXT,
    category TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
    source_event_id INTEGER
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS processed_sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    memory_count INTEGER DEFAULT 0
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(MEMORY_DB), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    # Migration: add trigger column if missing
    cols = {r[1] for r in conn.execute("PRAGMA table_info(memories)").fetchall()}
    if "trigger" not in cols:
        conn.execute("ALTER TABLE memories ADD COLUMN trigger TEXT")
    return conn


# --- Session tracking -----------------------------------------------------


def register_session(session_id: str) -> None:
    """Register a session as known (not yet processed)."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO processed_sessions (session_id, started_at) VALUES (?, ?)",
        (session_id, now),
    )
    conn.commit()
    conn.close()


def claim_session(session_id: str) -> bool:
    """Try to claim a session for processing. Returns True if claimed."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    # Only claim sessions that are registered but not yet started processing
    cur = conn.execute(
        "UPDATE processed_sessions SET started_at = ? WHERE session_id = ? AND finished_at IS NULL",
        (now, session_id),
    )
    claimed = cur.rowcount == 1
    conn.commit()
    conn.close()
    return claimed


def finish_session(session_id: str, memory_count: int) -> None:
    """Mark a session as finished."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE processed_sessions SET finished_at = ?, memory_count = ? WHERE session_id = ?",
        (now, memory_count, session_id),
    )
    conn.commit()
    conn.close()


def is_processed(session_id: str) -> bool:
    """True if session has been fully processed (finished_at is set)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM processed_sessions WHERE session_id = ? AND finished_at IS NOT NULL",
        (session_id,),
    ).fetchone()
    conn.close()
    return row is not None


def find_unprocessed() -> list[str]:
    """Find session IDs registered in DB but not yet finished."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT session_id FROM processed_sessions WHERE finished_at IS NULL"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


# --- Memory save/export ---------------------------------------------------


def save_memories(entries: list[dict], source_id: int = 0) -> int:
    """Save extracted memories to DB and re-export files. Returns count saved."""
    conn = get_conn()
    count = 0
    for entry in entries:
        cat = entry.get("category", "").lower()
        if cat not in CATEGORIES:
            continue
        conn.execute(
            "INSERT INTO memories (summary, detail, trigger, tags, category, source_event_id)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (entry["summary"], entry.get("detail", ""), entry.get("trigger", ""),
             entry.get("tags", ""), cat, source_id),
        )
        count += 1
    conn.commit()
    conn.close()
    export()
    return count


def export() -> None:
    """Export memories to per-category .md files for KB indexing."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT summary, detail, tags, category, created_at FROM memories ORDER BY id"
    ).fetchall()
    conn.close()

    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    sections: dict[str, list[str]] = {c: [] for c in CATEGORIES}

    for summary, detail, tags, category, created_at in rows:
        cat = category if category in CATEGORIES else "discovery"
        entry_date = created_at[:10] if created_at else datetime.now().strftime("%Y-%m-%d")
        md = f"## {summary}\n\nDate: {entry_date} | Tags: {tags}\n"
        if detail:
            md += f"\n{detail}\n"
        sections[cat].append(md)

    for cat in CATEGORIES:
        out_path = _MEMORY_DIR / f"memory-{cat}.md"
        if sections[cat]:
            content = f"# {cat.title()}\n\n" + "\n".join(sections[cat])
            out_path.write_text(content, encoding="utf-8")
        else:
            out_path.unlink(missing_ok=True)

    # Clean up old single file
    (_MEMORY_DIR / "memories.md").unlink(missing_ok=True)


# --- CLI entry point (for worker agent) -----------------------------------


if __name__ == "__main__":
    import json
    import sys

    usage = (
        "Usage:\n"
        "  _memory.py save '<json_array>'\n"
        "  _memory.py finish <session_id> <count>\n"
        "  _memory.py list-unprocessed\n"
        "  _memory.py list-existing"
    )

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "save" and len(sys.argv) >= 3:
        entries = json.loads(sys.argv[2])
        if not isinstance(entries, list):
            entries = [entries]
        count = save_memories(entries, 0)
        print(f"Saved {count} memories.")
    elif cmd == "finish" and len(sys.argv) >= 4:
        finish_session(sys.argv[2], int(sys.argv[3]))
        print(f"Session {sys.argv[2]} marked finished.")
    elif cmd == "list-unprocessed":
        for sid in find_unprocessed():
            print(sid)
    elif cmd == "list-existing":
        conn = get_conn()
        rows = conn.execute("SELECT summary FROM memories ORDER BY id DESC LIMIT 50").fetchall()
        conn.close()
        for r in rows:
            print(f"- {r[0]}")
        if not rows:
            print("(none)")
    else:
        print(usage)
        sys.exit(1)
