#!/usr/bin/env python3.12
# @hook agentSpawn
# @priority 30
# @skill memory-curation
# @description Inject a reminder when there are parsed entries ready
#   for pattern review, listing top recurring keywords.

import subprocess
from collections import Counter
from pathlib import Path

import memory
from _common import emit_reminder

TOP_N = 5


def main() -> None:
    parsed = [e for e in memory.load() if e["stage"] == "parsed"]
    if not parsed:
        return
    keywords = Counter(kw for e in parsed for kw in e.get("keywords", []))
    top = ", ".join(f"{kw} ({n})" for kw, n in keywords.most_common(TOP_N))
    emit_reminder(
        f"{len(parsed)} parsed entries ready for pattern review.\n"
        f"Top keywords: {top}.\n"
        "Ask the user whether to review now. If confirmed, read "
        "references/pattern-protocol.md and follow its flow."
    )


if __name__ == "__main__":
    main()
