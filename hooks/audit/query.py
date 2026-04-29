#!/usr/bin/env python3.12
"""Human-facing query CLI for the audit pipeline.

This CLI is **not** advertised to the agent. It is intended for
maintainers who want to inspect recorded tool usage, trace a specific
turn, or prune old data. The agent gets its signal through the
``<audit-reminder>`` tags emitted by ``record_pre.py``.

Commands::

    query.py stats
    query.py top [--limit N]
    query.py failures [--last N]
    query.py turn <turn_id>
    query.py recent [--turns N]
    query.py slow [--limit N] [--tool NAME]
    query.py pattern [--turns N]
    query.py prune --days N

Database path can be overridden with ``AUDIT_DB``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _db  # noqa: E402


# --- formatting helpers ---------------------------------------------------


def _format_pct(num: int, denom: int) -> str:
    if denom == 0:
        return "  -   "
    return f"{num / denom * 100:5.1f}%"


def _print_table(headers: list[str], widths: list[int], rows: list[tuple]) -> None:
    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print("  ".join("-" * w for w in widths))
    for row in rows:
        cells: list[str] = []
        for value, width in zip(row, widths):
            text = "" if value is None else str(value)
            if len(text) > width:
                text = text[: width - 1] + "…"
            cells.append(text.ljust(width))
        print("  ".join(cells))


# --- commands -------------------------------------------------------------


def cmd_stats(_args: argparse.Namespace) -> int:
    with _db.connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        if total == 0:
            print("No records.")
            return 0
        failures = conn.execute(
            "SELECT COUNT(*) FROM audit WHERE success = 0"
        ).fetchone()[0]
        print(
            f"Total: {total}  Failures: {failures} "
            f"({_format_pct(failures, total).strip()})"
        )
        print()
        rows = conn.execute(
            "SELECT tool,"
            " COUNT(*) AS calls,"
            " SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS fails,"
            " ROUND(AVG(duration_ms)) AS avg_ms"
            " FROM audit GROUP BY tool ORDER BY calls DESC"
        ).fetchall()
    _print_table(
        ["TOOL", "CALLS", "FAILS", "FAIL%", "AVG_MS"],
        [22, 8, 6, 7, 8],
        [
            (tool, calls, fails, _format_pct(fails or 0, calls), int(avg_ms) if avg_ms else None)
            for tool, calls, fails, avg_ms in rows
        ],
    )
    return 0


def cmd_top(args: argparse.Namespace) -> int:
    with _db.connect() as conn:
        rows = conn.execute(
            "SELECT tool, COUNT(*) AS calls FROM audit"
            " GROUP BY tool ORDER BY calls DESC LIMIT ?",
            (args.limit,),
        ).fetchall()
    if not rows:
        print("No records.")
        return 0
    _print_table(["TOOL", "CALLS"], [22, 8], rows)
    return 0


def cmd_failures(args: argparse.Namespace) -> int:
    with _db.connect() as conn:
        rows = conn.execute(
            "SELECT id, timestamp, tool, turn_id, error, input_summary"
            " FROM audit WHERE success = 0 ORDER BY id DESC LIMIT ?",
            (args.last,),
        ).fetchall()
    if not rows:
        print("No failures recorded.")
        return 0
    for row_id, ts, tool, turn_id, error, summary in rows:
        print(f"[{row_id}] {ts}  turn={turn_id or '-'}  tool={tool}")
        if summary:
            print(f"    input: {summary}")
        if error:
            for line in error.splitlines():
                print(f"    {line}")
        print()
    return 0


def cmd_turn(args: argparse.Namespace) -> int:
    with _db.connect() as conn:
        rows = conn.execute(
            "SELECT id, timestamp, tool, success, duration_ms, input_summary, error"
            " FROM audit WHERE turn_id = ? ORDER BY id",
            (args.turn_id,),
        ).fetchall()
    if not rows:
        print(f"No records for turn {args.turn_id!r}.")
        return 0
    print(f"turn {args.turn_id}: {len(rows)} tool call(s)")
    print()
    _print_table(
        ["ID", "TIME", "TOOL", "OK?", "MS", "INPUT"],
        [6, 20, 18, 4, 6, 40],
        [
            (
                row_id,
                ts,
                tool,
                "✓" if success else "✗",
                duration_ms if duration_ms is not None else "",
                summary,
            )
            for row_id, ts, tool, success, duration_ms, summary, _err in rows
        ],
    )
    failed = [r for r in rows if r[3] == 0]
    if failed:
        print()
        print(f"{len(failed)} failure(s):")
        for row_id, _ts, tool, _succ, _ms, _summary, error in failed:
            print(f"  [{row_id}] {tool}: {error.splitlines()[0] if error else '(no error message)'}")
    return 0


def cmd_recent(args: argparse.Namespace) -> int:
    with _db.connect() as conn:
        rows = conn.execute(
            "SELECT turn_id, MIN(timestamp) AS started, MAX(timestamp) AS ended,"
            " COUNT(*) AS calls,"
            " SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS fails"
            " FROM audit"
            " WHERE turn_id IS NOT NULL"
            " GROUP BY turn_id"
            " ORDER BY started DESC LIMIT ?",
            (args.turns,),
        ).fetchall()
    if not rows:
        print("No turns recorded.")
        return 0
    _print_table(
        ["TURN", "STARTED", "ENDED", "CALLS", "FAILS"],
        [20, 20, 20, 6, 6],
        rows,
    )
    return 0


def cmd_slow(args: argparse.Namespace) -> int:
    sql = (
        "SELECT id, timestamp, tool, duration_ms, input_summary"
        " FROM audit WHERE duration_ms IS NOT NULL"
    )
    params: list = []
    if args.tool:
        sql += " AND tool = ?"
        params.append(args.tool)
    sql += " ORDER BY duration_ms DESC LIMIT ?"
    params.append(args.limit)
    with _db.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    if not rows:
        print("No records with duration.")
        return 0
    _print_table(
        ["ID", "TIME", "TOOL", "MS", "INPUT"],
        [6, 20, 18, 8, 40],
        rows,
    )
    return 0


def cmd_pattern(args: argparse.Namespace) -> int:
    with _db.connect() as conn:
        # Limit to the last N turns for relevance
        recent_turns = conn.execute(
            "SELECT DISTINCT turn_id FROM audit"
            " WHERE turn_id IS NOT NULL"
            " ORDER BY id DESC LIMIT ?",
            (args.turns,),
        ).fetchall()
        turn_ids = [t[0] for t in recent_turns]
        if not turn_ids:
            print("No turns with recorded activity.")
            return 0
        placeholders = ",".join("?" * len(turn_ids))
        # Tool pairs where B fails right after A (same turn, consecutive)
        rows = conn.execute(
            f"""
            SELECT a.tool AS before_tool, b.tool AS after_tool,
                   COUNT(*) AS occurrences
              FROM audit a
              JOIN audit b ON b.turn_id = a.turn_id
                          AND b.id = (
                              SELECT MIN(c.id) FROM audit c
                               WHERE c.turn_id = a.turn_id AND c.id > a.id
                          )
             WHERE a.turn_id IN ({placeholders})
               AND b.success = 0
             GROUP BY a.tool, b.tool
             HAVING occurrences >= 2
             ORDER BY occurrences DESC
             LIMIT 20
            """,
            turn_ids,
        ).fetchall()
    if not rows:
        print("No repeated failure-following-tool patterns in recent turns.")
        return 0
    print(f"Failure patterns across last {len(turn_ids)} turn(s):")
    _print_table(
        ["AFTER", "FAILED TOOL", "COUNT"],
        [20, 20, 6],
        rows,
    )
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    if args.days <= 0:
        print("--days must be a positive integer", file=sys.stderr)
        return 2
    cutoff_sql = (
        "SELECT COUNT(*) FROM audit WHERE timestamp <"
        " strftime('%Y-%m-%dT%H:%M:%SZ', 'now', ?)"
    )
    delete_sql = cutoff_sql.replace("SELECT COUNT(*)", "DELETE")
    days = f"-{args.days} days"
    with _db.connect() as conn:
        (to_delete,) = conn.execute(cutoff_sql, (days,)).fetchone()
        if to_delete == 0:
            print(f"Nothing older than {args.days} day(s).")
            return 0
        if not args.yes:
            print(f"Would delete {to_delete} row(s) older than {args.days} day(s).")
            print("Re-run with --yes to commit.")
            return 0
        conn.execute(delete_sql, (days,))
        conn.commit()
        print(f"Deleted {to_delete} row(s).")
        conn.execute("VACUUM")
    return 0


# --- parser ---------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="audit-query",
        description="Read-only inspection of the audit.db written by the audit hooks.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("stats", help="Totals and per-tool usage summary")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("top", help="Most-used tools")
    sp.add_argument("--limit", type=int, default=10)
    sp.set_defaults(func=cmd_top)

    sp = sub.add_parser("failures", help="Most recent failures")
    sp.add_argument("--last", type=int, default=10)
    sp.set_defaults(func=cmd_failures)

    sp = sub.add_parser("turn", help="Full timeline for one turn")
    sp.add_argument("turn_id")
    sp.set_defaults(func=cmd_turn)

    sp = sub.add_parser("recent", help="Most recent turns with counts")
    sp.add_argument("--turns", type=int, default=10)
    sp.set_defaults(func=cmd_recent)

    sp = sub.add_parser("slow", help="Slowest tool calls")
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("--tool", help="Restrict to one tool")
    sp.set_defaults(func=cmd_slow)

    sp = sub.add_parser("pattern", help="Recurring failure-after-tool patterns")
    sp.add_argument("--turns", type=int, default=50,
                    help="Consider the last N turns")
    sp.set_defaults(func=cmd_pattern)

    sp = sub.add_parser("prune", help="Delete rows older than N days")
    sp.add_argument("--days", type=int, required=True)
    sp.add_argument("--yes", action="store_true",
                    help="Actually delete (default is dry-run)")
    sp.set_defaults(func=cmd_prune)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
