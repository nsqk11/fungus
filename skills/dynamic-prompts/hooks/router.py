#!/usr/bin/env python3
# @hook userPromptSubmit
# @priority 10
# @description Route hook events to matching handlers and inject dynamic prompts.
"""Hook event router + dynamic prompt injection.

Receives hook payloads from the agent platform via stdin, then:
1. For userPromptSubmit: analyze intent and inject relevant context
2. For all events: dispatch to matching handler scripts across skills

Each handler script declares its hook binding via annotations in the
first 15 lines:

    # @hook <event-name>[,<event-name>...]   required
    # @priority <integer>                    required (lower runs first)
    # @description <text>                    required
"""

import json
import os
import subprocess
import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parent.parent
_SKILLS_ROOT = _SKILL_DIR.parent

_REQUIRED_ANNOTATIONS = frozenset({"hook", "priority", "description"})
_ANNOTATION_SCAN_LINES = 15


def _parse_hook_name(payload: str) -> str:
    try:
        return json.loads(payload).get("hook_event_name", "")
    except (json.JSONDecodeError, AttributeError):
        return ""


def _parse_annotations(path: Path) -> dict[str, str] | None:
    annotations: dict[str, str] = {}
    with path.open() as f:
        for _, line in zip(range(_ANNOTATION_SCAN_LINES), f):
            stripped = line.strip()
            if stripped.startswith("# @"):
                key, _, value = stripped[3:].partition(" ")
                annotations[key] = value.strip()
    if _REQUIRED_ANNOTATIONS <= annotations.keys():
        return annotations
    return None


def _matches_hook(annotation: str, hook: str) -> bool:
    return annotation == "*" or hook in annotation.split(",")


def _discover_scripts() -> list[Path]:
    scripts: list[Path] = []
    if _SKILLS_ROOT.is_dir():
        for p in _SKILLS_ROOT.glob("**/hooks/*.py"):
            if not p.name.startswith("_") and p.resolve() != Path(__file__).resolve():
                scripts.append(p)
        for p in _SKILLS_ROOT.glob("**/hooks/*.sh"):
            if not p.name.startswith("_"):
                scripts.append(p)
    return scripts


def _resolve_handlers(hook: str) -> list[Path]:
    matches: list[tuple[int, Path]] = []
    for script in _discover_scripts():
        ann = _parse_annotations(script)
        if ann is None or not _matches_hook(ann["hook"], hook):
            continue
        try:
            priority = int(ann["priority"])
        except ValueError:
            continue
        matches.append((priority, script))
    matches.sort(key=lambda m: m[0])
    return [path for _, path in matches]


def _execute(script: Path, payload: str) -> None:
    subprocess.run([str(script)], input=payload, text=True, check=False)


def main() -> None:
    if sys.stdin.isatty():
        return
    payload = sys.stdin.read()
    if not payload:
        return

    os.environ["FUNGUS_ROOT"] = str(_SKILLS_ROOT)

    hook = _parse_hook_name(payload)
    if not hook:
        return

    for script in _resolve_handlers(hook):
        _execute(script, payload)


if __name__ == "__main__":
    main()
