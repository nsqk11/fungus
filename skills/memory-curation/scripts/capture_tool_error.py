#!/usr/bin/env python3.12
# @hook postToolUse
# @priority 10
# @skill memory-curation
# @description Append tool errors to the current pending entry.

import json

from _common import get_pending_entry, read_payload, update_pending_data


def main() -> None:
    payload = read_payload()
    if payload.get("tool_response", {}).get("success") is not False:
        return
    pending = get_pending_entry()
    if not pending:
        return
    entry_id, data = pending
    error = payload.get("tool_response", {}).get("error", "unknown")
    data.setdefault("errors", []).append(error)
    update_pending_data(entry_id, data)


if __name__ == "__main__":
    main()
