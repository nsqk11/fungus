#!/usr/bin/env python3
# @hook preToolUse
# @priority 30
# @description Warn when about to read or write a large file.
"""Detect large file operations and suggest chunked processing."""

import json
import os
import sys
from pathlib import Path

_SIZE_THRESHOLD = 100_000  # 100KB


def main() -> None:
    if sys.stdin.isatty():
        return
    payload = json.loads(sys.stdin.read())

    data = payload.get("data", {})
    tool_input = data.get("tool_input", {})

    # Check for file path in common tool input fields
    file_path = (
        tool_input.get("path", "")
        or tool_input.get("file_path", "")
        or tool_input.get("command", "")
    )

    if not file_path or not isinstance(file_path, str):
        return

    # Try to resolve and check size
    p = Path(file_path).expanduser()
    if p.is_file() and p.stat().st_size > _SIZE_THRESHOLD:
        size_kb = p.stat().st_size // 1024
        print(
            "<large-file-warning>\n"
            f"Target file is {size_kb}KB. Consider reading in chunks "
            "using offset/limit to avoid context overflow.\n"
            "</large-file-warning>"
        )


if __name__ == "__main__":
    main()
