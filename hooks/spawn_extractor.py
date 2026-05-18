#!/usr/bin/env python3
# @hook stop
# @priority 90
# @description Spawn worker agents to extract memories from unprocessed sessions.
"""On stop, find unprocessed sessions from DB and spawn extraction workers."""

import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(os.environ.get("FUNGUS_ROOT", Path(__file__).resolve().parent.parent))
_HOOKS_DIR = _ROOT / "hooks"
_CRITERIA_PATH = _ROOT / "prompts" / "extract-criteria.md"
_MEMORY_PY = _HOOKS_DIR / "_memory.py"

_SESSIONS_DIR = Path.home() / ".kiro" / "sessions" / "cli"
_MAX_WORKERS = 2

sys.path.insert(0, str(_HOOKS_DIR))


def main() -> None:
    from _memory import claim_session, find_unprocessed

    candidates = find_unprocessed()
    if not candidates or not _CRITERIA_PATH.is_file():
        return

    criteria = _CRITERIA_PATH.read_text(encoding="utf-8")
    claimed = []
    for sid in candidates:
        if claim_session(sid):
            claimed.append(sid)
        if len(claimed) >= _MAX_WORKERS:
            break

    for sid in claimed:
        jsonl_path = _SESSIONS_DIR / f"{sid}.jsonl"
        if not jsonl_path.exists():
            continue
        prompt = f"""{criteria}

---

## Your Task

Process the session file at: `{jsonl_path}`

The file is a JSONL (one JSON object per line). Each line has:
- `kind`: "Prompt" (user message), "AssistantMessage" (agent reply), or "ToolResults"
- `data.content`: the actual content

Focus on "Prompt" lines (user messages) and "AssistantMessage" lines (agent responses).
Skip "ToolResults" lines unless they contain important context.

Read the file (you may need to read in chunks using offset/limit), then for each
meaningful turn (user prompt + agent response pair), extract memories per the criteria above.

When you have extracted memories, save them by running:

```bash
{_MEMORY_PY} save '<json_array>'
```

Where `<json_array>` is a JSON array of memory objects.

After processing ALL turns in the file, mark the session as finished:

```bash
{_MEMORY_PY} finish '{sid}' <total_memory_count>
```

If the session has nothing worth extracting, still mark it finished with count 0.
"""
        subprocess.Popen(
            ["kiro-cli", "chat", "--no-interactive", "--trust-all-tools", prompt],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


if __name__ == "__main__":
    main()
