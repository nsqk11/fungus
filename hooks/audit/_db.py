"""Shared SQLite helpers for the audit pipeline.

The database lives at ``<fungus-root>/data/audit.db``. The turn state
file lives at ``<fungus-root>/data/audit/current-turn.txt``. Pending
records (written by ``record_pre.py``, consumed by ``record_post.py``)
live under ``data/audit/pending-*.json``.

This module is imported by the audit hooks and the human-facing
``query.py`` CLI. It is never imported by the agent directly.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# --- Layer-1 tuning -------------------------------------------------------

#: How many consecutive failures of the same tool in the same turn
#: before a reminder is injected. Tuned empirically: 2 is too twitchy,
#: 5 wastes steps.
FAILURE_THRESHOLD = 3

#: Maximum length of the compact ``tool_input`` summary stored in the
#: DB. 200 chars is enough for "command=git status --porcelain" or a
#: short path; longer values bloat the store without helping analysis.
INPUT_SUMMARY_MAX = 200

#: Keys in ``tool_input`` whose values are replaced with ``<redacted>``.
_REDACT_KEYS = re.compile(r"(token|password|secret|api[_-]?key)", re.I)

# --- Paths ---------------------------------------------------------------


def fungus_root() -> Path:
    """Locate the Fungus root (repo or install dir).

    Prefers the ``FUNGUS_ROOT`` environment variable set by ``router.py``.
    Falls back to walking up from this file.
    """
    env = os.environ.get("FUNGUS_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent.parent


def db_path() -> Path:
    override = os.environ.get("AUDIT_DB")
    if override:
        return Path(override)
    return fungus_root() / "data" / "audit.db"


def audit_dir() -> Path:
    override = os.environ.get("AUDIT_DIR")
    if override:
        return Path(override)
    return fungus_root() / "data" / "audit"


def current_turn_file() -> Path:
    return audit_dir() / "current-turn.txt"


def pending_dir() -> Path:
    return audit_dir()


# --- Schema --------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    turn_id         TEXT,
    tool            TEXT NOT NULL,
    success         INTEGER NOT NULL,
    error           TEXT DEFAULT '',
    duration_ms     INTEGER,
    input_summary   TEXT DEFAULT '',
    started_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_tool      ON audit(tool);
CREATE INDEX IF NOT EXISTS idx_audit_turn      ON audit(turn_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit(timestamp);
"""


def connect() -> sqlite3.Connection:
    """Return a connection with the schema ensured."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    return conn


# --- Turn state ----------------------------------------------------------


def now_iso() -> str:
    """UTC ISO-8601 with seconds resolution."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_turn_id() -> str:
    """Generate a fresh turn id. Timestamp-based; compact; sortable."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_turn_id(turn_id: str) -> None:
    d = audit_dir()
    d.mkdir(parents=True, exist_ok=True)
    current_turn_file().write_text(turn_id, encoding="utf-8")


def read_turn_id() -> str:
    """Return the current turn id or empty string if none recorded."""
    path = current_turn_file()
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


# --- Pending pre→post handoff -------------------------------------------


def pending_path(pid: int, seq: int) -> Path:
    return pending_dir() / f"pending-{pid}-{seq}.json"


def next_pending_seq() -> int:
    """Next counter within the current process for disambiguating calls."""
    d = pending_dir()
    d.mkdir(parents=True, exist_ok=True)
    counter = d / f"counter-{os.getpid()}.txt"
    try:
        value = int(counter.read_text()) + 1
    except (FileNotFoundError, ValueError):
        value = 1
    counter.write_text(str(value))
    return value


def save_pending(pid: int, seq: int, data: dict) -> None:
    path = pending_path(pid, seq)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def load_and_delete_pending(pid: int, seq: int) -> dict | None:
    path = pending_path(pid, seq)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = None
    try:
        path.unlink()
    except OSError:
        pass
    return data


# --- Summaries / sanitization -------------------------------------------


def summarize_input(tool_input: object) -> str:
    """Compact, length-limited, redacted summary of ``tool_input``.

    - Dicts: ``key=value`` pairs joined with ``,``. Paths reduced to
      basenames. Keys matching the redact pattern have values replaced
      with ``<redacted>``.
    - Non-dicts: ``str(tool_input)`` truncated.
    """
    if tool_input is None:
        return ""
    if isinstance(tool_input, dict):
        parts: list[str] = []
        for key, raw in tool_input.items():
            if not isinstance(key, str):
                continue
            if _REDACT_KEYS.search(key):
                parts.append(f"{key}=<redacted>")
                continue
            value = _summarize_value(raw, key)
            parts.append(f"{key}={value}")
        summary = ",".join(parts)
    else:
        summary = str(tool_input)
    if len(summary) > INPUT_SUMMARY_MAX:
        summary = summary[: INPUT_SUMMARY_MAX - 1] + "…"
    return summary


def _summarize_value(value: object, key: str) -> str:
    text = str(value)
    if key in {"path", "file", "filepath", "file_path", "source", "target"}:
        text = os.path.basename(text) or text
    if "\n" in text:
        text = text.split("\n", 1)[0]
    return text


# --- Write (postToolUse) ------------------------------------------------


def insert_record(
    *,
    turn_id: str,
    tool: str,
    success: bool,
    error: str,
    duration_ms: int | None,
    input_summary: str,
    started_at: str | None,
) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO audit(timestamp, turn_id, tool, success, error,"
            " duration_ms, input_summary, started_at)"
            " VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (
                now_iso(),
                turn_id or None,
                tool,
                1 if success else 0,
                error or "",
                duration_ms,
                input_summary or "",
                started_at,
            ),
        )


# --- Read (Layer-1 + query) ---------------------------------------------


def consecutive_failures(turn_id: str, tool: str) -> int:
    """How many consecutive failures ``tool`` has in the current turn.

    Counts the tail of the turn's log for ``tool``: the number of most
    recent rows with ``success = 0`` that appear before the first
    ``success = 1`` row (or the start of the turn).
    """
    if not turn_id:
        return 0
    with connect() as conn:
        rows = conn.execute(
            "SELECT success FROM audit"
            " WHERE turn_id = ? AND tool = ?"
            " ORDER BY id DESC",
            (turn_id, tool),
        ).fetchall()
    count = 0
    for (success,) in rows:
        if success == 0:
            count += 1
        else:
            break
    return count


def reminder_already_issued(turn_id: str, tool: str) -> bool:
    """Check whether a reminder for (turn, tool) has been emitted.

    Tracked via a sentinel file per (turn, tool) so we only remind once
    per streak per turn. The file is cleared when ``new_turn_id`` is
    written.
    """
    d = audit_dir()
    marker = d / f"reminded-{turn_id}-{_slug(tool)}.flag"
    return marker.exists()


def mark_reminder_issued(turn_id: str, tool: str) -> None:
    d = audit_dir()
    d.mkdir(parents=True, exist_ok=True)
    marker = d / f"reminded-{turn_id}-{_slug(tool)}.flag"
    try:
        marker.touch()
    except OSError:
        pass


def clear_reminder_markers() -> None:
    """Delete any stale per-turn reminder markers."""
    d = audit_dir()
    if not d.is_dir():
        return
    for p in d.glob("reminded-*.flag"):
        try:
            p.unlink()
        except OSError:
            pass


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)[:64]
