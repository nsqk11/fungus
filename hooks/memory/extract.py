#!/usr/bin/env python3.12
"""Extract worker: derive turns from events, send to LLM for multi-direction extraction.

Usage:
    python3.12 extract.py list          # show pending turns (dry-run)
    python3.12 extract.py run           # extract all pending turns via LLM
    python3.12 extract.py keep '<json>' <prompt_event_id>  # manual insert (testing)
    python3.12 extract.py drop <prompt_event_id>           # manual drop
"""

import json
import sys
from datetime import date
from pathlib import Path

from _db import (
    CATEGORIES,
    DATA_DIR,
    DECLARATIVE,
    NON_DECLARATIVE,
    get_events_conn,
    get_memory_conn,
)

CRITERIA_PATH = Path(__file__).resolve().parent.parent / "prompts" / "extract-criteria.md"


def _pending_turns() -> list[tuple[int, str, list[str], str]]:
    """Return list of (prompt_event_id, prompt, tools, response) for unprocessed turns."""
    econn = get_events_conn()
    mconn = get_memory_conn()

    kept = {r[0] for r in mconn.execute(
        "SELECT source_event_id FROM memories WHERE source_event_id IS NOT NULL"
    ).fetchall()}
    dropped = {int(r[0].split("_", 1)[1]) for r in mconn.execute(
        "SELECT key FROM meta WHERE key LIKE 'dropped_%'"
    ).fetchall()}
    processed = kept | dropped
    mconn.close()

    prompts = econn.execute(
        "SELECT id, session_id, prompt FROM events WHERE hook = 'userPromptSubmit' ORDER BY id"
    ).fetchall()

    pending = []
    for pid, sid, prompt in prompts:
        if pid in processed:
            continue
        next_prompt = econn.execute(
            "SELECT MIN(id) FROM events WHERE session_id = ? AND hook = 'userPromptSubmit' AND id > ?",
            (sid, pid),
        ).fetchone()[0]
        if next_prompt:
            stop = econn.execute(
                "SELECT response FROM events WHERE session_id = ? AND hook = 'stop' AND id > ? AND id < ? ORDER BY id DESC LIMIT 1",
                (sid, pid, next_prompt),
            ).fetchone()
            tools = econn.execute(
                "SELECT tool_name FROM events WHERE session_id = ? AND hook = 'preToolUse' AND id > ? AND id < ?",
                (sid, pid, next_prompt),
            ).fetchall()
        else:
            stop = econn.execute(
                "SELECT response FROM events WHERE session_id = ? AND hook = 'stop' AND id > ? ORDER BY id DESC LIMIT 1",
                (sid, pid),
            ).fetchone()
            tools = econn.execute(
                "SELECT tool_name FROM events WHERE session_id = ? AND hook = 'preToolUse' AND id > ?",
                (sid, pid),
            ).fetchall()
        if not stop:
            continue
        pending.append((pid, prompt, [t[0] for t in tools], stop[0]))

    econn.close()
    return pending


def _format_turn(prompt: str, tools: list[str], response: str) -> str:
    """Format turn data for the LLM prompt."""
    parts = [f"PROMPT: {prompt}"]
    if tools:
        parts.append(f"TOOLS: {', '.join(tools)}")
    if response:
        parts.append(f"RESPONSE: {response[:2000]}")
    return "\n".join(parts)


def list_turns() -> None:
    """Print pending turns for inspection."""
    pending = _pending_turns()
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
    print(f"Total: {len(pending)} pending turns.")


def _save_memories(entries: list[dict], event_id: int) -> None:
    """Save extracted memories to DB and export files."""
    mconn = get_memory_conn()
    for entry in entries:
        cat = entry.get("category", "").lower()
        if cat not in CATEGORIES:
            continue
        mconn.execute(
            "INSERT INTO memories (summary, detail, tags, category, source_event_id) VALUES (?, ?, ?, ?, ?)",
            (entry["summary"], entry.get("detail", ""), entry.get("tags", ""), cat, event_id),
        )
    mconn.commit()
    mconn.close()
    _export_all()


