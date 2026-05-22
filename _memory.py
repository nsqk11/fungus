#!/usr/bin/env python3
"""Memory store: SQLite persistence for extracted memories.

Provides save, export, and session-processing tracking.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(os.environ.get("FUNGUS_ROOT", Path(__file__).resolve().parent.parent.parent))
_PROP_DIR = Path(__file__).resolve().parent
_KIRO_HOME = Path.home() / ".kiro"
MEMORY_DB = _KIRO_HOME / ".memory.db"
_RULES_DIR = _KIRO_HOME / "prompts"
_KB_DIR = _KIRO_HOME / "knowledge-bases" / "fungus"

CATEGORIES = ("skill", "kb", "rule")

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS fragments (
    id TEXT PRIMARY KEY,
    extractor TEXT NOT NULL,
    task_or_topic TEXT,
    fragment_type TEXT,
    content TEXT NOT NULL,
    context TEXT,
    x_knowledge REAL DEFAULT 0.0,
    y_rule REAL DEFAULT 0.0,
    z_task REAL DEFAULT 0.0,
    session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS processed_sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    fragment_count INTEGER DEFAULT 0
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(MEMORY_DB), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
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


def finish_session(session_id: str, fragment_count: int) -> None:
    """Mark a session as finished."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE processed_sessions SET finished_at = ?, fragment_count = ? WHERE session_id = ?",
        (now, fragment_count, session_id),
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


def find_unprocessed() :
    """Find session IDs registered in DB but not yet finished."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT session_id FROM processed_sessions WHERE finished_at IS NULL"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


# --- Memory save/export ---------------------------------------------------


def save_fragments(entries, extractor: str, session_id: str = "") -> int:
    """Save extracted fragments to DB and re-export. Returns count saved."""
    conn = get_conn()
    count = 0
    for entry in entries:
        scores = entry.get("scores", {})
        conn.execute(
            "INSERT INTO fragments (id, extractor, task_or_topic, fragment_type, content, context,"
            " x_knowledge, y_rule, z_task, session_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()),
             extractor,
             entry.get("task") or entry.get("topic") or "",
             entry.get("fragment_type", ""),
             entry.get("content") or entry.get("rule") or entry.get("summary", ""),
             entry.get("context") or entry.get("rationale") or "",
             scores.get("x_knowledge", 0.0),
             scores.get("y_rule", 0.0),
             scores.get("z_task", 0.0),
             session_id),
        )
        count += 1
    if session_id:
        conn.execute(
            "UPDATE processed_sessions SET fragment_count = fragment_count + ? WHERE session_id = ?",
            (count, session_id),
        )
    conn.commit()
    conn.close()
    export()
    return count


def export() -> None:
    """Export fragments: y_rule>0 to rules.md, rest to KB directory."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT extractor, task_or_topic, fragment_type, content, context,"
        " x_knowledge, y_rule, z_task, created_at"
        " FROM fragments ORDER BY id"
    ).fetchall()
    conn.close()

    _RULES_DIR.mkdir(parents=True, exist_ok=True)
    _KB_DIR.mkdir(parents=True, exist_ok=True)

    rules = []
    kb_entries = []

    for extractor, topic, ftype, content, context, xk, yr, zt, created_at in rows:
        if yr > 0:
            # Goes to rules.md (always loaded by main agent)
            entry = f"- {content}"
            if context:
                entry += f" ({context})"
            rules.append(entry)
        else:
            # Goes to KB (searchable)
            md = f"## {topic}\n\n"
            if ftype:
                md += f"Type: {ftype} | "
            md += f"Scores: x={xk:.1f} z={zt:.1f}\n\n"
            md += f"{content}\n"
            if context:
                md += f"\n> {context}\n"
            kb_entries.append(md)

    # Write rules.md
    rules_path = _RULES_DIR / "rules.md"
    if rules:
        rules_path.write_text("# Rules\n\n" + "\n".join(rules) + "\n", encoding="utf-8")
    else:
        rules_path.unlink(missing_ok=True)

    # Write KB file
    kb_path = _KB_DIR / "fragments.md"
    if kb_entries:
        kb_path.write_text("# Fragments\n\n" + "\n".join(kb_entries), encoding="utf-8")
    else:
        kb_path.unlink(missing_ok=True)


# --- CLI entry point (for worker agent) -----------------------------------


if __name__ == "__main__":
    import json
    import sys

    usage = (
        "Usage:\n"
        "  _memory.py save <extractor> '<json_array>' [session_id]\n"
        "  _memory.py finish <session_id> [count]\n"
        "  _memory.py list-unprocessed\n"
        "  _memory.py list-existing"
    )

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "save" and len(sys.argv) >= 4:
        extractor = sys.argv[2]
        entries = json.loads(sys.argv[3])
        if not isinstance(entries, list):
            entries = [entries]
        sid = sys.argv[4] if len(sys.argv) >= 5 else ""
        count = save_fragments(entries, extractor, session_id=sid)
        print(f"Saved {count} fragments.")
    elif cmd == "finish" and len(sys.argv) >= 3:
        mc = int(sys.argv[3]) if len(sys.argv) >= 4 else 0
        finish_session(sys.argv[2], mc)
        print(f"Session {sys.argv[2]} marked finished.")
    elif cmd == "list-unprocessed":
        for sid in find_unprocessed():
            print(sid)
    elif cmd == "list-existing":
        conn = get_conn()
        rows = conn.execute(
            "SELECT extractor, task_or_topic, content FROM fragments ORDER BY id DESC LIMIT 50"
        ).fetchall()
        conn.close()
        for ext, topic, content in rows:
            print(f"[{ext}] {topic}: {content[:80]}")
        if not rows:
            print("(none)")
    else:
        print(usage)
        sys.exit(1)
