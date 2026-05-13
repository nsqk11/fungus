#!/usr/bin/env python3.12
# @hook preToolUse
# @priority 20
# @description Emit audit-reminder on consecutive tool failures.

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory"))
from _db import FAILURE_THRESHOLD, SESSION_ID, get_events_conn


def main() -> None:
    conn = get_events_conn()
    # Get current tool (latest preToolUse for this session)
    cur = conn.execute(
        "SELECT tool_name FROM events WHERE session_id = ? AND hook = 'preToolUse' ORDER BY id DESC LIMIT 1",
        (SESSION_ID,),
    ).fetchone()
    if not cur:
        conn.close()
        return
    tool = cur[0]

    # Find current turn start
    turn_start = conn.execute(
        "SELECT id FROM events WHERE session_id = ? AND hook = 'userPromptSubmit' ORDER BY id DESC LIMIT 1",
        (SESSION_ID,),
    ).fetchone()
    if not turn_start:
        conn.close()
        return

    # Count consecutive failures
    rows = conn.execute(
        """SELECT tool_success FROM events
           WHERE session_id = ? AND hook = 'postToolUse' AND tool_name = ? AND id > ?
           ORDER BY id DESC""",
        (SESSION_ID, tool, turn_start[0]),
    ).fetchall()
    conn.close()

    streak = 0
    for (s,) in rows:
        if s == 0:
            streak += 1
        else:
            break

    if streak >= FAILURE_THRESHOLD:
        msg = (
            "<audit-reminder>\n"
            f'The tool "{tool}" has failed {streak} consecutive times in '
            "this turn. Consider a different approach.\n"
            "</audit-reminder>"
        )
        display = os.environ.get("AGENT_DISPLAY_OUT")
        if display:
            with open(display, "w") as f:
                f.write(f"\033[33m[audit]\033[0m ⚠ {tool} failed {streak}x consecutively\n")
        out = os.environ.get("AGENT_CONTEXT_OUT")
        if out:
            with open(out, "w") as f:
                f.write(msg)
        else:
            sys.stdout.write(msg + "\n")


if __name__ == "__main__":
    main()
