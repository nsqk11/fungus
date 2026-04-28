#!/usr/bin/env python3.12
# @hook preToolUse
# @priority 10
# @description Append TOOL line to current-turn.txt (skipping noise tools).

from _common import NOISE_TOOLS, TURN_FILE, read_payload


def main() -> None:
    payload = read_payload()
    tool = payload.get("tool_name", "")
    if not tool or tool in NOISE_TOOLS:
        return
    if not TURN_FILE.exists():
        return
    with TURN_FILE.open("a", encoding="utf-8") as f:
        f.write(f"TOOL: {tool}\n")


if __name__ == "__main__":
    main()
