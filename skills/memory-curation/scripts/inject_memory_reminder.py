#!/usr/bin/env python3.12
# @hook userPromptSubmit
# @priority 20
# @skill memory-curation
# @description Inject a reminder for the agent to ground ambiguous
#   user messages in long-term memory.

from _common import emit_reminder


def main() -> None:
    emit_reminder(
        "If the user's message is ambiguous or unclear, search the "
        "long-term memory for relevant context before answering."
    )


if __name__ == "__main__":
    main()
