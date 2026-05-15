#!/usr/bin/env python3
# @hook userPromptSubmit
# @priority 30
# @description Remind the agent about incomplete todo items.
"""Emit a todo-reminder if there are pending tasks."""

import json
import sys


def main() -> None:
    payload = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}
    # The todo state is managed by the agent tool; this is a nudge only.
    print(
        "<todo-reminder>\n"
        "If you have an active task list, check it before starting new work.\n"
        "</todo-reminder>"
    )


if __name__ == "__main__":
    main()
