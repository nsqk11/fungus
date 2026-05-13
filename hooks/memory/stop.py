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
DISTILL_CRITERIA = os.path.join(FUNGUS_ROOT, "prompts", "distill-criteria.md")
DISTILL_THRESHOLD = 200


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

    # Trigger distill if threshold exceeded and no distill in progress
    conn = get_conn()
    lock = conn.execute("SELECT value FROM meta WHERE key = 'distill_lock'").fetchone()
    if not lock:
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if count >= DISTILL_THRESHOLD:
            max_id = conn.execute("SELECT MAX(id) FROM memories").fetchone()[0]
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('distill_lock', strftime('%Y-%m-%dT%H:%M:%f','now'))")
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('distill_max_id', ?)", (str(max_id),))
            conn.commit()
            conn.close()

            distill_script = os.path.join(FUNGUS_ROOT, "hooks", "memory", "distill.py")
            with open(DISTILL_CRITERIA) as f:
                criteria = f.read()
            distill_prompt = f"""{criteria}

---

## Interface

Do NOT read or write files. Use the CLI tool at `{distill_script}`:

```bash
python3.12 {distill_script} list       # show memories to distill
python3.12 {distill_script} apply '<json_array>'  # apply distilled entries
```

Run `list` to see all entries, then apply the distill criteria to merge/supersede/keep/drop.
Call `apply` with a JSON array of objects: [{{"summary": "...", "detail": "...", "tags": "..."}}]
"""
            subprocess.Popen(
                ["kiro-cli", "chat", "--no-interactive", "--trust-all-tools", distill_prompt],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        else:
            conn.close()
    else:
        conn.close()


if __name__ == "__main__":
    main()
