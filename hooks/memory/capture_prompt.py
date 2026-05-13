#!/usr/bin/env python3.12
# @hook userPromptSubmit
# @priority 10
# @description Insert new turn row on user prompt.

import json
import sys

from _db import MIN_PROMPT_LEN, SESSION_ID, get_conn


def read_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    raw = sys.stdin.read()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def main() -> None:
    payload = read_payload()
    prompt = payload.get("prompt", "").strip()
    if len(prompt) < MIN_PROMPT_LEN:
        return
    conn = get_conn()
    conn.execute(
        "INSERT INTO turns (session_id, prompt, status) VALUES (?, ?, 'userPromptSubmit')",
        (SESSION_ID, prompt),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
