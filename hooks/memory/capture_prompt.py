#!/usr/bin/env python3.12
# @hook userPromptSubmit
# @priority 10
# @description Start a new turn: write PROMPT line to current-turn.txt.

from _common import MIN_PROMPT_LEN, TURN_FILE, ensure_data_dir, read_payload


def main() -> None:
    payload = read_payload()
    prompt = payload.get("prompt", "").strip()
    if len(prompt) < MIN_PROMPT_LEN:
        return
    ensure_data_dir()
    # Overwrite — a new user prompt starts a new turn. If a stale
    # turn file exists from a crashed prior turn, it is discarded.
    TURN_FILE.write_text(f"PROMPT: {prompt}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
