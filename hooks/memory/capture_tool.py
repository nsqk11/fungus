#!/usr/bin/env python3.12
# @hook preToolUse
# @priority 10
# @description Append tool name to current turn's tools column.

import json
import sys

from _db import NOISE_TOOLS, SESSION_ID, get_conn


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
    tool = payload.get("tool_name", "")
    if not tool or tool in NOISE_TOOLS:
        return
    conn = get_conn()
    conn.execute(
        """UPDATE turns
           SET tools = CASE WHEN tools = '' THEN ? ELSE tools || char(10) || ? END,
               status = 'preToolUse',
               updated_at = strftime('%Y-%m-%dT%H:%M:%f','now')
           WHERE id = (SELECT MAX(id) FROM turns WHERE session_id = ?)""",
        (f"TOOL: {tool}", f"TOOL: {tool}", SESSION_ID),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
