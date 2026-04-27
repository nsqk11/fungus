#!/usr/bin/env python3.12
# @hook userPromptSubmit
# @priority 10
# @skill memory-curation
# @description Capture non-trivial user prompts as raw entries.

import json
import subprocess
import sys
from pathlib import Path

from _common import read_payload

MEMORY_PY = str(Path(__file__).parent / "memory.py")
MIN_LEN = 5


def main() -> None:
    payload = read_payload()
    prompt = payload.get("prompt", "")
    if len(prompt) <= MIN_LEN:
        return
    subprocess.run(
        ["python3.12", MEMORY_PY, "insert",
         "--hook", "userPromptSubmit",
         "--data", json.dumps(payload)],
        check=False,
    )


if __name__ == "__main__":
    main()
