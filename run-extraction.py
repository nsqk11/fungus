#!/usr/bin/env python3
"""Cron-triggered extraction scheduler.

Checks for unprocessed sessions, acquires a lock, launches 3 extractor
agents in parallel, waits for completion, then releases the lock.

Usage: run from cron every N minutes.
"""

import fcntl
import subprocess
import sys
from pathlib import Path

_PROP_DIR = Path(__file__).resolve().parent
_LOCK_FILE = _PROP_DIR / "extract.lock"
_SESSIONS_DIR = Path.home() / ".kiro" / "sessions" / "cli"

sys.path.insert(0, str(_PROP_DIR))

EXTRACTORS = ("skill-extractor", "kb-extractor", "rule-extractor")


def find_unprocessed_sessions():
    """Find sessions not yet in DB as finished."""
    from _memory import get_conn

    conn = get_conn()
    finished = {r[0] for r in conn.execute(
        "SELECT session_id FROM processed_sessions WHERE finished_at IS NOT NULL"
    ).fetchall()}
    conn.close()

    current_lock = _SESSIONS_DIR / "*.lock"
    locked = {p.stem for p in _SESSIONS_DIR.glob("*.lock")}

    unprocessed = []
    for jsonl in _SESSIONS_DIR.glob("*.jsonl"):
        sid = jsonl.stem
        if sid in finished or sid in locked:
            continue
        unprocessed.append(sid)
    return unprocessed


def main() -> None:
    # Try to acquire lock (non-blocking)
    lock_fd = open(_LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        # Another instance is running
        lock_fd.close()
        return

    try:
        unprocessed = find_unprocessed_sessions()
        if not unprocessed:
            return

        # Process one session per run
        sid = unprocessed[0]

        # Mark as processing so next cron won't pick it up
        from _memory import get_conn, finish_session
        conn = get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO processed_sessions (session_id, started_at) VALUES (?, ?)",
            (sid, __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

        # Launch 3 extractors in parallel for this session
        session_file = _SESSIONS_DIR / f"{sid}.jsonl"
        prompt = (
            f"Session ID: {sid}\n"
            f"Session file: {session_file}\n"
            f"Save command: {_PROP_DIR}/_memory.py save <extractor-name> '<json>' {sid}"
        )
        procs = []
        for agent in EXTRACTORS:
            p = subprocess.Popen(
                ["kiro-cli", "chat", "--agent", agent, "--no-interactive",
                 "--trust-all-tools", prompt],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            procs.append(p)

        # Wait for all to finish
        for p in procs:
            p.wait()

        # Mark session as finished
        finish_session(sid, 0)

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
