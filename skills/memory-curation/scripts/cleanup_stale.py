#!/usr/bin/env python3.12
# @hook agentSpawn
# @priority 10
# @skill memory-curation
# @description Delete dropped and stale pending entries, cap longterm.

import subprocess
from pathlib import Path

MEMORY_PY = str(Path(__file__).parent / "memory.py")


def main() -> None:
    subprocess.run(["python3.12", MEMORY_PY, "clean"], check=False)


if __name__ == "__main__":
    main()
