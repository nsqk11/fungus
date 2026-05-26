#!/usr/bin/env python3
# @hook agentSpawn
# @priority 90
# @description Spawn batch extraction for unprocessed sessions in background.
"""Launches batch extraction as a background process to avoid blocking the hook."""

import subprocess
import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parent.parent
_LOCK_FILE = Path.home() / ".kiro" / ".extract.lock"
_SESSIONS_DIR = Path.home() / ".kiro" / "sessions" / "cli"

sys.path.insert(0, str(_SKILL_DIR / "scripts"))


def has_unprocessed():
    from memory import get_conn
    conn = get_conn()
    finished = {r[0] for r in conn.execute(
        "SELECT session_id FROM processed_sessions WHERE finished_at IS NOT NULL"
    ).fetchall()}
    conn.close()
    locked = {p.stem for p in _SESSIONS_DIR.glob("*.lock")}
    for jsonl in _SESSIONS_DIR.glob("*.jsonl"):
        if jsonl.stem not in finished and jsonl.stem not in locked:
            return True
    return False


def main() -> None:
    try:
        import fcntl
        fd = open(_LOCK_FILE, "w")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
    except BlockingIOError:
        return

    if not has_unprocessed():
        return

    script = _SKILL_DIR / "scripts" / "extract.py"
    subprocess.Popen(
        [sys.executable, str(script)],
        stdout=open(Path.home() / ".kiro" / ".extract.log", "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


if __name__ == "__main__":
    main()
