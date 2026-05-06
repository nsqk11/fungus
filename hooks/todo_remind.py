#!/usr/bin/env python3.12
# @hook userPromptSubmit
# @priority 35
# @description Remind agent of incomplete todo items from previous turn.

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "audit"))

import _db  # noqa: E402


def main() -> None:
    marker = _db.audit_dir() / "incomplete-todo.flag"
    if not marker.exists():
        return
    try:
        count = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return
    marker.unlink(missing_ok=True)
    print(
        "<incomplete-todo>\n"
        f"Previous turn ended with {count} incomplete task(s). "
        "Continue working on them or update the task list.\n"
        "</incomplete-todo>"
    )


if __name__ == "__main__":
    main()
