#!/usr/bin/env python3.12
# @hook userPromptSubmit
# @priority 30
# @description Warn if previous turn had writes without verification.

"""At the start of a new turn, check audit.db for the previous turn:
if it contains write operations but no subsequent test/build execution,
inject a reminder."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _db  # noqa: E402

_WRITE_TOOLS = {"fs_write", "write", "file_write"}
_VERIFY_PATTERNS = ("test", "pytest", "npm run", "make", "cargo", "go test", "lint")


def _had_unverified_writes(turn_id: str) -> bool:
    if not turn_id:
        return False
    with _db.connect() as conn:
        rows = conn.execute(
            "SELECT tool, input_summary FROM audit"
            " WHERE turn_id = ? ORDER BY id",
            (turn_id,),
        ).fetchall()

    saw_write = False
    for tool, summary in rows:
        if tool in _WRITE_TOOLS:
            saw_write = True
        elif tool in ("execute_bash", "shell"):
            if any(p in (summary or "") for p in _VERIFY_PATTERNS):
                saw_write = False  # verified
    return saw_write


def main() -> None:
    prev_turn = _db.read_turn_id()
    if prev_turn and _had_unverified_writes(prev_turn):
        print(
            "<unverified-changes>\n"
            "Previous turn wrote files but no test/build was run. "
            "Consider verifying those changes.\n"
            "</unverified-changes>"
        )


if __name__ == "__main__":
    main()
