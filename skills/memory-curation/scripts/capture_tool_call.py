#!/usr/bin/env python3.12
# @hook preToolUse
# @priority 10
# @skill memory-curation
# @description Capture non-trivial tool calls as raw entries.

import json
import subprocess
import sys
from pathlib import Path

from _common import read_payload

MEMORY_PY = str(Path(__file__).parent / "memory.py")
SKIP_TOOLS = frozenset({"fs_read", "fs_write", "grep", "glob",
                        "code", "todo_list"})


def main() -> None:
    payload = read_payload()
    tool = payload.get("tool_name", "")
    if tool in SKIP_TOOLS:
        return
    if "memory.py" in json.dumps(payload):
        return
    subprocess.run(
        ["python3.12", MEMORY_PY, "insert",
         "--hook", "preToolUse",
         "--data", json.dumps(payload)],
        check=False,
    )


if __name__ == "__main__":
    main()
