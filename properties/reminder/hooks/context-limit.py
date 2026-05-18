#!/usr/bin/env python3
# @hook postToolUse
# @priority 50
# @description Warn when session is getting long to avoid context compaction.
"""Detect long sessions and remind agent to be concise."""

import json
import os
from pathlib import Path

_SESSIONS_DIR = Path.home() / ".kiro" / "sessions" / "cli"
_LINE_THRESHOLD = 500


def main() -> None:
    session_id = os.environ.get("KIRO_SESSION_ID", "")
    if not session_id:
        return

    jsonl = _SESSIONS_DIR / f"{session_id}.jsonl"
    if not jsonl.exists():
        return

    line_count = sum(1 for _ in jsonl.open())
    if line_count > _LINE_THRESHOLD:
        print(
            "<context-warning>\n"
            "Session is getting long. Keep responses concise to avoid "
            "context compaction.\n"
            "</context-warning>"
        )


if __name__ == "__main__":
    main()
