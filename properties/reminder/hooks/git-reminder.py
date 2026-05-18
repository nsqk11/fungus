#!/usr/bin/env python3
# @hook preToolUse
# @priority 20
# @description Inject git reminders when agent is about to use git.
"""Detect git-related tool calls and inject appropriate reminders."""

import json
import sys

_PUSH_KEYWORDS = ("push", "publish", "deploy")
_EXTERNAL_HOSTS = ("github", "gitlab", "bitbucket", "npm", "pypi")


def main() -> None:
    if sys.stdin.isatty():
        return
    payload = json.loads(sys.stdin.read())

    # Extract tool name and arguments from payload
    data = payload.get("data", {})
    tool_name = data.get("tool_name", "").lower()
    tool_input = json.dumps(data.get("tool_input", {})).lower()

    # Check if this is a git-related tool call
    is_git = "git" in tool_name or "git" in tool_input

    if not is_git:
        return

    # Check for push to external
    is_push = any(k in tool_input for k in _PUSH_KEYWORDS)
    is_external = any(h in tool_input for h in _EXTERNAL_HOSTS)

    # If pushing without explicit host, resolve the remote URL
    if is_push and not is_external:
        import subprocess
        try:
            url = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                stderr=subprocess.DEVNULL, text=True
            ).lower()
            is_external = any(h in url for h in _EXTERNAL_HOSTS)
        except Exception:
            pass

    if is_push and is_external:
        print(
            "<git-push-warning>\n"
            "Before pushing to an external remote, check the repo for "
            "sensitive information (.env, credentials, tokens, private keys).\n"
            "</git-push-warning>"
        )
    else:
        print(
            "<git-reminder>\n"
            "Run `git status` and `git branch` to understand the current "
            "repo state before proceeding.\n"
            "</git-reminder>"
        )


if __name__ == "__main__":
    main()
