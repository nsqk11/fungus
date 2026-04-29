#!/usr/bin/env python3.12
# @hook userPromptSubmit
# @priority 5
# @description Mint a new turn id for the audit pipeline.

"""Called on every user prompt. Generates a fresh turn id and stores it
so that ``record_pre.py`` and ``record_post.py`` can tag tool calls
with the current turn.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow sibling import of _db from this hooks/audit/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _db  # noqa: E402


def main() -> None:
    # We don't read stdin — router forwards it but we don't need it.
    # Draining it prevents blocking if the caller buffered.
    try:
        _ = sys.stdin.read()
    except OSError:
        pass

    turn_id = _db.new_turn_id()
    _db.write_turn_id(turn_id)
    _db.clear_reminder_markers()


if __name__ == "__main__":
    main()
