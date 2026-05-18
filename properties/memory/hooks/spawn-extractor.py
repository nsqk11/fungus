#!/usr/bin/env python3
# @hook stop
# @priority 90
# @description Spawn a worker agent to extract memories from unprocessed sessions.
"""On stop, spawn a worker if there are unprocessed sessions."""

import subprocess
import sys
from pathlib import Path

_PROP_DIR = Path(__file__).resolve().parent.parent
_PROMPT = _PROP_DIR / "extract-prompt.md"

sys.path.insert(0, str(_PROP_DIR))


def main() -> None:
    from _memory import find_unprocessed

    if not find_unprocessed() or not _PROMPT.is_file():
        return

    prompt = _PROMPT.read_text(encoding="utf-8")
    subprocess.Popen(
        ["kiro-cli", "chat", "--no-interactive", "--trust-all-tools", prompt],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


if __name__ == "__main__":
    main()
