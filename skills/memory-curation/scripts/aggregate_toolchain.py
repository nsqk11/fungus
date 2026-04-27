#!/usr/bin/env python3.12
# @hook stop
# @priority 20
# @skill memory-curation
# @description Aggregate preToolUse raw entries since last user prompt
#   into a single toolChain raw entry. Delete the individual preToolUse
#   entries afterwards.

import json
from datetime import datetime, timezone
from pathlib import Path

import memory


def main() -> None:
    entries = memory.load()

    # Find the last userPromptSubmit to mark the turn boundary.
    boundary_idx = -1
    for i in range(len(entries) - 1, -1, -1):
        e = entries[i]
        if e["stage"] == "raw" and e["hook"] == "userPromptSubmit":
            boundary_idx = i
            break
    if boundary_idx < 0:
        return

    # Collect preToolUse entries after the boundary.
    tool_entries = [
        e for e in entries[boundary_idx + 1:]
        if e["stage"] == "raw" and e["hook"] == "preToolUse"
    ]
    if not tool_entries:
        return

    tool_names = [e["data"].get("tool_name", "") for e in tool_entries]

    # Build toolChain entry.
    next_entries = [e for e in entries if e not in tool_entries]
    chain_id = datetime.now(timezone.utc).strftime("%Y%m%d")
    existing_today = [e["id"] for e in next_entries if e["id"].startswith(chain_id)]
    seq = max((int(i[8:]) for i in existing_today), default=0) + 1
    chain_id = f"{chain_id}{seq:03d}"

    next_entries.append({
        "id": chain_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": "raw",
        "hook": "toolChain",
        "data": {"tools": tool_names},
        "summary": "",
        "keywords": [],
        "refs": [e["id"] for e in tool_entries],
        "category": "",
    })
    memory.save(next_entries)


if __name__ == "__main__":
    main()
