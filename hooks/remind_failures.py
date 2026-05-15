#!/usr/bin/env python3
# @hook preToolUse
# @priority 10
# @description Warn the agent after consecutive tool failures.
"""Track tool failures and emit a warning after 3 consecutive failures."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _event import get_conn

_THRESHOLD = 3


def main() -> None:
    if sys.stdin.isatty():
        return
    payload = json.loads(sys.stdin.read())
    session_id = os.environ.get("KIRO_SESSION_ID", "default")

    conn = get_conn()
    recent = conn.execute(
        "SELECT tool_success FROM events"
        " WHERE session_id = ? AND hook = 'postToolUse'"
        " ORDER BY id DESC LIMIT ?",
        (session_id, _THRESHOLD),
    ).fetchall()
    conn.close()

    if len(recent) >= _THRESHOLD and all(r[0] == 0 for r in recent):
        print(
            "<failure-warning>\n"
            f"Last {_THRESHOLD} tool calls failed. "
            "Step back and try a different approach.\n"
            "</failure-warning>"
        )


if __name__ == "__main__":
    main()
