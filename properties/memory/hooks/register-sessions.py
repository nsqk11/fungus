#!/usr/bin/env python3
# @hook agentSpawn
# @priority 80
# @description Register untracked ended sessions to DB for later processing.
"""At agent spawn, scan sessions dir and register any unknown ended sessions."""

import os
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
_PROP_DIR = _HOOKS_DIR.parent
_ROOT = Path(os.environ.get("FUNGUS_ROOT", _PROP_DIR.parent.parent))
_SESSIONS_DIR = Path.home() / ".kiro" / "sessions" / "cli"
_CURRENT_SESSION = os.environ.get("KIRO_SESSION_ID", "")

sys.path.insert(0, str(_PROP_DIR))


def main() -> None:
    from _memory import get_conn, register_session

    conn = get_conn()
    known = {r[0] for r in conn.execute("SELECT session_id FROM processed_sessions").fetchall()}
    conn.close()

    for jsonl in _SESSIONS_DIR.glob("*.jsonl"):
        sid = jsonl.stem
        if sid == _CURRENT_SESSION:
            continue
        if (jsonl.parent / f"{sid}.lock").exists():
            continue
        if sid in known:
            continue
        register_session(sid)


if __name__ == "__main__":
    main()
