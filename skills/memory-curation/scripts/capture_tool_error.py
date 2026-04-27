#!/usr/bin/env python3.12
# @hook postToolUse
# @priority 10
# @skill memory-curation
# @description Capture tool failures as raw entries. Successes are dropped.

import json
import subprocess
import sys
from pathlib import Path

from _common import read_payload

MEMORY_PY = str(Path(__file__).parent / "memory.py")


def main() -> None:
    payload = read_payload()
    if "memory.py" in json.dumps(payload):
        return
    if payload.get("tool_response", {}).get("success") is not False:
        return
    subprocess.run(
        ["python3.12", MEMORY_PY, "add", "--stage", "raw",
         "--hook", "postToolUse",
         "--data", json.dumps(payload)],
        check=False,
    )


if __name__ == "__main__":
    main()
