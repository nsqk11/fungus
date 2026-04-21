#!/usr/bin/env python3.12
"""Memory storage backed by SQLite.

Drop-in CLI replacement for memory.sh.
Auto-imports data/memory.json on first run if present.

Usage::

    memory.py <add|delete|get|list|update|query|count|clean> [options]
"""
import json
import os
import sqlite3
import sys
from datetime import datetime
from datetime import timezone

_FUNGUS_HOME = os.environ.get(
    "FUNGUS_HOME",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
)
_DB_PATH = os.path.join(_FUNGUS_HOME, "data", "memory.db")
_JSON_PATH = os.path.join(_FUNGUS_HOME, "data", "memory.json")

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

_UPDATABLE_FIELDS = frozenset(
    {"stage", "hook", "data", "summary", "keywords", "refs", "category"}
)

_FIELD_COLUMNS = (
    "id", "timestamp", "stage", "hook", "data",
    "summary", "keywords", "refs", "category",
)


# ── Database ───────────────────────────────────────────────────


def _connect() -> sqlite3.Connection:
    """Open the database, create table, import JSON if first run."""
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    first_run = not os.path.exists(_DB_PATH)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(_SCHEMA)
    if first_run:
        _import_json(conn)
    return conn


def _import_json(conn: sqlite3.Connection) -> None:
    """Bulk-import memory.json into SQLite if the file exists."""
    if not os.path.exists(_JSON_PATH):
        return
    with open(_JSON_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    if not entries:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO memory"
        f"({', '.join(_FIELD_COLUMNS)})"
        f" VALUES({', '.join('?' for _ in _FIELD_COLUMNS)})",
        [_entry_to_row(e) for e in entries],
    )
    conn.commit()
    print(
        f"Imported {len(entries)} entries from memory.json",
        file=sys.stderr,
    )


def _entry_to_row(entry: dict) -> tuple:
    """Convert a JSON entry dict to a SQLite row tuple."""
    return (
        entry["id"],
        entry.get("timestamp", ""),
        entry.get("stage", ""),
        entry.get("hook", ""),
        json.dumps(entry.get("data", {}), ensure_ascii=False),
        entry.get("summary", ""),
        json.dumps(entry.get("keywords", []), ensure_ascii=False),
        json.dumps(entry.get("refs", []), ensure_ascii=False),
        entry.get("category", ""),
    )


def _row_to_dict(row: tuple) -> dict:
    """Convert a SQLite row tuple to the standard JSON dict."""
    return {
        "id": row[0],
        "timestamp": row[1],
        "stage": row[2],
        "hook": row[3],
        "data": json.loads(row[4]) if row[4] else {},
        "summary": row[5],
        "keywords": json.loads(row[6]) if row[6] else [],
        "refs": json.loads(row[7]) if row[7] else [],
        "category": row[8],
    }


