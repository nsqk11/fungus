#!/usr/bin/env python3.12
# @hook userPromptSubmit
# @priority 10
# @skill memory-curation
# @description Create a pending entry for this interaction.

import json
import subprocess
from pathlib import Path

from _common import read_payload

MEMORY_PY = str(Path(__file__).parent / "memory.py")
MIN_LEN = 5


def main() -> None:
    payload = read_payload()
    prompt = payload.get("prompt", "")
    if len(prompt) <= MIN_LEN:
        return
    data = {"prompt": prompt, "tools": [], "errors": [], "response": ""}
    subprocess.run(
        ["python3.12", MEMORY_PY, "add", "--stage", "pending",
         "--data", json.dumps(data, ensure_ascii=False)],
        check=False,
    )


if __name__ == "__main__":
    main()
