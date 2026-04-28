#!/usr/bin/env python3.12
"""Audit — SQLite-backed tool call recorder and stats CLI.

Usage:
  audit.py add --tool <name> --success <0|1> [--error <text>]
  audit.py stats
  audit.py top [--limit N]
  audit.py failures [--last N]

Data model: see SKILL.md.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import NoReturn

SKILL_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)
DB_PATH = os.path.join(SKILL_ROOT, "data", "audit.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    tool      TEXT NOT NULL,
    success   INTEGER NOT NULL,
    error     TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_tool ON audit(tool);
CREATE INDEX IF NOT EXISTS idx_timestamp ON audit(timestamp);
"""


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def _parse_pairs(args: list[str], keys: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--") and args[i][2:] in keys:
            if i + 1 >= len(args):
                _die(f"{args[i]} requires a value")
            out[args[i][2:]] = args[i + 1]
            i += 2
        else:
            _die(f"Unknown option: {args[i]}")
    return out


def _die(msg: str) -> NoReturn:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


# ── Commands ────────────────────────────────────────────────


def cmd_add(args: list[str]) -> None:
    opts = _parse_pairs(args, {"tool", "success", "error"})
    tool = opts.get("tool") or _die("--tool required")
    success_raw = opts.get("success")
    if success_raw not in ("0", "1"):
        _die("--success must be 0 or 1")
    success = int(success_raw)
    error = opts.get("error", "")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO audit(timestamp, tool, success, error)"
            " VALUES(?, ?, ?, ?)",
            (ts, tool, success, error),
        )


def cmd_stats(args: list[str]) -> None:
    if args:
        _die("stats takes no arguments")
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        if total == 0:
            print("No records.")
            return
        failures = conn.execute(
            "SELECT COUNT(*) FROM audit WHERE success = 0"
        ).fetchone()[0]
        rate = failures / total * 100

        print(f"Total: {total}  Failures: {failures} ({rate:.1f}%)")
        print()
        print(f"{'Tool':<20} {'Calls':>6} {'Fails':>6} {'Fail%':>6}")
        print("-" * 40)
        rows = conn.execute(
            "SELECT tool,"
            " COUNT(*) AS calls,"
            " SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS fails"
            " FROM audit GROUP BY tool ORDER BY calls DESC"
        ).fetchall()
        for tool, calls, fails in rows:
            pct = fails / calls * 100 if calls else 0
            print(f"{tool:<20} {calls:>6} {fails:>6} {pct:>5.1f}%")


def cmd_top(args: list[str]) -> None:
    opts = _parse_pairs(args, {"limit"})
    try:
        limit = int(opts.get("limit", "10"))
    except ValueError:
        _die("--limit must be an integer")
    with _connect() as conn:
        rows = conn.execute(
            "SELECT tool, COUNT(*) AS calls"
            " FROM audit GROUP BY tool"
            " ORDER BY calls DESC LIMIT ?",
            (limit,),
        ).fetchall()
    if not rows:
        print("No records.")
        return
    print(f"{'Tool':<20} {'Calls':>6}")
    print("-" * 28)
    for tool, calls in rows:
        print(f"{tool:<20} {calls:>6}")


def cmd_failures(args: list[str]) -> None:
    opts = _parse_pairs(args, {"last"})
    try:
        last = int(opts.get("last", "10"))
    except ValueError:
        _die("--last must be an integer")
    with _connect() as conn:
        rows = conn.execute(
            "SELECT timestamp, tool, error FROM audit"
            " WHERE success = 0 ORDER BY id DESC LIMIT ?",
            (last,),
        ).fetchall()
    if not rows:
        print("No failures recorded.")
        return
    for ts, tool, error in rows:
        print(f"{ts}  {tool}")
        if error:
            # Indent multi-line errors for readability.
            for line in error.splitlines():
                print(f"    {line}")


_COMMANDS = {
    "add": cmd_add,
    "stats": cmd_stats,
    "top": cmd_top,
    "failures": cmd_failures,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        _die(f"Usage: audit.py <{'|'.join(_COMMANDS)}> [options]")
    _COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
