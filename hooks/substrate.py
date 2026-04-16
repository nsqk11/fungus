#!/usr/bin/env python3.12
"""Substrate core — scan module scripts, match hook, enforce permissions, output execution order.

Usage: substrate.py <hook-name> <repo-root>
Output: one line per script: <path>|<module>  (sorted by priority ascending)
"""

import sys
from pathlib import Path

# Annotations scanned from script file headers.
_REQUIRED = frozenset({"hook", "priority", "module", "description"})
_MAX_SCAN_LINES = 15


def _parse_annotations(path: Path) -> dict[str, str] | None:
    """Extract @-annotations from the first lines of a script."""
    annotations: dict[str, str] = {}
    with path.open() as f:
        for _, line in zip(range(_MAX_SCAN_LINES), f):
            line = line.strip()
            if line.startswith("# @"):
                key, _, value = line[3:].partition(" ")
                annotations[key] = value.strip()
    return annotations if _REQUIRED <= annotations.keys() else None


def _resolve(hook: str, repo_root: Path) -> list[tuple[str, str, int]]:
    """Return matching scripts as (path, module, priority) sorted by priority."""
    modules_dir = repo_root / "modules"
    if not modules_dir.is_dir():
        return []

    matches: list[tuple[str, str, int]] = []
    for script in modules_dir.rglob("*.py"):
        ann = _parse_annotations(script)
        if ann is None or ann["hook"] != hook:
            continue
        try:
            priority = int(ann["priority"])
        except ValueError:
            continue
        matches.append((str(script), ann["module"], priority))

    matches.sort(key=lambda x: x[2])
    return matches


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <hook-name> <repo-root>", file=sys.stderr)
        sys.exit(1)

    hook, repo_root = sys.argv[1], Path(sys.argv[2])
    for path, module, _ in _resolve(hook, repo_root):
        print(f"{path}|{module}")


if __name__ == "__main__":
    main()
