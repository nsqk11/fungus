#!/usr/bin/env python3.12
# @hook stop
# @priority 10
# @description Finalize turn: write response, set status='stop', spawn extract worker.

import json
import os
import subprocess
import sys

from _db import SESSION_ID, get_conn

FUNGUS_ROOT = os.environ.get("FUNGUS_ROOT", str(__import__("pathlib").Path(__file__).resolve().parent.parent))
EXTRACT_CRITERIA = os.path.join(FUNGUS_ROOT, "prompts", "parse-criteria.md")


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
    response = payload.get("assistant_response", "")

    conn = get_conn()
    conn.execute(
        """UPDATE turns
           SET response = ?, status = 'stop',
               updated_at = strftime('%Y-%m-%dT%H:%M:%f','now')
           WHERE id = (SELECT MAX(id) FROM turns WHERE session_id = ?)""",
        (response, SESSION_ID),
    )
    conn.commit()
    conn.close()

    # Spawn extract worker (detached)
    if os.path.isfile(EXTRACT_CRITERIA):
        with open(EXTRACT_CRITERIA) as f:
            criteria = f.read()
        extract_script = os.path.join(FUNGUS_ROOT, "hooks", "memory", "extract.py")
        extract_prompt = f"""{criteria}

---

## Interface

Do NOT read or write files. Use the CLI tool at `{extract_script}`:

```bash
python3.12 {extract_script} list                              # show pending turns
python3.12 {extract_script} keep <id> "<summary>" "<detail>" "<tags>"
python3.12 {extract_script} drop <id>
```

Run `list` first, then for each turn decide keep or drop per the criteria above.
"""
        subprocess.Popen(
            ["kiro-cli", "chat", "--no-interactive", "--trust-all-tools", extract_prompt],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


if __name__ == "__main__":
    main()
