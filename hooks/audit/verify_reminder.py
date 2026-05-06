#!/usr/bin/env python3.12
# @hook postToolUse
# @priority 30
# @description Remind agent to verify after write operations.

"""After a successful write operation (file write, shell command that
modifies files), inject a verification reminder so the agent runs
tests or build before moving on."""

from __future__ import annotations

import json
import sys

_WRITE_TOOLS = {"fs_write", "write", "file_write"}
_SHELL_TOOLS = {"execute_bash", "shell"}


def _is_write_op(payload: dict) -> bool:
    tool = payload.get("tool_name", "")
    if tool in _WRITE_TOOLS:
        return True
    if tool in _SHELL_TOOLS:
        cmd = (payload.get("tool_input") or {}).get("command", "")
        # Heuristic: shell commands that create/modify files
        if any(k in cmd for k in ("tee ", "> ", ">> ", "sed -i", "patch ")):
            return True
    return False


def main() -> None:
    if sys.stdin.isatty():
        return
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return

    response = payload.get("tool_response") or {}
    if response.get("success") is False:
        return

    if _is_write_op(payload):
        print(
            "<verification-reminder>\n"
            "You just modified code/files. Run the relevant test or "
            "build command to verify correctness before proceeding.\n"
            "</verification-reminder>"
        )


if __name__ == "__main__":
    main()
