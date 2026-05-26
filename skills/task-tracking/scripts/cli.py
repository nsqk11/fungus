#!/usr/bin/env python3
"""task-tracking — structured logbook for tasks."""

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_KIRO_HOME = Path.home() / ".kiro"
_DB_PATH = Path(os.environ.get("TASK_TRACKING_DB", "")) or _KIRO_HOME / "data" / "task-tracking" / "tasks.db"

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS records (
    id         INTEGER PRIMARY KEY,
    task_id    TEXT NOT NULL,
    type       TEXT NOT NULL,
    content    TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_task ON records(task_id);
CREATE INDEX IF NOT EXISTS idx_type ON records(task_id, type);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _nano_id() -> int:
    return time.time_ns()


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.executescript(_SCHEMA)
    return conn


def _die(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _get_meta(conn: sqlite3.Connection, task_id: str) -> tuple | None:
    return conn.execute(
        "SELECT id, content FROM records WHERE task_id = ? AND type = 'meta' LIMIT 1",
        (task_id,),
    ).fetchone()


# --- write commands -------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    conn = _conn()
    if _get_meta(conn, args.task_id):
        _die(f"task '{args.task_id}' already exists")
    rid = _nano_id()
    conn.execute(
        "INSERT INTO records (id, task_id, type, content, updated_at) VALUES (?, ?, 'meta', ?, ?)",
        (rid, args.task_id, f"{args.name} [active]", _now()),
    )
    conn.commit()
    print(f"OK: created {args.task_id} (id: {rid})")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    conn = _conn()
    if not _get_meta(conn, args.task_id):
        _die(f"no task matching '{args.task_id}'")
    rid = _nano_id()
    conn.execute(
        "INSERT INTO records (id, task_id, type, content, updated_at) VALUES (?, ?, ?, ?, ?)",
        (rid, args.task_id, args.type, args.content, _now()),
    )
    conn.commit()
    print(f"OK: added (id: {rid})")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    conn = _conn()
    row = conn.execute("SELECT id FROM records WHERE id = ?", (args.id,)).fetchone()
    if not row:
        _die(f"record {args.id} not found")
    sets, vals = [], []
    if args.content is not None:
        sets.append("content = ?")
        vals.append(args.content)
    if args.type is not None:
        sets.append("type = ?")
        vals.append(args.type)
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(args.id)
    conn.execute(f"UPDATE records SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()
    print("OK: updated")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    conn = _conn()
    cur = conn.execute("DELETE FROM records WHERE id = ?", (args.id,))
    if cur.rowcount == 0:
        _die(f"record {args.id} not found")
    conn.commit()
    print("OK: deleted")
    return 0


def _set_status(task_id: str, status: str) -> int:
    conn = _conn()
    meta = _get_meta(conn, task_id)
    if not meta:
        _die(f"no task matching '{task_id}'")
    # Replace [status] in content
    content = meta[1]
    import re
    content = re.sub(r"\[.*?\]\s*$", "", content).strip()
    content = f"{content} [{status}]"
    conn.execute(
        "UPDATE records SET content = ?, updated_at = ? WHERE id = ?",
        (content, _now(), meta[0]),
    )
    conn.commit()
    print(f"OK: {task_id} → {status}")
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    return _set_status(args.task_id, "done")


def cmd_archive(args: argparse.Namespace) -> int:
    return _set_status(args.task_id, "archived")


# --- read commands --------------------------------------------------------


def cmd_get(args: argparse.Namespace) -> int:
    conn = _conn()
    sql = "SELECT id, type, content, updated_at FROM records WHERE task_id = ?"
    params: list = [args.task_id]
    if args.type:
        sql += " AND type = ?"
        params.append(args.type)
    if args.since:
        sql += " AND updated_at >= ?"
        params.append(args.since)
    sql += " ORDER BY id DESC"
    if args.last:
        sql += " LIMIT ?"
        params.append(args.last)
    rows = conn.execute(sql, params).fetchall()
    if not rows:
        print("(no records)")
        return 0
    for rid, rtype, content, updated in rows:
        short = (content[:60] + "...") if len(content) > 63 else content
        print(f"{rid}  {rtype:<12} {short}  ({updated})")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    conn = _conn()
    row = conn.execute(
        "SELECT id, task_id, type, content, updated_at FROM records WHERE id = ?",
        (args.id,),
    ).fetchone()
    if not row:
        _die(f"record {args.id} not found")
    rid, task_id, rtype, content, updated = row
    print(f"id:         {rid}")
    print(f"task:       {task_id}")
    print(f"type:       {rtype}")
    print(f"updated_at: {updated}")
    print(f"content:\n  {content}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    conn = _conn()
    rows = conn.execute(
        "SELECT task_id, content FROM records WHERE type = 'meta' ORDER BY task_id"
    ).fetchall()
    if not rows:
        print("(no tasks)")
        return 0
    if args.status:
        rows = [r for r in rows if f"[{args.status}]" in r[1]]
    for task_id, content in rows:
        print(f"{task_id:<16} {content}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    conn = _conn()
    meta = _get_meta(conn, args.task_id)
    if not meta:
        _die(f"no task matching '{args.task_id}'")
    print(f"=== {args.task_id}: {meta[1]} ===")

    milestones = conn.execute(
        "SELECT content FROM records WHERE task_id = ? AND type = 'milestone' ORDER BY id",
        (args.task_id,),
    ).fetchall()
    if milestones:
        print(f"Milestones: {len(milestones)}")
        for (c,) in milestones:
            print(f"  • {c}")

    blockers = conn.execute(
        "SELECT content FROM records WHERE task_id = ? AND type = 'blocker' ORDER BY id",
        (args.task_id,),
    ).fetchall()
    if blockers:
        print(f"Blockers: {len(blockers)}")
        for (c,) in blockers:
            print(f"  ⚠ {c}")

    recent = conn.execute(
        "SELECT type, content FROM records WHERE task_id = ? AND type != 'meta' ORDER BY id DESC LIMIT 5",
        (args.task_id,),
    ).fetchall()
    if recent:
        print("Recent:")
        for rtype, content in recent:
            short = (content[:60] + "...") if len(content) > 63 else content
            print(f"  [{rtype}] {short}")
    return 0


def cmd_remind(_args: argparse.Namespace) -> int:
    conn = _conn()
    tasks = conn.execute(
        "SELECT task_id, content FROM records WHERE type = 'meta' AND content LIKE '%[active]%'"
    ).fetchall()
    found = False
    for task_id, meta_content in tasks:
        milestones = conn.execute(
            "SELECT content FROM records WHERE task_id = ? AND type = 'milestone'",
            (task_id,),
        ).fetchall()
        blockers = conn.execute(
            "SELECT content FROM records WHERE task_id = ? AND type = 'blocker'",
            (task_id,),
        ).fetchall()
        if not milestones and not blockers:
            continue
        found = True
        print(f"[{task_id}]")
        for (c,) in milestones:
            print(f"  • {c}")
        for (c,) in blockers:
            print(f"  ⚠ {c}")
    if not found:
        print("No pending items.")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    conn = _conn()
    sql = "SELECT id, task_id, type, content FROM records WHERE content LIKE ?"
    params: list = [f"%{args.query}%"]
    if args.task_id:
        sql += " AND task_id = ?"
        params.append(args.task_id)
    if args.type:
        sql += " AND type = ?"
        params.append(args.type)
    sql += " ORDER BY id DESC LIMIT 20"
    rows = conn.execute(sql, params).fetchall()
    if not rows:
        print("(no results)")
        return 0
    for rid, task_id, rtype, content in rows:
        short = (content[:55] + "...") if len(content) > 58 else content
        print(f"[{task_id}] {rid}  {rtype:<12} {short}")
    return 0


# --- parser ---------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(prog="task-tracking")
    sub = p.add_subparsers(dest="command", required=True)

    # init
    s = sub.add_parser("init")
    s.add_argument("task_id")
    s.add_argument("--name", required=True)
    s.set_defaults(func=cmd_init)

    # add
    s = sub.add_parser("add")
    s.add_argument("task_id")
    s.add_argument("--type", required=True)
    s.add_argument("--content", required=True)
    s.set_defaults(func=cmd_add)

    # update
    s = sub.add_parser("update")
    s.add_argument("id", type=int)
    s.add_argument("--content")
    s.add_argument("--type")
    s.set_defaults(func=cmd_update)

    # delete
    s = sub.add_parser("delete")
    s.add_argument("id", type=int)
    s.set_defaults(func=cmd_delete)

    # done
    s = sub.add_parser("done")
    s.add_argument("task_id")
    s.set_defaults(func=cmd_done)

    # archive
    s = sub.add_parser("archive")
    s.add_argument("task_id")
    s.set_defaults(func=cmd_archive)

    # get
    s = sub.add_parser("get")
    s.add_argument("task_id")
    s.add_argument("--type")
    s.add_argument("--last", type=int)
    s.add_argument("--since")
    s.set_defaults(func=cmd_get)

    # show
    s = sub.add_parser("show")
    s.add_argument("id", type=int)
    s.set_defaults(func=cmd_show)

    # list
    s = sub.add_parser("list")
    s.add_argument("--status")
    s.set_defaults(func=cmd_list)

    # status
    s = sub.add_parser("status")
    s.add_argument("task_id")
    s.set_defaults(func=cmd_status)

    # remind
    s = sub.add_parser("remind")
    s.set_defaults(func=cmd_remind)

    # search
    s = sub.add_parser("search")
    s.add_argument("--query", required=True)
    s.add_argument("--task_id")
    s.add_argument("--type")
    s.set_defaults(func=cmd_search)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
