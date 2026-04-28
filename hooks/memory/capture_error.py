#!/usr/bin/env python3.12
# @hook postToolUse
# @priority 10
# @description Append ERROR line to current-turn.txt on tool failure.

from _common import TURN_FILE, read_payload


def main() -> None:
    payload = read_payload()
    response = payload.get("tool_response", {})
    if response.get("success") is not False:
        return
    if not TURN_FILE.exists():
        return
    error = str(response.get("error", "")).strip()
    if not error:
        return
    # Collapse multi-line errors to a single line for the turn file.
    error = " ".join(error.split())
    with TURN_FILE.open("a", encoding="utf-8") as f:
        f.write(f"ERROR: {error}\n")


if __name__ == "__main__":
    main()
