#!/usr/bin/env python3
# @hook userPromptSubmit,preToolUse,postToolUse
# @priority 10
# @description Dynamic context injection based on regex rules.
"""Reads hook payload, matches against rules.json, injects context."""

import json
import re
import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parent.parent
_RULES_FILE = _SKILL_DIR / "rules.json"


def _load_rules() -> list[dict]:
    if not _RULES_FILE.exists():
        return []
    try:
        with _RULES_FILE.open() as f:
            rules = json.load(f)
        return rules if isinstance(rules, list) else []
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARNING: {_RULES_FILE}: {e}", file=sys.stderr)
        return []


def _extract_content(payload: dict) -> str:
    data = payload.get("data", {})
    if isinstance(data, dict):
        return data.get("content", "")
    return str(data)


def main() -> None:
    if sys.stdin.isatty():
        return
    raw = sys.stdin.read()
    if not raw:
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return

    event = payload.get("hook_event_name", "")
    if not event:
        return

    content = _extract_content(payload)
    if not content:
        return

    rules = _load_rules()
    matched = []

    for rule in rules:
        events = rule.get("event", [])
        if isinstance(events, str):
            events = [events]
        if event not in events:
            continue

        pattern = rule.get("pattern", "")
        if not pattern:
            continue

        try:
            if not re.search(pattern, content, re.IGNORECASE):
                continue
        except re.error as e:
            print(f"WARNING: bad regex {pattern!r}: {e}", file=sys.stderr)
            continue

        priority = rule.get("priority", 50)
        matched.append((priority, rule.get("context", "")))

    if not matched:
        return

    matched.sort(key=lambda x: x[0])
    combined = "\n\n".join(ctx for _, ctx in matched if ctx)

    if combined:
        print(json.dumps({"type": "context", "context": combined}))


if __name__ == "__main__":
    main()
