#!/usr/bin/env python3.12
# @hook stop
# @priority 5
# @description Flag incomplete todo items at turn end for next-turn awareness.

"""At stop, check if the assistant_response mentions incomplete tasks
(from todo_list). Write a marker file so the next userPromptSubmit
can remind the agent."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "audit"))

import _db  # noqa: E402

_TODO_INCOMPLETE = re.compile(r"\[ \]\s+#?\d+", re.MULTILINE)


def main() -> None:
    if sys.stdin.isatty():
        return
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return

    response = payload.get("assistant_response", "")
    if not response:
        return

    # Check if there are incomplete todo items visible in the response
    matches = _TODO_INCOMPLETE.findall(response)
    if not matches:
        # Clean up any stale marker
        marker = _db.audit_dir() / "incomplete-todo.flag"
        if marker.exists():
            marker.unlink(missing_ok=True)
        return

    # Write marker with count
    d = _db.audit_dir()
    d.mkdir(parents=True, exist_ok=True)
    marker = d / "incomplete-todo.flag"
    marker.write_text(str(len(matches)), encoding="utf-8")


if __name__ == "__main__":
    main()
