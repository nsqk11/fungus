#!/usr/bin/env python3
"""Memory store: SQLite persistence for extracted memories.

Provides save, drop-marking, and export for the memory.db database.
"""

import os
import sqlite3
from datetime import date
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
"""


def get_conn() -> sqlite3.Connection:
    """Open a connection to memory.db, creating schema if needed."""
    conn = sqlite3.connect(str(MEMORY_DB), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn


def save_memories(entries: list[dict], event_id: int) -> None:
    """Save extracted memories to DB and re-export files."""
    conn = get_conn()
    for entry in entries:
        cat = entry.get("category", "").lower()
        if cat not in CATEGORIES:
            continue
        conn.execute(
            "INSERT INTO memories (summary, detail, tags, category, source_event_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (entry["summary"], entry.get("detail", ""), entry.get("tags", ""), cat, event_id),
        )
    conn.commit()
    conn.close()
    export()


def mark_dropped(event_id: int) -> None:
    """Mark a turn as dropped (nothing worth extracting)."""
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, '1')",
        (f"dropped_{event_id}",),
    )
    conn.commit()
    conn.close()


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
        entry_date = created_at[:10] if created_at else date.today().isoformat()
        md = f"## {summary}\n\nDate: {entry_date} | Tags: {tags}\n"
        if detail:
            md += f"\n{detail}\n"
        if cat in declarative:
            declarative[cat].append(md)
        elif cat in non_declarative:
            non_declarative[cat].append(md)
        else:
            declarative["semantic"].append(md)

    # Write declarative KB files.
    for cat, entries in declarative.items():
        path = _MEMORY_DIR / f"memory-{cat}.md"
        if entries:
            path.write_text(
                f"# Fungus Memory — {cat.title()}\n\n" + "\n".join(entries),
                encoding="utf-8",
            )
        else:
            path.unlink(missing_ok=True)

    # Write non-declarative prompt file.
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
