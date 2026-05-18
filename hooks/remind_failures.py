#!/usr/bin/env python3
# @hook preToolUse
# @priority 10
# @description Warn the agent after consecutive tool failures.
"""Read current session .jsonl to detect consecutive tool failures."""

import json
import os
from pathlib import Path

_SESSIONS_DIR = Path.home() / ".kiro" / "sessions" / "cli"
_THRESHOLD = 3


def main() -> None:
    session_id = os.environ.get("KIRO_SESSION_ID", "")
    if not session_id:
        return

    jsonl = _SESSIONS_DIR / f"{session_id}.jsonl"
    if not jsonl.exists():
        return

    # Read last N ToolResults lines from the end
    tool_results = []
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                if obj.get("kind") == "ToolResults":
                    tool_results.append(obj)
            except json.JSONDecodeError:
                continue

    # Check last _THRESHOLD tool results for failures
    recent = tool_results[-_THRESHOLD:]
    if len(recent) < _THRESHOLD:
        return

    all_failed = True
    for tr in recent:
        results = tr.get("data", {}).get("results", {})
        for tool_id, result in results.items():
            status = result.get("tool", {}).get("status", "success")
            if status == "success":
                all_failed = False
                break
        if not all_failed:
            break

    if all_failed:
        print(
            "<failure-warning>\n"
            f"Last {_THRESHOLD} tool calls failed. "
            "Step back and try a different approach.\n"
            "</failure-warning>"
        )


if __name__ == "__main__":
    main()
