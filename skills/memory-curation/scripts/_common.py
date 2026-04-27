"""Shared utilities for memory-curation hook scripts.

Router skips files starting with underscore, so this module is
import-only (not dispatched as a hook).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = SKILL_ROOT / "data" / "memory.db"


def read_payload() -> dict:
    """Read and parse hook stdin JSON. Returns {} on failure."""
    if sys.stdin.isatty():
        return {}
    raw = sys.stdin.read()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def emit_reminder(body: str) -> None:
    """Print a memory-curation-reminder tag to stdout.

    Host agent includes stdout from hook scripts as context entries.
    """
    print(f"<memory-curation-reminder>\n{body}\n</memory-curation-reminder>")


def get_pending_entry() -> tuple[str, dict] | None:
    """Return (id, data_dict) of the latest pending entry, or None."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            "SELECT id, data FROM memory WHERE stage = 'pending'"
            " ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
    except Exception:
        return None
    if not row:
        return None
    try:
        return row[0], json.loads(row[1])
    except json.JSONDecodeError:
        return row[0], {}


def update_pending_data(entry_id: str, data: dict) -> None:
    """Write updated data JSON back to a pending entry."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "UPDATE memory SET data = ? WHERE id = ?",
        (json.dumps(data, ensure_ascii=False), entry_id),
    )
    conn.commit()
    conn.close()
