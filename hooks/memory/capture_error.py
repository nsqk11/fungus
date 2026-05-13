#!/usr/bin/env python3.12
# @hook postToolUse
# @priority 10
# @description Append error info to current turn's tools column on failure.

import json
import sys

from _db import SESSION_ID, get_conn


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
    response = payload.get("tool_response", {})
    if response.get("success") is not False:
        return
    error = " ".join(str(response.get("error", "")).split()).strip()
    if not error:
        return
    conn = get_conn()
    conn.execute(
        """UPDATE turns
           SET tools = CASE WHEN tools = '' THEN ? ELSE tools || char(10) || ? END,
               status = 'postToolUse',
               updated_at = strftime('%Y-%m-%dT%H:%M:%f','now')
           WHERE id = (SELECT MAX(id) FROM turns WHERE session_id = ?)""",
        (f"ERROR: {error}", f"ERROR: {error}", SESSION_ID),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
