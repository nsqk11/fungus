#!/usr/bin/env python3.12
"""Extract worker CLI: list pending turns from events DB, keep or drop.

Usage:
    python3.12 extract.py list
    python3.12 extract.py keep <prompt_event_id> "<summary>" "<detail>" "<tags>"
    python3.12 extract.py drop <prompt_event_id>
"""

import sys
from datetime import date

from _db import DATA_DIR, get_events_conn, get_memory_conn


def list_turns() -> None:
    econn = get_events_conn()
    mconn = get_memory_conn()

    # Get already-processed event ids
    kept = {r[0] for r in mconn.execute("SELECT source_event_id FROM memories WHERE source_event_id IS NOT NULL").fetchall()}
    dropped = {int(r[0].split("_", 1)[1]) for r in mconn.execute("SELECT key FROM meta WHERE key LIKE 'dropped_%'").fetchall()}
    processed = kept | dropped
    mconn.close()

    # Get all userPromptSubmit events
    prompts = econn.execute("SELECT id, session_id, prompt FROM events WHERE hook = 'userPromptSubmit' ORDER BY id").fetchall()

    pending = []
    for pid, sid, prompt in prompts:
        if pid in processed:
            continue
        # Check if this turn has a stop event
        next_prompt = econn.execute(
            "SELECT MIN(id) FROM events WHERE session_id = ? AND hook = 'userPromptSubmit' AND id > ?", (sid, pid)
        ).fetchone()[0] or 9999999999999999999
        stop = econn.execute(
            "SELECT response FROM events WHERE session_id = ? AND hook = 'stop' AND id > ? AND id < ? ORDER BY id DESC LIMIT 1",
            (sid, pid, next_prompt),
        ).fetchone()
        if not stop:
            continue
        tools = econn.execute(
            "SELECT tool_name FROM events WHERE session_id = ? AND hook = 'preToolUse' AND id > ? AND id < ?",
            (sid, pid, next_prompt),
        ).fetchall()
        pending.append((pid, prompt, [t[0] for t in tools], stop[0]))

    econn.close()

    if not pending:
        print("No pending turns.")
        return
    for pid, prompt, tools, response in pending:
        print(f"--- Turn {pid} ---")
        print(f"PROMPT: {prompt}")
        if tools:
            print(f"TOOLS: {', '.join(tools)}")
        if response:
            print(f"RESPONSE: {response[:200]}")
        print()


def keep_turn(event_id: int, summary: str, detail: str = "", tags: str = "") -> None:
    mconn = get_memory_conn()
    mconn.execute(
        "INSERT INTO memories (summary, detail, tags, source_event_id) VALUES (?, ?, ?, ?)",
        (summary, detail, tags, event_id),
    )
    mconn.commit()
    mconn.close()
    _export_memory(summary, detail, tags)
    print(f"Turn {event_id} archived.")


def drop_turn(event_id: int) -> None:
    mconn = get_memory_conn()
    mconn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, '1')", (f"dropped_{event_id}",))
    mconn.commit()
    mconn.close()
    print(f"Turn {event_id} dropped.")


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
        keep_turn(int(sys.argv[2]), sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "", sys.argv[5] if len(sys.argv) > 5 else "")
    elif cmd == "drop" and len(sys.argv) >= 3:
        drop_turn(int(sys.argv[2]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