def _next_id(conn: sqlite3.Connection) -> str:
    """Generate next sequential ID: YYYYMMDD + 3-digit counter."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    row = conn.execute(
        "SELECT id FROM memory WHERE id LIKE ? || '%'"
        " ORDER BY id DESC LIMIT 1",
        (today,),
    ).fetchone()
    seq = int(row[0][len(today):]) + 1 if row else 1
    return f"{today}{seq:03d}"


# ── Arg parsing ────────────────────────────────────────────────


def _parse_pairs(args: list[str], keys: set[str]) -> dict[str, str]:
    """Parse --key value pairs from args. Die on unknown keys."""
    result: dict[str, str] = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--") and args[i][2:] in keys:
            key = args[i][2:]
            if i + 1 >= len(args):
                _die(f"--{key} requires a value")
            result[key] = args[i + 1]
            i += 2
        else:
            _die(f"Unknown option: {args[i]}")
    return result


# ── Commands ───────────────────────────────────────────────────


def cmd_add(args: list[str]) -> None:
    """Add a new entry.

    Options: --stage (required), --hook, --data (JSON string).
    """
    opts = _parse_pairs(args, {"stage", "hook", "data"})
    stage = opts.get("stage")
    if not stage:
        _die("--stage required")
    hook = opts.get("hook", "")
    data = opts.get("data", "{}")
    with _connect() as conn:
        entry_id = _next_id(conn)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT OR IGNORE INTO memory"
            f"({', '.join(_FIELD_COLUMNS)})"
            f" VALUES({', '.join('?' for _ in _FIELD_COLUMNS)})",
            (entry_id, ts, stage, hook, data, "", "[]", "[]", ""),
        )
    print(f"OK: {entry_id}")


def cmd_delete(args: list[str]) -> None:
    """Delete an entry by id."""
    if not args:
        _die("id required")
    with _connect() as conn:
        cur = conn.execute("DELETE FROM memory WHERE id = ?", (args[0],))
    if cur.rowcount == 0:
        _die(f"{args[0]} not found")
    print(f"OK: deleted {args[0]}")


def cmd_get(args: list[str]) -> None:
    """Print a single entry as JSON."""
    if not args:
        _die("id required")
    with _connect() as conn:
        row = conn.execute(
            f"SELECT {', '.join(_FIELD_COLUMNS)}"
            " FROM memory WHERE id = ?",
            (args[0],),
        ).fetchone()
    if not row:
        _die(f"{args[0]} not found")
    print(json.dumps(_row_to_dict(row), indent=2, ensure_ascii=False))


def cmd_list(args: list[str]) -> None:
    """List entries as 'id stage hook' lines.

    Options: --stage, --hook (both optional filters).
    """
    opts = _parse_pairs(args, {"stage", "hook"})
    clauses: list[str] = []
    params: list[str] = []
    for key in ("stage", "hook"):
        if key in opts:
            clauses.append(f"{key} = ?")
            params.append(opts[key])
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with _connect() as conn:
        for row in conn.execute(
            f"SELECT id, stage, hook FROM memory{where}", params
        ):
            print(f"{row[0]} {row[1]} {row[2]}")


def cmd_update(args: list[str]) -> None:
    """Update a single field on an entry.

    Options: --id (required), --field (required), --value (required).
    """
    opts = _parse_pairs(args, {"id", "field", "value"})
    entry_id = opts.get("id")
    field = opts.get("field")
    value = opts.get("value", "")
    if not entry_id:
        _die("--id required")
    if not field:
        _die("--field required")
    if field not in _UPDATABLE_FIELDS:
        _die(f"Cannot update field: {field}")
    # Each field has its own UPDATE to avoid SQL injection via field name.
    sql_map = {f: f"UPDATE memory SET {f} = ? WHERE id = ?" for f in _UPDATABLE_FIELDS}
    with _connect() as conn:
        cur = conn.execute(sql_map[field], (value, entry_id))
    if cur.rowcount == 0:
        _die(f"{entry_id} not found")
    print(f"OK: {entry_id}.{field}")


def cmd_query(args: list[str]) -> None:
    """Run a read-only SQL query.

    Usage: memory.py query --sql "SELECT ... FROM memory WHERE ..."
    """
    opts = _parse_pairs(args, {"sql", "jq"})
    if "jq" in opts:
        _die("--jq no longer supported. Use --sql with a SQL query.")
    sql = opts.get("sql")
    if not sql:
        _die("--sql required")
    with _connect() as conn:
        for row in conn.execute(sql):
            print(row[0] if len(row) == 1 else "\t".join(str(c) for c in row))


def cmd_count(args: list[str]) -> None:
    """Count entries, optionally filtered by --stage."""
    opts = _parse_pairs(args, {"stage"})
    stage = opts.get("stage")
    with _connect() as conn:
        if stage:
            row = conn.execute(
                "SELECT COUNT(*) FROM memory WHERE stage = ?", (stage,)
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM memory").fetchone()
    print(row[0])


def cmd_clean(args: list[str]) -> None:
    """Remove skipped/fruiting entries, trim network to newest 50."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM memory WHERE stage IN ('skipped', 'fruiting')"
        )
        conn.execute(
            "DELETE FROM memory WHERE stage = 'network' AND id NOT IN"
            " (SELECT id FROM memory WHERE stage = 'network'"
            "  ORDER BY timestamp DESC LIMIT 50)"
        )
    print("OK: clean")


# ── Helpers ────────────────────────────────────────────────────


def _die(msg: str) -> None:
    """Print error to stderr and exit."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


# ── CLI dispatch ───────────────────────────────────────────────

_COMMANDS = {
    "add": cmd_add,
    "delete": cmd_delete,
    "get": cmd_get,
    "list": cmd_list,
    "update": cmd_update,
    "query": cmd_query,
    "count": cmd_count,
    "clean": cmd_clean,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        _die(f"Usage: memory.py <{'|'.join(_COMMANDS)}> [options]")
    _COMMANDS[sys.argv[1]](sys.argv[2:])
