#!/usr/bin/env python3.12
"""Router — route hook events to skill scripts and global hooks.

Reads hook payload from stdin, extracts `hook_event_name`, then scans
`skills/*/scripts/*.{sh,py}` and `hooks/*.{sh,py}` for matching
`@hook` annotations and executes them in priority order. Each script
receives the original stdin payload unchanged, plus `FUNGUS_ROOT`
in its environment pointing at the repo/install root.

Usage:
  Kiro invokes this as the registered hook handler. Not called directly.

Annotations (first 15 lines of each script):
  # @hook <event-name>       required
  # @priority <integer>      required, lower runs first
  # @skill <name>            required for skill scripts, optional for hooks/
  # @description <text>      required
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / "hooks"
SKILLS_DIR = REPO_ROOT / "skills"
_REQUIRED_KEYS = frozenset({"hook", "priority", "description"})
_MAX_SCAN_LINES = 15


def _read_hook_name(payload: str) -> str:
    """Extract hook_event_name from JSON payload. Empty on failure."""
    try:
        return json.loads(payload).get("hook_event_name", "")
    except json.JSONDecodeError:
        return ""


def _parse_annotations(path: Path) -> dict[str, str] | None:
    """Return annotations dict if all required keys are present."""
    annotations: dict[str, str] = {}
    with path.open() as f:
        for _, line in zip(range(_MAX_SCAN_LINES), f):
            stripped = line.strip()
            if stripped.startswith("# @"):
                key, _, value = stripped[3:].partition(" ")
                annotations[key] = value.strip()
    return annotations if _REQUIRED_KEYS <= annotations.keys() else None


def _iter_scripts() -> list[Path]:
    """Yield candidate scripts from hooks/, hooks/*/, and skills/*/scripts/."""
    scripts: list[Path] = []
    if HOOKS_DIR.is_dir():
        # Top-level hooks (router.py excluded).
        for p in HOOKS_DIR.iterdir():
            if p.is_file() and p.suffix in (".py", ".sh") \
                    and not p.name.startswith("_"):
                if p.name != "router.py":
                    scripts.append(p)
        # One level of grouped hooks: hooks/<group>/*.{py,sh}
        for p in HOOKS_DIR.glob("*/*"):
            if p.suffix in (".py", ".sh") and not p.name.startswith("_"):
                scripts.append(p)
    if SKILLS_DIR.is_dir():
        for p in SKILLS_DIR.glob("*/scripts/*"):
            if p.suffix in (".py", ".sh") and not p.name.startswith("_"):
                scripts.append(p)
    return scripts


def _resolve(hook: str) -> list[tuple[Path, str]]:
    """Return (script_path, label) pairs matching hook, sorted by priority."""
    matches: list[tuple[int, Path, str]] = []
    for script in _iter_scripts():
        ann = _parse_annotations(script)
        if ann is None or ann["hook"] != hook:
            continue
        try:
            priority = int(ann["priority"])
        except ValueError:
            continue
        label = ann.get("skill", "hooks")
        matches.append((priority, script, label))

    matches.sort(key=lambda m: m[0])
    return [(path, label) for _, path, label in matches]


def _run(script: Path, payload: str) -> None:
    """Forward payload to script via stdin."""
    runner = "python3.12" if script.suffix == ".py" else "bash"
    # Label for diagnostics:
    #   skills/<name>/scripts/x.py  -> <name>
    #   hooks/<group>/x.py          -> <group>
    #   hooks/x.py                  -> hooks
    if script.parent.name == "scripts":
        label = script.parent.parent.name
    elif script.parent.parent == HOOKS_DIR:
        label = script.parent.name
    else:
        label = "hooks"
    print(f"[router] → {script.name} ({label})", file=sys.stderr)
    subprocess.run([runner, str(script)], input=payload, text=True, check=False)


def main() -> None:
    if sys.stdin.isatty():
        return
    payload = sys.stdin.read()
    if not payload:
        return

    os.environ["FUNGUS_ROOT"] = str(REPO_ROOT)

    hook = _read_hook_name(payload)
    if not hook:
        return

    for script, _label in _resolve(hook):
        _run(script, payload)


if __name__ == "__main__":
    main()
