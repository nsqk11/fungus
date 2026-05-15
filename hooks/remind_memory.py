#!/usr/bin/env python3
# @hook userPromptSubmit
# @priority 20
# @description Remind the agent to search fungus-memory KB when unsure.
"""Emit a memory-reminder context injection."""


def main() -> None:
    print(
        "<memory-reminder>\n"
        "If the user's message is ambiguous or references prior "
        "context you do not recognize, search the `fungus-memory` "
        "knowledge base before answering.\n"
        "</memory-reminder>"
    )


if __name__ == "__main__":
    main()
