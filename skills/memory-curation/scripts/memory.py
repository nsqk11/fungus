#!/usr/bin/env python3.12
"""Memory — SQLite-backed CRUD for memory-curation.

Usage:
  memory.py add --stage <s> [--hook <h>] [--data <json>]
  memory.py get <id>
  memory.py list [--stage <s>] [--hook <h>]
  memory.py update --id <id> --field <f> --value <v>
  memory.py count [--stage <s>]
  memory.py clean

Data model: see references/memory-schema.md.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import NoReturn

SKILL_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)
DB_PATH = os.path.join(SKILL_ROOT, "data", "memory.db")

STAGES = frozenset({"raw", "parsed", "longterm", "candidate", "dropped"})
LONGTERM_CAP = 500

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory(
    id        TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    stage     TEXT NOT NULL,
    hook      TEXT DEFAULT '',
    data      TEXT DEFAULT '{}',
    summary   TEXT DEFAULT '',
    keywords  TEXT DEFAULT '[]',
    refs      TEXT DEFAULT '[]',
    category  TEXT DEFAULT ''
)
"""

_COLS = ("id", "timestamp", "stage", "hook", "data",
         "summary", "keywords", "refs", "category")
_UPDATABLE = frozenset({"stage", "hook", "data", "summary",
                        "keywords", "refs", "category"})


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def _row_to_dict(row: tuple) -> dict:
    return {
        "id": row[0], "timestamp": row[1], "stage": row[2], "hook": row[3],
        "data": json.loads(row[4]) if row[4] else {},
        "summary": row[5],
        "keywords": json.loads(row[6]) if row[6] else [],
        "refs": json.loads(row[7]) if row[7] else [],
        "category": row[8],
    }


def _next_id(conn: sqlite3.Connection) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    row = conn.execute(
        "SELECT id FROM memory WHERE id LIKE ? || '%' ORDER BY id DESC LIMIT 1",
        (today,),
    ).fetchone()
    seq = int(row[0][len(today):]) + 1 if row else 1
    return f"{today}{seq:03d}"


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
    opts = _parse_pairs(args, {"stage", "hook", "data"})
    stage = opts.get("stage") or _die("--stage required")
    if stage not in STAGES:
        _die(f"invalid stage: {stage}")
    hook = opts.get("hook", "")
    data = opts.get("data", "{}")
    with _connect() as conn:
        entry_id = _next_id(conn)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            f"INSERT OR IGNORE INTO memory({', '.join(_COLS)})"
            f" VALUES({', '.join('?' for _ in _COLS)})",
            (entry_id, ts, stage, hook, data, "", "[]", "[]", ""),
        )
    print(entry_id)


def cmd_get(args: list[str]) -> None:
    if not args:
        _die("id required")
    with _connect() as conn:
        row = conn.execute(
            f"SELECT {', '.join(_COLS)} FROM memory WHERE id = ?",
            (args[0],),
        ).fetchone()
    if not row:
        _die(f"{args[0]} not found")
    print(json.dumps(_row_to_dict(row), indent=2, ensure_ascii=False))


def cmd_list(args: list[str]) -> None:
    opts = _parse_pairs(args, {"stage", "hook"})
    clauses, params = [], []
    for k in ("stage", "hook"):
        if k in opts:
            clauses.append(f"{k} = ?")
            params.append(opts[k])
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with _connect() as conn:
        for row in conn.execute(
            f"SELECT {', '.join(_COLS)} FROM memory{where} ORDER BY id",
            params,
        ):
            print(json.dumps(_row_to_dict(row), ensure_ascii=False))


def cmd_update(args: list[str]) -> None:
    opts = _parse_pairs(args, {"id", "field", "value"})
    entry_id = opts.get("id") or _die("--id required")
    field = opts.get("field") or _die("--field required")
    value = opts.get("value", "")
    if field not in _UPDATABLE:
        _die(f"cannot update: {field}")
    if field == "stage" and value not in STAGES:
        _die(f"invalid stage: {value}")
    sql = {f: f"UPDATE memory SET {f} = ? WHERE id = ?" for f in _UPDATABLE}
    with _connect() as conn:
        cur = conn.execute(sql[field], (value, entry_id))
    if cur.rowcount == 0:
        _die(f"{entry_id} not found")
    print(f"OK: {entry_id}.{field}")


def cmd_count(args: list[str]) -> None:
    opts = _parse_pairs(args, {"stage"})
    with _connect() as conn:
        if "stage" in opts:
            row = conn.execute(
                "SELECT COUNT(*) FROM memory WHERE stage = ?",
                (opts["stage"],),
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM memory").fetchone()
    print(row[0])


def cmd_clean(args: list[str]) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM memory WHERE stage IN ('dropped', 'candidate')"
        )
        # Cap longterm at newest N
        row = conn.execute(
            "SELECT COUNT(*) FROM memory WHERE stage = 'longterm'"
        ).fetchone()
        if row[0] > LONGTERM_CAP:
            conn.execute(
                "DELETE FROM memory WHERE id IN ("
                "  SELECT id FROM memory WHERE stage = 'longterm'"
                "  ORDER BY timestamp ASC LIMIT ?"
                ")",
                (row[0] - LONGTERM_CAP,),
            )
    _connect().execute("VACUUM")
    print("OK: clean")


_COMMANDS = {
    "add": cmd_add, "get": cmd_get, "list": cmd_list,
    "update": cmd_update, "count": cmd_count, "clean": cmd_clean,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        _die(f"Usage: memory.py <{'|'.join(_COMMANDS)}> [options]")
    _COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
