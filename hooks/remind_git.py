#!/usr/bin/env python3
# @hook userPromptSubmit
# @priority 40
# @description Inject current git context (branch, dirty state).
"""Emit git context if inside a git repository."""

import subprocess


def main() -> None:
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return

    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()

    status = "dirty" if dirty else "clean"
    print(f"<git-context>branch: {branch} | status: {status}</git-context>")


if __name__ == "__main__":
    main()
