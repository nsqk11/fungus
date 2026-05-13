#!/usr/bin/env python3.12
# @hook userPromptSubmit
# @priority 20
# @description Remind the agent to consult the fungus-memory KB when unsure.

import os


def main() -> None:
    out = os.environ.get("AGENT_CONTEXT_OUT")
    display = os.environ.get("AGENT_DISPLAY_OUT")
    msg = (
        "<memory-reminder>\n"
        "If the user's message is ambiguous or references prior "
        "context you do not recognize, search the `fungus-memory` "
        "knowledge base before answering.\n"
        "</memory-reminder>"
    )
    if display:
        with open(display, "w") as f:
            f.write("\033[36m[memory]\033[0m remind: search fungus-memory if unsure\n")
    if out:
        with open(out, "w") as f:
            f.write(msg)
    else:
        print(msg)


if __name__ == "__main__":
    main()
