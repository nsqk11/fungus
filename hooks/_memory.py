#!/usr/bin/env python3
"""Memory store: SQLite persistence for extracted memories.

Provides save, export, and session-processing tracking.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(os.environ.get("FUNGUS_ROOT", Path(__file__).resolve().parent.parent))
MEMORY_DB = _ROOT / ".memory.db"
_MEMORY_DIR = _ROOT / "memory"

CATEGORIES = (
    "semantic", "episodic", "autobiographical",
    "skill", "habit", "reflex", "metacognitive",
    "prospective", "emotional",
)

DECLARATIVE = ("semantic", "episodic", "autobiographical")
NON_DECLARATIVE = ("skill", "habit", "reflex", "metacognitive", "prospective", "emotional")

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY,
    summary TEXT NOT NULL,
    detail TEXT,
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
    return conn


# --- Session tracking -----------------------------------------------------


def claim_session(session_id: str) -> bool:
    """Try to claim a session for processing. Returns True if claimed."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO processed_sessions (session_id, started_at) VALUES (?, ?)",
        (session_id, now),
    )
    claimed = conn.execute("SELECT changes()").fetchone()[0] == 1
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
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM processed_sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return row is not None


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
            "INSERT INTO memories (summary, detail, tags, category, source_event_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (entry["summary"], entry.get("detail", ""), entry.get("tags", ""), cat, source_id),
        )
        count += 1
    conn.commit()
    conn.close()
    export()
    return count


def export() -> None:
    """Export all memories to category-split .md files for KB indexing."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT summary, detail, tags, category, created_at FROM memories ORDER BY id"
    ).fetchall()
    conn.close()

    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    declarative: dict[str, list[str]] = {c: [] for c in DECLARATIVE}
    non_declarative: dict[str, list[str]] = {c: [] for c in NON_DECLARATIVE}

    for summary, detail, tags, category, created_at in rows:
        cat = category or "semantic"
        entry_date = created_at[:10] if created_at else datetime.now().strftime("%Y-%m-%d")
        md = f"## {summary}\n\nDate: {entry_date} | Tags: {tags}\n"
        if detail:
            md += f"\n{detail}\n"
        if cat in declarative:
            declarative[cat].append(md)
        elif cat in non_declarative:
            non_declarative[cat].append(md)
        else:
            declarative["semantic"].append(md)

    for cat, entries in declarative.items():
        path = _MEMORY_DIR / f"memory-{cat}.md"
        if entries:
            path.write_text(
                f"# Fungus Memory — {cat.title()}\n\n" + "\n".join(entries),
                encoding="utf-8",
            )
        else:
            path.unlink(missing_ok=True)

    nd_sections = []
    for cat, entries in non_declarative.items():
        if entries:
            nd_sections.append(f"### {cat.title()}\n\n" + "\n".join(entries))
    nd_path = _MEMORY_DIR / "procedural.md"
    if nd_sections:
        nd_path.write_text(
            "# Fungus Memory — Non-declarative\n\n" + "\n".join(nd_sections),
            encoding="utf-8",
        )
    else:
        nd_path.unlink(missing_ok=True)


# --- CLI entry point (for worker agent) -----------------------------------


if __name__ == "__main__":
    import json
    import sys

    usage = "Usage: _memory.py save '<json_array>' [session_id]\n       _memory.py finish <session_id> <count>"

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "save" and len(sys.argv) >= 3:
        entries = json.loads(sys.argv[2])
        if not isinstance(entries, list):
            entries = [entries]
        session_id = sys.argv[3] if len(sys.argv) > 3 else ""
        count = save_memories(entries, 0)
        print(f"Saved {count} memories.")
    elif cmd == "finish" and len(sys.argv) >= 4:
        finish_session(sys.argv[2], int(sys.argv[3]))
        print(f"Session {sys.argv[2]} marked finished.")
    else:
        print(usage)
        sys.exit(1)
