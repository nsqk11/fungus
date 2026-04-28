#!/usr/bin/env python3.12
# @hook userPromptSubmit
# @priority 10
# @description Start a new turn: write PROMPT line to turn-<ts>.txt.

from _common import MIN_PROMPT_LEN, new_turn_file, read_payload


def main() -> None:
    payload = read_payload()
    prompt = payload.get("prompt", "").strip()
    if len(prompt) < MIN_PROMPT_LEN:
        return
    turn_file = new_turn_file()
    turn_file.write_text(f"PROMPT: {prompt}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
