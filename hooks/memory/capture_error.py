#!/usr/bin/env python3.12
# @hook postToolUse
# @priority 10
# @description Append ERROR line to the current turn file on tool failure.

from _common import latest_turn_file, read_payload


def main() -> None:
    payload = read_payload()
    response = payload.get("tool_response", {})
    if response.get("success") is not False:
        return
    turn = latest_turn_file()
    if turn is None:
        return
    error = str(response.get("error", "")).strip()
    if not error:
        return
    # Collapse multi-line errors to a single line for the turn file.
    error = " ".join(error.split())
    with turn.open("a", encoding="utf-8") as f:
        f.write(f"ERROR: {error}\n")


if __name__ == "__main__":
    main()
