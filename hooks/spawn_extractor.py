#!/usr/bin/env python3
# @hook stop
# @priority 10
# @description Spawn a background agent to extract memories from pending turns.
"""Spawn kiro-cli to process unprocessed turns via LLM extraction."""

import os
import subprocess
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
_ROOT = Path(os.environ.get("FUNGUS_ROOT", _HOOKS_DIR.parent))
_CRITERIA_PATH = _ROOT / "prompts" / "extract-criteria.md"
_EXTRACT_CLI = _HOOKS_DIR / "extract_cli.py"


def main() -> None:
    if not _CRITERIA_PATH.is_file():
        return

    criteria = _CRITERIA_PATH.read_text(encoding="utf-8")
    prompt = f"""{criteria}

---

## Interface

Do NOT read or write files. Use the CLI tool at `{_EXTRACT_CLI}`:

```bash
{_EXTRACT_CLI} list
{_EXTRACT_CLI} keep '<json_array>' <prompt_event_id>
{_EXTRACT_CLI} drop <prompt_event_id>
```

The `keep` command takes a JSON array as the first argument and the prompt event ID as the second.
Example:

```bash
{_EXTRACT_CLI} keep '[{{"category":"semantic","summary":"...","detail":"...","tags":"tag1, tag2"}}]' 1234567890
```

Run `list` first, then for each turn decide keep or drop per the criteria above.
If a turn yields nothing across all 9 directions, use `drop`.
"""

    subprocess.Popen(
        ["kiro-cli", "chat", "--no-interactive", "--trust-all-tools", prompt],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


if __name__ == "__main__":
    main()