def _mark_dropped(event_id: int) -> None:
    """Mark a turn as dropped."""
    mconn = get_memory_conn()
    mconn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, '1')", (f"dropped_{event_id}",))
    mconn.commit()
    mconn.close()


def _export_all() -> None:
    """Re-export all memories to category-split files."""
    mconn = get_memory_conn()
    rows = mconn.execute(
        "SELECT summary, detail, tags, category, created_at FROM memories ORDER BY id"
    ).fetchall()
    mconn.close()

    # Group by output target
    declarative: dict[str, list] = {c: [] for c in DECLARATIVE}
    non_declarative: dict[str, list] = {c: [] for c in NON_DECLARATIVE}

    for summary, detail, tags, category, created_at in rows:
        cat = category or "semantic"  # legacy entries without category
        entry_date = created_at[:10] if created_at else date.today().isoformat()
        md_entry = f"## {summary}\n\nDate: {entry_date} | Tags: {tags}\n"
        if detail:
            md_entry += f"\n{detail}\n"
        if cat in declarative:
            declarative[cat].append(md_entry)
        elif cat in non_declarative:
            non_declarative[cat].append(md_entry)
        else:
            declarative["semantic"].append(md_entry)

    # Write declarative KB files
    for cat, entries in declarative.items():
        path = DATA_DIR / f"memory-{cat}.md"
        content = f"# Fungus Memory — {cat.title()}\n\n" + "\n".join(entries) if entries else ""
        path.write_text(content, encoding="utf-8") if entries else path.unlink(missing_ok=True)

    # Write non-declarative prompt file
    nd_entries = []
    for cat, entries in non_declarative.items():
        if entries:
            nd_entries.append(f"### {cat.title()}\n\n" + "\n".join(entries))
    nd_path = DATA_DIR / "memory-procedural.md"
    if nd_entries:
        nd_path.write_text("# Fungus Memory — Non-declarative\n\n" + "\n".join(nd_entries), encoding="utf-8")
    else:
        nd_path.unlink(missing_ok=True)

    # Also maintain legacy combined file for backward compat
    all_entries = []
    for entries in declarative.values():
        all_entries.extend(entries)
    for entries in non_declarative.values():
        all_entries.extend(entries)
    legacy_path = DATA_DIR / "long-term-memory.md"
    legacy_path.write_text("# Fungus Memory\n\n" + "\n".join(all_entries), encoding="utf-8")


def run_extraction() -> None:
    """Process all pending turns through LLM extraction."""
    pending = _pending_turns()
    if not pending:
        print("No pending turns.")
        return

    for pid, prompt, tools, response in pending:
        turn_text = _format_turn(prompt, tools, response)
        # The actual LLM call is done by the agent worker that invokes this.
        # This script outputs the turn data for the agent to process.
        print(f"EXTRACT_TURN:{pid}")
        print(turn_text)
        print("END_TURN")


def keep_manual(json_str: str, event_id: int) -> None:
    """Manually insert memories from JSON (for testing or agent use)."""
    entries = json.loads(json_str)
    if not isinstance(entries, list):
        entries = [entries]
    _save_memories(entries, event_id)
    print(f"Saved {len(entries)} memories from turn {event_id}.")


def drop_manual(event_id: int) -> None:
    """Manually drop a turn."""
    _mark_dropped(event_id)
    print(f"Turn {event_id} dropped.")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "list":
        list_turns()
    elif cmd == "run":
        run_extraction()
    elif cmd == "keep" and len(sys.argv) >= 4:
        keep_manual(sys.argv[2], int(sys.argv[3]))
    elif cmd == "drop" and len(sys.argv) >= 3:
        drop_manual(int(sys.argv[2]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
