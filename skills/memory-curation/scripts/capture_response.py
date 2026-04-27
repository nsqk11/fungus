#!/usr/bin/env python3.12
# @hook stop
# @priority 10
# @skill memory-curation
# @description Capture agent response summary as raw entry.

import json
import subprocess
from pathlib import Path

from _common import read_payload

MEMORY_PY = str(Path(__file__).parent / "memory.py")


def main() -> None:
    payload = read_payload()
    if not payload:
        return
    subprocess.run(
        ["python3.12", MEMORY_PY, "insert",
         "--hook", "stop",
         "--data", json.dumps(payload)],
        check=False,
    )


if __name__ == "__main__":
    main()
