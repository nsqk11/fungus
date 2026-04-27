#!/usr/bin/env python3.12
# @hook stop
# @priority 20
# @skill memory-curation
# @description Aggregate preToolUse raw entries since last user prompt
#   into a single toolChain raw entry.

import json
import subprocess
from pathlib import Path

MEMORY_PY = str(Path(__file__).parent / "memory.py")


def _list_raw() -> list[dict]:
    result = subprocess.run(
        ["python3.12", MEMORY_PY, "list", "--stage", "raw"],
        capture_output=True, text=True, check=False,
    )
    return [json.loads(line) for line in result.stdout.splitlines() if line]


def main() -> None:
    entries = _list_raw()

    # Find the last userPromptSubmit as turn boundary.
    boundary_idx = -1
    for i in range(len(entries) - 1, -1, -1):
        if entries[i]["hook"] == "userPromptSubmit":
            boundary_idx = i
            break
    if boundary_idx < 0:
        return

    tool_entries = [
        e for e in entries[boundary_idx + 1:]
        if e["hook"] == "preToolUse"
    ]
    if not tool_entries:
        return

    tool_names = [e["data"].get("tool_name", "") for e in tool_entries]
    chain_data = {"tools": tool_names, "refs": [e["id"] for e in tool_entries]}

    # Insert the aggregated chain entry.
    subprocess.run(
        ["python3.12", MEMORY_PY, "add",
         "--stage", "raw",
         "--hook", "toolChain",
         "--data", json.dumps(chain_data)],
        check=False,
    )

    # Drop individual preToolUse entries by marking them dropped.
    for e in tool_entries:
        subprocess.run(
            ["python3.12", MEMORY_PY, "update",
             "--id", e["id"],
             "--field", "stage",
             "--value", "dropped"],
            check=False,
        )


if __name__ == "__main__":
    main()
