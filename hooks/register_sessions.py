#!/usr/bin/env python3
# @hook agentSpawn
# @priority 80
# @description Register untracked ended sessions to DB for later processing.
"""At agent spawn, scan sessions dir and register any unknown ended sessions."""

import os
import sys
from pathlib import Path

_ROOT = Path(os.environ.get("FUNGUS_ROOT", Path(__file__).resolve().parent.parent))
_HOOKS_DIR = _ROOT / "hooks"
_SESSIONS_DIR = Path.home() / ".kiro" / "sessions" / "cli"
_CURRENT_SESSION = os.environ.get("KIRO_SESSION_ID", "")

sys.path.insert(0, str(_HOOKS_DIR))


def main() -> None:
    from _memory import is_processed, register_session

    for jsonl in _SESSIONS_DIR.glob("*.jsonl"):
        sid = jsonl.stem
        if sid == _CURRENT_SESSION:
            continue
        if (jsonl.parent / f"{sid}.lock").exists():
            continue
        if is_processed(sid):
            continue
        register_session(sid)


if __name__ == "__main__":
    main()
