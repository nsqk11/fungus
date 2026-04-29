#!/usr/bin/env python3.12
# @hook preToolUse
# @priority 20
# @description Record tool-call start time and inject audit-reminder on consecutive failures.

"""Two responsibilities:

1. Save ``started_at`` + compact input summary so ``record_post.py`` can
   compute ``duration_ms`` and fill the DB row.
2. If the same tool has failed ``FAILURE_THRESHOLD`` times in a row
   within the current turn, emit an ``<audit-reminder>`` to stdout so
   the agent sees it in its next context.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _db  # noqa: E402


def _read_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read()
    except OSError:
        return {}
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _emit_reminder(tool: str, count: int) -> None:
    sys.stdout.write(
        "<audit-reminder>\n"
        f"The tool \"{tool}\" has failed {count} consecutive times in "
        "this turn. Consider a different approach, verify assumptions "
        "about the environment, or ask the user before retrying the "
        "same operation.\n"
        "</audit-reminder>\n"
    )


def main() -> None:
    payload = _read_payload()
    tool = payload.get("tool_name", "")
    if not tool:
        return

    turn_id = _db.read_turn_id()

    # --- (1) Stash start time + input summary for the post hook ---
    seq = _db.next_pending_seq()
    _db.save_pending(
        pid=os.getpid(),
        seq=seq,
        data={
            "turn_id": turn_id,
            "tool": tool,
            "started_at": _db.now_iso(),
            "input_summary": _db.summarize_input(payload.get("tool_input")),
        },
    )

    # --- (2) Layer-1 consecutive-failure reminder ---
    if not turn_id:
        return
    streak = _db.consecutive_failures(turn_id, tool)
    if streak >= _db.FAILURE_THRESHOLD and not _db.reminder_already_issued(
        turn_id, tool
    ):
        _emit_reminder(tool, streak)
        _db.mark_reminder_issued(turn_id, tool)


if __name__ == "__main__":
    main()
