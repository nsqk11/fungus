#!/usr/bin/env python3.12
# @hook agentSpawn
# @priority 20
# @skill memory-curation
# @description Inject a reminder when there are raw entries awaiting
#   parsing.

import subprocess
from pathlib import Path

from _common import emit_reminder

MEMORY_PY = str(Path(__file__).parent / "memory.py")


def main() -> None:
    result = subprocess.run(
        ["python3.12", MEMORY_PY, "count", "--stage", "raw"],
        capture_output=True, text=True, check=False,
    )
    count = int(result.stdout.strip() or "0")
    if count == 0:
        return
    emit_reminder(
        f"{count} unparsed raw entries pending.\n"
        "Ask the user whether to parse now. If confirmed, read "
        "references/parse-protocol.md and follow its flow."
    )


if __name__ == "__main__":
    main()
