#!/usr/bin/env python3
"""Hook event router for the Fungus agent.

Receives hook payloads from Kiro via stdin, then dispatches to
matching handler scripts sorted by priority.

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

_ROOT = Path(__file__).resolve().parent.parent
_HOOKS_DIR = _ROOT / "hooks"
_PROPERTIES_DIR = _ROOT / "properties"

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
    if _HOOKS_DIR.is_dir():
        for p in _HOOKS_DIR.iterdir():
            if (p.is_file() and p.suffix in (".py", ".sh")
                    and not p.name.startswith("_")
                    and p.name != Path(__file__).name):
                scripts.append(p)
        for p in _HOOKS_DIR.glob("*/*"):
            if p.suffix in (".py", ".sh") and not p.name.startswith("_"):
                scripts.append(p)
    if _PROPERTIES_DIR.is_dir():
        for p in _PROPERTIES_DIR.glob("*/hooks/*"):
            if p.suffix in (".py", ".sh") and not p.name.startswith("_"):
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

    os.environ["FUNGUS_ROOT"] = str(_ROOT)

    hook = _parse_hook_name(payload)
    if not hook:
        return

    for script in _resolve_handlers(hook):
        _execute(script, payload)


if __name__ == "__main__":
    main()
