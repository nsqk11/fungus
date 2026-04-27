#!/usr/bin/env python3.12
"""Memory — CRUD for memory.db.

Usage:
  memory.py list --stage <stage> [--limit N]
  memory.py get <id>
  memory.py count --stage <stage>
  memory.py insert --hook <hook> --data <json>
  memory.py update --id <id> --field <field> --value <value>
  memory.py clean [--cap N]

Data model: see references/memory-schema.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"
STAGES = frozenset({"raw", "parsed", "longterm", "candidate", "dropped"})
LONGTERM_CAP = 500


def load() -> list[dict]:
    if not DB_PATH.exists():
        return []
    with DB_PATH.open() as f:
        return json.load(f)


def save(entries: list[dict]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DB_PATH.open("w") as f:
        json.dump(entries, f, indent=2)


def _next_id(entries: list[dict]) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    todays = [e["id"] for e in entries if e["id"].startswith(today)]
    seq = max((int(i[8:]) for i in todays), default=0) + 1
    return f"{today}{seq:03d}"


def cmd_list(args: argparse.Namespace) -> int:
    entries = [e for e in load() if e["stage"] == args.stage]
    if args.limit:
        entries = entries[: args.limit]
    json.dump(entries, sys.stdout, indent=2)
    print()
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    for e in load():
        if e["id"] == args.id:
            json.dump(e, sys.stdout, indent=2)
            print()
            return 0
    print(f"not found: {args.id}", file=sys.stderr)
    return 1


def cmd_count(args: argparse.Namespace) -> int:
    print(sum(1 for e in load() if e["stage"] == args.stage))
    return 0


def cmd_insert(args: argparse.Namespace) -> int:
    entries = load()
    entry = {
        "id": _next_id(entries),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": "raw",
        "hook": args.hook,
        "data": json.loads(args.data),
        "summary": "",
        "keywords": [],
        "refs": [],
        "category": "",
    }
    entries.append(entry)
    save(entries)
    print(entry["id"])
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    entries = load()
    for e in entries:
        if e["id"] != args.id:
            continue
        if args.field in ("keywords", "refs"):
            e[args.field] = json.loads(args.value)
        elif args.field == "stage" and args.value not in STAGES:
            print(f"invalid stage: {args.value}", file=sys.stderr)
            return 1
        else:
            e[args.field] = args.value
        save(entries)
        return 0
    print(f"not found: {args.id}", file=sys.stderr)
    return 1


def cmd_clean(args: argparse.Namespace) -> int:
    entries = load()
    kept = [e for e in entries if e["stage"] not in ("dropped", "candidate")]
    longterm = [e for e in kept if e["stage"] == "longterm"]
    if len(longterm) > args.cap:
        drop_ids = {e["id"] for e in longterm[: len(longterm) - args.cap]}
        kept = [e for e in kept if e["id"] not in drop_ids]
    save(kept)
    print(f"cleaned: kept {len(kept)}", file=sys.stderr)
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list"); sp.add_argument("--stage", required=True)
    sp.add_argument("--limit", type=int)
    sp.set_defaults(fn=cmd_list)

    sp = sub.add_parser("get"); sp.add_argument("id")
    sp.set_defaults(fn=cmd_get)

    sp = sub.add_parser("count"); sp.add_argument("--stage", required=True)
    sp.set_defaults(fn=cmd_count)

    sp = sub.add_parser("insert")
    sp.add_argument("--hook", required=True)
    sp.add_argument("--data", required=True)
    sp.set_defaults(fn=cmd_insert)

    sp = sub.add_parser("update")
    sp.add_argument("--id", required=True)
    sp.add_argument("--field", required=True)
    sp.add_argument("--value", required=True)
    sp.set_defaults(fn=cmd_update)

    sp = sub.add_parser("clean"); sp.add_argument("--cap", type=int, default=LONGTERM_CAP)
    sp.set_defaults(fn=cmd_clean)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
