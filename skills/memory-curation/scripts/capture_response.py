#!/usr/bin/env python3.12
# @hook stop
# @priority 10
# @skill memory-curation
# @description Finalize the pending entry: merge response, promote to raw.

import json
import sqlite3

from _common import DB_PATH, get_pending_entry, read_payload


def main() -> None:
    payload = read_payload()
    pending = get_pending_entry()
    if not pending:
        return
    entry_id, data = pending
    data["response"] = payload.get("assistant_response", "")
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "UPDATE memory SET stage = 'raw', data = ? WHERE id = ?",
        (json.dumps(data, ensure_ascii=False), entry_id),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
