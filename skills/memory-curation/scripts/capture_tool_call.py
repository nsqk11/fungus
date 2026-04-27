#!/usr/bin/env python3.12
# @hook preToolUse
# @priority 10
# @skill memory-curation
# @description Append tool name to the current pending entry.

from _common import get_pending_entry, read_payload, update_pending_data

SKIP_TOOLS = frozenset({"fs_read", "fs_write", "grep", "glob",
                        "code", "todo_list"})


def main() -> None:
    payload = read_payload()
    tool = payload.get("tool_name", "")
    if not tool or tool in SKIP_TOOLS:
        return
    pending = get_pending_entry()
    if not pending:
        return
    entry_id, data = pending
    data.setdefault("tools", []).append(tool)
    update_pending_data(entry_id, data)


if __name__ == "__main__":
    main()
