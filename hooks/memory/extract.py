#!/usr/bin/env python3.12
"""Extract worker CLI: list pending turns, keep or drop them.

Usage:
    python3.12 extract.py list
    python3.12 extract.py keep <id> "<summary>" "<detail>" "<tags>"
    python3.12 extract.py drop <id>
"""

import sys
from datetime import date

from _db import DATA_DIR, get_conn


def list_turns() -> None:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, prompt, tools, response FROM turns WHERE status = 'stop'"
    ).fetchall()
    conn.close()
    if not rows:
        print("No pending turns.")
        return
    for r in rows:
        print(f"--- Turn {r[0]} ---")
        print(f"PROMPT: {r[1]}")
        if r[2]:
            print(r[2])
        if r[3]:
            print(f"RESPONSE: {r[3][:200]}")
        print()


def claim_turn(turn_id: int) -> bool:
    """Optimistic lock: claim a turn for extraction. Returns False if already claimed."""
    conn = get_conn()
    cur = conn.execute(
        "UPDATE turns SET status = 'extracting' WHERE id = ? AND status = 'stop'",
        (turn_id,),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def keep_turn(turn_id: int, summary: str, detail: str = "", tags: str = "") -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO memories (summary, detail, tags, source_turn_id) VALUES (?, ?, ?, ?)",
        (summary, detail, tags, turn_id),
    )
    conn.execute("UPDATE turns SET status = 'archived' WHERE id = ?", (turn_id,))
    conn.commit()
    conn.close()
    _export_memory(summary, detail, tags)
    print(f"Turn {turn_id} archived.")


def drop_turn(turn_id: int) -> None:
    conn = get_conn()
    conn.execute("UPDATE turns SET status = 'dropped' WHERE id = ?", (turn_id,))
    conn.commit()
    conn.close()
    print(f"Turn {turn_id} dropped.")


def _export_memory(summary: str, detail: str, tags: str) -> None:
    md_path = DATA_DIR / "long-term-memory.md"
    entry = f"\n## {summary}\n\nDate: {date.today().isoformat()} | Tags: {tags}\n"
    if detail:
        entry += f"\n{detail}\n"
    with open(md_path, "a", encoding="utf-8") as f:
        f.write(entry)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "list":
        list_turns()
    elif cmd == "keep" and len(sys.argv) >= 4:
        turn_id = int(sys.argv[2])
        if not claim_turn(turn_id):
            print(f"Turn {turn_id} already claimed by another worker.")
            return
        summary = sys.argv[3]
        detail = sys.argv[4] if len(sys.argv) > 4 else ""
        tags = sys.argv[5] if len(sys.argv) > 5 else ""
        keep_turn(turn_id, summary, detail, tags)
    elif cmd == "drop" and len(sys.argv) >= 3:
        turn_id = int(sys.argv[2])
        if not claim_turn(turn_id):
            print(f"Turn {turn_id} already claimed by another worker.")
            return
        drop_turn(turn_id)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
