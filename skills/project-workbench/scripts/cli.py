#!/usr/bin/env python3.12
"""project-workbench — per-project lifecycle metadata CLI.

One JSON file per project lives under ``data/workbenches/<id>.json``.
Run ``python3.12 cli.py --help`` for full usage.

The script is meant to be executed directly; it is not a hook.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any

# Sibling imports from the scripts/ directory itself.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _schema  # noqa: E402
import _store  # noqa: E402


# --- helpers --------------------------------------------------------------


def _die(msg: str, code: int = 1) -> None:
    print(f"ERR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _resolve(wb_id: str) -> str:
    try:
        return _store.resolve_id(wb_id)
    except _store.StoreError as exc:
        _die(str(exc))


def _load(wb_id: str) -> dict[str, Any]:
    try:
        return _store.load(wb_id)
    except _store.StoreError as exc:
        _die(str(exc))


def _save(workbench: dict[str, Any]) -> None:
    try:
        _store.save(workbench)
    except _store.StoreError as exc:
        _die(str(exc))


def _today() -> str:
    return datetime.date.today().isoformat()


def _get_field(obj: Any, path: str) -> Any:
    """Walk ``obj`` following a dot-separated ``path``.

    Supports dict keys and integer list indices. Returns ``None`` if the
    path does not resolve (distinct from a JSON null, so callers that
    need to tell them apart should not use this helper).
    """
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if cur is None:
            return None
    return cur


def _dump_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


# --- commands -------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    try:
        _store.create(args.id, args.name, args.type or "")
    except _store.StoreError as exc:
        _die(str(exc))
    print(f"OK: created {args.id}")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    if args.field:
        value = _get_field(workbench, args.field)
        if value is None:
            _die(f"field {args.field!r} not found in {wb_id!r}")
        _dump_json(value)
    else:
        _dump_json(workbench)
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    entry: dict[str, Any] = {
        "date": args.date or _today(),
        "summary": args.summary,
    }
    if args.ref:
        entry["ref"] = args.ref
    workbench["changeLog"].append(entry)
    _save(workbench)
    print("OK: logged")
    return 0


def cmd_review_add(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    next_id = len(workbench["reviews"]) + 1
    entry = {
        "id": next_id,
        "location": args.location or "",
        "comment": args.comment,
        "by": args.by,
        "response": args.response or "",
        "done": False,
    }
    workbench["reviews"].append(entry)
    _save(workbench)
    print(f"OK: review #{next_id} added")
    return 0


def cmd_review_done(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    found = False
    for review in workbench["reviews"]:
        if review.get("id") == args.review_id:
            review["done"] = True
            if args.response is not None:
                review["response"] = args.response
            found = True
            break
    if not found:
        _die(f"review #{args.review_id} not found in {wb_id!r}")
    _save(workbench)
    print(f"OK: review #{args.review_id} done")
    return 0


def cmd_milestone_add(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    entry = {
        "name": args.name,
        "target": args.target or "",
        "done": False,
        "note": args.note or "",
    }
    workbench["milestones"].append(entry)
    _save(workbench)
    print(f"OK: milestone {args.name!r} added")
    return 0


def cmd_milestone_done(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    found = False
    for ms in workbench["milestones"]:
        if ms.get("name") == args.name:
            ms["done"] = True
            if args.note is not None:
                ms["note"] = args.note
            found = True
            break
    if not found:
        _die(f"milestone {args.name!r} not found in {wb_id!r}")
    _save(workbench)
    print(f"OK: milestone {args.name!r} done")
    return 0


def cmd_milestone_update(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    found = False
    for ms in workbench["milestones"]:
        if ms.get("name") == args.name:
            if args.target is not None:
                ms["target"] = args.target
            if args.note is not None:
                ms["note"] = args.note
            found = True
            break
    if not found:
        _die(f"milestone {args.name!r} not found in {wb_id!r}")
    _save(workbench)
    print(f"OK: milestone {args.name!r} updated")
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    workbench["notes"].append({"topic": args.topic, "content": args.content})
    _save(workbench)
    print("OK: note added")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    print(f"=== {workbench['id']} ({workbench['status']}) ===")
    pending_ms = [
        m for m in workbench["milestones"] if not m.get("done")
    ]
    print(f"Milestones pending: {len(pending_ms)}")
    for ms in pending_ms:
        target = f" ({ms['target']})" if ms.get("target") else ""
        note = f" — {ms['note']}" if ms.get("note") else ""
        print(f"  ⬜ {ms['name']}{target}{note}")

    open_reviews = [r for r in workbench["reviews"] if not r.get("done")]
    print(f"Review open: {len(open_reviews)}")
    for rv in open_reviews:
        loc = f"[{rv['location']}] " if rv.get("location") else ""
        comment = rv.get("comment", "")
        snippet = (comment[:57] + "…") if len(comment) > 60 else comment
        print(f"  #{rv['id']} {loc}{snippet}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    ids = _store.list_ids()
    rows: list[tuple[str, str, str, str]] = []
    for wb_id in ids:
        try:
            workbench = _store.load(wb_id)
        except _store.StoreError:
            continue
        status = workbench.get("status", "")
        if args.status and status != args.status:
            continue
        rows.append(
            (
                wb_id,
                workbench.get("type", ""),
                status,
                workbench.get("name", "")[:50],
            )
        )
    if not rows:
        print("No workbenches." if not args.status else f"No {args.status} workbenches.")
        return 0
    id_w = max(len(r[0]) for r in rows)
    type_w = max(4, max(len(r[1]) for r in rows))
    status_w = max(6, max(len(r[2]) for r in rows))
    for wb_id, type_, status, name in rows:
        print(f"{wb_id:<{id_w}}  {type_:<{type_w}}  {status:<{status_w}}  {name}")
    return 0


def cmd_remind(_args: argparse.Namespace) -> int:
    found = False
    for wb_id in _store.list_ids():
        try:
            workbench = _store.load(wb_id)
        except _store.StoreError:
            continue
        if workbench.get("status") != "active":
            continue
        pending_ms = [m for m in workbench["milestones"] if not m.get("done")]
        open_reviews = [r for r in workbench["reviews"] if not r.get("done")]
        if not pending_ms and not open_reviews:
            continue
        found = True
        print(f"[{wb_id}]")
        pending_ms.sort(key=lambda m: m.get("target") or "")
        for ms in pending_ms:
            target = f" ({ms['target']})" if ms.get("target") else ""
            note = f" — {ms['note']}" if ms.get("note") else ""
            print(f"  ⬜ {ms['name']}{target}{note}")
        if open_reviews:
            print(f"  📝 {len(open_reviews)} open review comment(s)")
    if not found:
        print("No pending items.")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    workbench["status"] = "archived"
    _save(workbench)
    print(f"OK: {wb_id} archived")
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    wb_id = _resolve(args.id)
    workbench = _load(wb_id)
    workbench["status"] = "done"
    _save(workbench)
    print(f"OK: {wb_id} done")
    return 0


# --- parser ---------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="project-workbench",
        description=(
            "Per-project lifecycle metadata: file paths, milestones,"
            " change log, reviews, and decision notes."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init", help="Create a new workbench")
    sp.add_argument("id")
    sp.add_argument("--name", required=True)
    sp.add_argument("--type", default="")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("query", help="Print workbench data")
    sp.add_argument("id")
    sp.add_argument(
        "--field",
        help=(
            "Dot-separated path to a sub-value "
            "(e.g. 'milestones', 'milestones.0.note')"
        ),
    )
    sp.set_defaults(func=cmd_query)

    sp = sub.add_parser("log", help="Append a change log entry")
    sp.add_argument("id")
    sp.add_argument("--summary", required=True)
    sp.add_argument("--date", help="YYYY-MM-DD (default: today)")
    sp.add_argument("--ref", help="Optional git sha, PR link, etc.")
    sp.set_defaults(func=cmd_log)

    sp = sub.add_parser("review", help="Manage review comments")
    sp_sub = sp.add_subparsers(dest="review_command", required=True)
    sp_add = sp_sub.add_parser("add", help="Add a review comment")
    sp_add.add_argument("id")
    sp_add.add_argument("--location", default="")
    sp_add.add_argument("--comment", required=True)
    sp_add.add_argument("--by", required=True)
    sp_add.add_argument("--response", default="")
    sp_add.set_defaults(func=cmd_review_add)
    sp_done = sp_sub.add_parser("done", help="Mark a review comment done")
    sp_done.add_argument("id")
    sp_done.add_argument("--review-id", type=int, required=True, dest="review_id")
    sp_done.add_argument("--response", default=None)
    sp_done.set_defaults(func=cmd_review_done)

    sp = sub.add_parser("milestone", help="Manage milestones")
    sp_sub = sp.add_subparsers(dest="milestone_command", required=True)
    sp_add = sp_sub.add_parser("add", help="Add a milestone")
    sp_add.add_argument("id")
    sp_add.add_argument("--name", required=True)
    sp_add.add_argument("--target", default="")
    sp_add.add_argument("--note", default="")
    sp_add.set_defaults(func=cmd_milestone_add)
    sp_done = sp_sub.add_parser("done", help="Mark a milestone done")
    sp_done.add_argument("id")
    sp_done.add_argument("--name", required=True)
    sp_done.add_argument("--note", default=None)
    sp_done.set_defaults(func=cmd_milestone_done)
    sp_upd = sp_sub.add_parser("update", help="Update milestone target/note")
    sp_upd.add_argument("id")
    sp_upd.add_argument("--name", required=True)
    sp_upd.add_argument("--target", default=None)
    sp_upd.add_argument("--note", default=None)
    sp_upd.set_defaults(func=cmd_milestone_update)

    sp = sub.add_parser("note", help="Add a decision note")
    sp.add_argument("id")
    sp.add_argument("--topic", required=True)
    sp.add_argument("--content", required=True)
    sp.set_defaults(func=cmd_note)

    sp = sub.add_parser("status", help="Show pending milestones and open reviews")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("list", help="List all workbenches")
    sp.add_argument("--status", choices=_schema.VALID_STATUSES)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser(
        "remind",
        help="Show pending milestones and open reviews across active workbenches",
    )
    sp.set_defaults(func=cmd_remind)

    sp = sub.add_parser("archive", help="Mark a workbench archived")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_archive)

    sp = sub.add_parser("done", help="Mark a workbench done")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_done)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
