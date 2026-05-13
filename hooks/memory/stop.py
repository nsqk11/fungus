#!/usr/bin/env python3.12
# @hook stop
# @priority 10
# @description Spawn extract worker, cleanup old events, trigger distill.

import os
import subprocess
import time

from _db import DISTILL_THRESHOLD, get_events_conn, get_memory_conn

FUNGUS_ROOT = os.environ.get("FUNGUS_ROOT", str(__import__("pathlib").Path(__file__).resolve().parent.parent))
EXTRACT_CRITERIA = os.path.join(FUNGUS_ROOT, "prompts", "parse-criteria.md")


def main() -> None:
    # Cleanup events older than 24h (keep those linked to memories)
    cutoff = time.time_ns() - 86400_000_000_000
    mconn = get_memory_conn()
    linked = [r[0] for r in mconn.execute("SELECT source_event_id FROM memories WHERE source_event_id IS NOT NULL").fetchall()]

    econn = get_events_conn()
    if linked:
        placeholders = ",".join("?" * len(linked))
        econn.execute(f"DELETE FROM events WHERE id < ? AND id NOT IN ({placeholders})", [cutoff] + linked)
    else:
        econn.execute("DELETE FROM events WHERE id < ?", (cutoff,))
    deleted = econn.execute("SELECT changes()").fetchone()[0]
    econn.commit()
    if deleted:
        econn.execute("VACUUM")
    econn.close()

    # Cleanup stale drop markers (event already deleted)
    mconn.execute(
        "DELETE FROM meta WHERE key LIKE 'dropped_%' AND CAST(SUBSTR(key, 9) AS INTEGER) < ?",
        (cutoff,),
    )
    mconn.commit()

    # Spawn extract worker
    if os.path.isfile(EXTRACT_CRITERIA):
        with open(EXTRACT_CRITERIA) as f:
            criteria = f.read()
        extract_script = os.path.join(FUNGUS_ROOT, "hooks", "memory", "extract.py")
        extract_prompt = f"""{criteria}

---

## Interface

Do NOT read or write files. Use the CLI tool at `{extract_script}`:

```bash
python3.12 {extract_script} list
python3.12 {extract_script} keep <id> "<summary>" "<detail>" "<tags>"
python3.12 {extract_script} drop <id>
```

Run `list` first, then for each turn decide keep or drop per the criteria above.
"""
        subprocess.Popen(
            ["kiro-cli", "chat", "--no-interactive", "--trust-all-tools", extract_prompt],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
        )
        display = os.environ.get("AGENT_DISPLAY_OUT")
        if display:
            with open(display, "w") as f:
                f.write("\033[35m[memory]\033[0m extracting turn...\n")

    # Distill trigger
    lock = mconn.execute("SELECT value FROM meta WHERE key = 'distill_lock'").fetchone()
    if not lock:
        count = mconn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if count >= DISTILL_THRESHOLD:
            max_id = mconn.execute("SELECT MAX(id) FROM memories").fetchone()[0]
            mconn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('distill_lock', 'active')")
            mconn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('distill_max_id', ?)", (str(max_id),))
            mconn.commit()
    mconn.close()


if __name__ == "__main__":
    main()
