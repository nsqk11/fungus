#!/usr/bin/env python3.12
# @hook postToolUse
# @priority 20
# @skill tool-audit
# @description Record every tool call result to audit.db.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

AUDIT_PY = str(Path(__file__).parent / "audit.py")


def main() -> None:
    if sys.stdin.isatty():
        return
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return

    tool = payload.get("tool_name", "")
    if not tool:
        return

    response = payload.get("tool_response", {})
    success = 0 if response.get("success") is False else 1
    error = ""
    if success == 0:
        error = str(response.get("error", ""))

    subprocess.run(
        ["python3.12", AUDIT_PY, "add",
         "--tool", tool,
         "--success", str(success),
         "--error", error],
        check=False,
    )


if __name__ == "__main__":
    main()
