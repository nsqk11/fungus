#!/usr/bin/env python3.12
# @hook preToolUse
# @priority 10
# @description Inject git workspace state before git write operations.

from __future__ import annotations

import json
import re
import subprocess
import sys

_WRITE_OPS = re.compile(
    r"\bgit\s+"
    r"(commit|push|merge|rebase|reset|checkout|switch|revert|cherry-pick"
    r"|stash|clean|tag\s+-d|branch\s+-[dD])\b"
)


def _read_command() -> str:
    """Return the bash command from preToolUse payload, or empty."""
    if sys.stdin.isatty():
        return ""
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return ""
    if payload.get("tool_name") != "execute_bash":
        return ""
    return payload.get("tool_input", {}).get("command", "")


def _git_status() -> str | None:
    """Run git status and return summary, or None if not in a repo."""
    r = subprocess.run(
        ["git", "status", "--porcelain=v2", "--branch"],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        return None
    return r.stdout


def _summarize(raw: str, command: str) -> str:
    """Build a concise workspace-reminder body from porcelain v2 output."""
    branch = "unknown"
    ahead = behind = 0
    modified = untracked = staged = 0

    for line in raw.splitlines():
        if line.startswith("# branch.head "):
            branch = line.split(" ", 2)[2]
        elif line.startswith("# branch.ab "):
            parts = line.split()
            ahead, behind = int(parts[2]), abs(int(parts[3]))
        elif line.startswith("1 ") or line.startswith("2 "):
            xy = line.split()[1]
            if xy[0] != ".":
                staged += 1
            if xy[1] != ".":
                modified += 1
        elif line.startswith("? "):
            untracked += 1

    stash = subprocess.run(
        ["git", "stash", "list"], capture_output=True, text=True, check=False,
    )
    stash_count = len(stash.stdout.splitlines()) if stash.returncode == 0 else 0

    parts = [f"branch: {branch}"]
    if ahead:
        parts.append(f"ahead {ahead}")
    if behind:
        parts.append(f"behind {behind}")
    tree = []
    if staged:
        tree.append(f"{staged} staged")
    if modified:
        tree.append(f"{modified} modified")
    if untracked:
        tree.append(f"{untracked} untracked")
    parts.append("tree: " + (", ".join(tree) if tree else "clean"))
    if stash_count:
        parts.append(f"stash: {stash_count}")
    parts.append(f"command: {command.strip()}")
    return " | ".join(parts)


def main() -> None:
    command = _read_command()
    if not command or not _WRITE_OPS.search(command):
        return
    status = _git_status()
    if status is None:
        return
    summary = _summarize(status, command)
    print(f"<fungus-reminder>\n{summary}\n</fungus-reminder>")


if __name__ == "__main__":
    main()
