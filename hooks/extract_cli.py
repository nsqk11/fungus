#!/usr/bin/env python3
"""CLI for the memory extraction agent.

Usage:
    extract_cli.py list                         # show pending turns
    extract_cli.py keep '<json_array>' <id>     # save extracted memories
    extract_cli.py drop <id>                    # mark turn as dropped
"""

import json
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))

from _event import get_conn as get_events_conn, mark_read
from _memory import save_memories, mark_dropped


def _pending_turns() -> list[tuple[int, list[dict]]]:
    """Return (stop_event_id, events) for unprocessed turns.

    A turn is all events with read=0 and id < stop_event_id in the same session.
    """
    conn = get_events_conn()
    stops = conn.execute(
        "SELECT id, session_id FROM events WHERE hook = 'stop' AND read = 0 ORDER BY id"
    ).fetchall()

    pending = []
    for stop_id, session_id in stops:
        rows = conn.execute(
            "SELECT id, hook, prompt, tool_name, response FROM events"
            " WHERE session_id = ? AND read = 0 AND id <= ?"
            " ORDER BY id",
            (session_id, stop_id),
        ).fetchall()
        if rows:
            pending.append((stop_id, [
                {"id": r[0], "hook": r[1], "prompt": r[2], "tool_name": r[3], "response": r[4]}
                for r in rows
            ]))
    conn.close()
    return pending


def _format_turn(events: list[dict]) -> str:
    """Format turn events for display."""
    prompt = next((e["prompt"] for e in events if e["hook"] == "userPromptSubmit" and e["prompt"]), "")
    tools = [e["tool_name"] for e in events if e["hook"] == "preToolUse" and e["tool_name"]]
    response = next((e["response"] for e in events if e["hook"] == "stop" and e["response"]), "")

    parts = [f"PROMPT: {prompt}"]
    if tools:
        parts.append(f"TOOLS: {', '.join(tools)}")
    if response:
        parts.append(f"RESPONSE: {response[:2000]}")
    return "\n".join(parts)


def cmd_list() -> None:
    """Print pending turns for the extraction agent."""
    pending = _pending_turns()
    if not pending:
        print("No pending turns.")
        return
    for stop_id, events in pending:
        print(f"--- Turn {stop_id} ---")
        print(_format_turn(events))
        print()
    print(f"Total: {len(pending)} pending turns.")


def cmd_keep(json_str: str, stop_id: int) -> None:
    """Save extracted memories and mark turn events as read."""
    entries = json.loads(json_str)
    if not isinstance(entries, list):
        entries = [entries]
    save_memories(entries, stop_id)
    _mark_turn_read(stop_id)
    print(f"Saved {len(entries)} memories from turn {stop_id}.")


def cmd_drop(stop_id: int) -> None:
    """Mark a turn as dropped and its events as read."""
    mark_dropped(stop_id)
    _mark_turn_read(stop_id)
    print(f"Turn {stop_id} dropped.")


def _mark_turn_read(stop_id: int) -> None:
    """Mark all events in a turn as read."""
    conn = get_events_conn()
    session_id = conn.execute(
        "SELECT session_id FROM events WHERE id = ?", (stop_id,)
    ).fetchone()[0]
    conn.execute(
        "UPDATE events SET read = 1 WHERE session_id = ? AND read = 0 AND id <= ?",
        (session_id, stop_id),
    )
    conn.commit()
    conn.close()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list()
    elif cmd == "keep" and len(sys.argv) >= 4:
        cmd_keep(sys.argv[2], int(sys.argv[3]))
    elif cmd == "drop" and len(sys.argv) >= 3:
        cmd_drop(int(sys.argv[2]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
