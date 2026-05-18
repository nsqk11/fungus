#!/usr/bin/env python3
# @hook userPromptSubmit
# @priority 20
# @description Analyze user message and selectively inject reminders.
"""Call LLM to analyze content tendencies, then inject matched reminders."""

import json
import re
import subprocess
import sys
from pathlib import Path

_PROP_DIR = Path(__file__).resolve().parent.parent
_PROMPT_PATH = _PROP_DIR / "analyze-prompt.md"

# Reminder texts keyed by tendency key
_REMINDERS = {
    "memory-correction": (
        "<memory-reminder>\n"
        "Search `fungus-memory` KB for correction memories — the user may have "
        "previously corrected similar behavior.\n"
        "</memory-reminder>"
    ),
    "memory-preference": (
        "<memory-reminder>\n"
        "Search `fungus-memory` KB for preference memories — the user may have "
        "stated preferences about this type of output or workflow.\n"
        "</memory-reminder>"
    ),
    "memory-discovery": (
        "<memory-reminder>\n"
        "Search `fungus-memory` KB for discovery memories — there may be known "
        "pitfalls or workarounds for this operation.\n"
        "</memory-reminder>"
    ),
    "memory-decision": (
        "<memory-reminder>\n"
        "Search `fungus-memory` KB for decision memories — prior architecture or "
        "design decisions may be relevant.\n"
        "</memory-reminder>"
    ),
    "todo-check": (
        "<todo-reminder>\n"
        "Check the active task list before starting new work.\n"
        "</todo-reminder>"
    ),
    "scope-creep": (
        "<scope-reminder>\n"
        "The user asked for a small, focused change. Do exactly that — "
        "no extra refactoring or improvements.\n"
        "</scope-reminder>"
    ),
    "confirm-destructive": (
        "<destructive-warning>\n"
        "This involves an irreversible operation. Confirm with the user "
        "before executing.\n"
        "</destructive-warning>"
    ),
    "language-match": (
        "<language-reminder>\n"
        "Reply in the same language the user is writing in.\n"
        "</language-reminder>"
    ),
}


def main() -> None:
    if not _PROMPT_PATH.is_file():
        return

    # Read user message from stdin (hook payload)
    payload = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}
    content = payload.get("data", {}).get("content", "")
    if not content:
        return

    # Build prompt
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    prompt = template.replace("{content}", content)

    # Call LLM synchronously
    result = subprocess.run(
        ["kiro-cli", "chat", "--no-interactive", "--trust-all-tools", prompt],
        capture_output=True, text=True, check=False,
    )

    # Parse matched keys from output
    output = result.stdout.strip()
    match = re.search(r"\[.*?\]", output)
    if not match:
        return

    try:
        keys = json.loads(match.group())
    except json.JSONDecodeError:
        return

    # Inject matched reminders
    for key in keys:
        if key in _REMINDERS:
            print(_REMINDERS[key])


if __name__ == "__main__":
    main()
