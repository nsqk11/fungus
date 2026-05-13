#!/usr/bin/env python3.12
"""Distill worker CLI: list memories, apply distilled results, unlock.

Usage:
    python3.12 distill.py list                    # show all memories up to snapshot max_id
    python3.12 distill.py apply "<entries_json>"  # replace old entries with distilled ones
    python3.12 distill.py unlock                  # remove distill lock (manual recovery)
"""

import json
import sys
from datetime import date

from _db import DATA_DIR, get_conn

DISTILL_THRESHOLD = 200


def list_memories() -> None:
    conn = get_conn()
    max_id = conn.execute("SELECT value FROM meta WHERE key = 'distill_max_id'").fetchone()
    if not max_id:
        print("No distill in progress.")
        conn.close()
        return
    max_id = int(max_id[0])
    rows = conn.execute(
        "SELECT id, summary, detail, tags FROM memories WHERE id <= ?", (max_id,)
    ).fetchall()
    conn.close()
    print(f"Distilling {len(rows)} memories (id <= {max_id}):\n")
    for r in rows:
        print(f"--- Memory {r[0]} ---")
        print(f"## {r[1]}")
        if r[3]:
            print(f"Tags: {r[3]}")
        if r[2]:
            print(r[2])
        print()


def apply_distill(entries_json: str) -> None:
    """Replace old memories with distilled entries.

    entries_json is a JSON array of objects: [{"summary": "...", "detail": "...", "tags": "..."}, ...]
    """
    conn = get_conn()
    max_id_row = conn.execute("SELECT value FROM meta WHERE key = 'distill_max_id'").fetchone()
    if not max_id_row:
        print("No distill in progress. Run from stop.py trigger.")
        conn.close()
        return
    max_id = int(max_id_row[0])

    entries = json.loads(entries_json)

    # Delete old entries
    conn.execute("DELETE FROM memories WHERE id <= ?", (max_id,))

    # Insert distilled entries
    for e in entries:
        conn.execute(
            "INSERT INTO memories (summary, detail, tags) VALUES (?, ?, ?)",
            (e.get("summary", ""), e.get("detail", ""), e.get("tags", "")),
        )

    # Remove lock
    conn.execute("DELETE FROM meta WHERE key IN ('distill_lock', 'distill_max_id')")
    conn.commit()
    conn.close()

    # Re-export full long-term-memory.md
    _export_all()
    print(f"Distill applied: {len(entries)} entries replaced {max_id} old entries.")


def unlock() -> None:
    conn = get_conn()
    conn.execute("DELETE FROM meta WHERE key IN ('distill_lock', 'distill_max_id')")
    conn.commit()
    conn.close()
    print("Distill lock removed.")


def _export_all() -> None:
    """Full export of memories table to long-term-memory.md."""
    conn = get_conn()
    rows = conn.execute("SELECT summary, detail, tags, created_at FROM memories ORDER BY id").fetchall()
    conn.close()

    md_path = DATA_DIR / "long-term-memory.md"
    lines = ["# Fungus Memory\n"]
    for summary, detail, tags, created_at in rows:
        d = created_at[:10] if created_at else date.today().isoformat()
        lines.append(f"\n\n## {summary}\n\nDate: {d} | Tags: {tags}")
        if detail:
            lines.append(f"\n\n{detail}")
    md_path.write_text("".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "list":
        list_memories()
    elif cmd == "apply" and len(sys.argv) >= 3:
        apply_distill(sys.argv[2])
    elif cmd == "unlock":
        unlock()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
