#!/usr/bin/env python3.12
# @hook preToolUse
# @priority 10
# @description Append TOOL line to the current turn file (skipping noise tools).

from _common import NOISE_TOOLS, latest_turn_file, read_payload


def main() -> None:
    payload = read_payload()
    tool = payload.get("tool_name", "")
    if not tool or tool in NOISE_TOOLS:
        return
    turn = latest_turn_file()
    if turn is None:
        return
    with turn.open("a", encoding="utf-8") as f:
        f.write(f"TOOL: {tool}\n")


if __name__ == "__main__":
    main()
