#!/usr/bin/env python3
# @hook userPromptSubmit
# @priority 50
# @description Remind user to distill when fragments accumulate.
"""Inject a reminder when undistilled fragments exceed threshold."""

import json
import sqlite3
import sys
from pathlib import Path

_FUNGUS_DIR = Path(__file__).resolve().parent.parent
_DB = _FUNGUS_DIR / "data" / "memory.db"

FRAGMENT_THRESHOLD = 30
TASK_THRESHOLD = 5  # same task has this many fragments


def main() -> None:
    if not _DB.exists():
        return

    conn = sqlite3.connect(str(_DB), timeout=5)
    try:
        total = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
        top_task = conn.execute(
            "SELECT task_or_topic, COUNT(*) as c FROM fragments "
            "GROUP BY task_or_topic ORDER BY c DESC LIMIT 1"
        ).fetchone()
    except sqlite3.OperationalError:
        conn.close()
        return
    conn.close()

    reasons = []
    if total >= FRAGMENT_THRESHOLD:
        reasons.append(f"{total} fragments accumulated")
    if top_task and top_task[1] >= TASK_THRESHOLD:
        reasons.append(f"task '{top_task[0]}' has {top_task[1]} fragments (ready for skill?)")

    if not reasons:
        return

    reminder = {
        "type": "context",
        "context": (
            f"<distill-reminder>\n"
            f"Consider suggesting a distill session: {'; '.join(reasons)}.\n"
            f"</distill-reminder>"
        )
    }
    print(json.dumps(reminder))


if __name__ == "__main__":
    main()
