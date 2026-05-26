#!/usr/bin/env python3
"""Batch extraction: loops through all unprocessed sessions."""

import fcntl
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parent.parent
_LOCK_FILE = Path.home() / ".kiro" / ".extract.lock"
_SESSIONS_DIR = Path.home() / ".kiro" / "sessions" / "cli"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory import get_conn, finish_session

EXTRACTORS = ("skill-extractor", "kb-extractor", "rule-extractor")


def find_unprocessed_sessions():
    conn = get_conn()
    finished = {r[0] for r in conn.execute(
        "SELECT session_id FROM processed_sessions WHERE finished_at IS NOT NULL"
    ).fetchall()}
    conn.close()
    locked = {p.stem for p in _SESSIONS_DIR.glob("*.lock")}
    unprocessed = []
    for jsonl in _SESSIONS_DIR.glob("*.jsonl"):
        sid = jsonl.stem
        if sid not in finished and sid not in locked:
            unprocessed.append(sid)
    return unprocessed


def main():
    lock_fd = open(_LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("ERROR: lock held by another process")
        sys.exit(1)

    try:
        unprocessed = find_unprocessed_sessions()
        total = len(unprocessed)
        print(f"Sessions to process: {total}")

        for i, sid in enumerate(unprocessed, 1):
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{i}/{total}] {ts} {sid}", flush=True)

            conn = get_conn()
            conn.execute(
                "INSERT OR IGNORE INTO processed_sessions (session_id, started_at) VALUES (?, ?)",
                (sid, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            conn.close()

            session_file = _SESSIONS_DIR / f"{sid}.jsonl"
            prompt = (
                f"Session ID: {sid}\n"
                f"Session file: {session_file}\n"
                f"Save command: {_SKILL_DIR}/scripts/memory.py save <extractor-name> '<json>' {sid}"
            )

            procs = []
            t0 = time.time()
            for agent in EXTRACTORS:
                p = subprocess.Popen(
                    ["kiro-cli", "chat", "--agent", agent, "--no-interactive",
                     "--trust-all-tools", prompt],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                procs.append(p)

            deadline = t0 + 300
            timeout = False
            for p in procs:
                remaining = deadline - time.time()
                if remaining <= 0 or timeout:
                    timeout = True
                    p.kill()
                else:
                    try:
                        p.wait(timeout=remaining)
                    except subprocess.TimeoutExpired:
                        timeout = True
                        p.kill()

            if timeout:
                for p in procs:
                    p.kill()
                    p.wait()
                conn = get_conn()
                conn.execute("DELETE FROM processed_sessions WHERE session_id = ?", (sid,))
                conn.commit()
                conn.close()
                unprocessed.append(sid)
                total += 1
                print(f"  ✗ timeout, moved to end ({int(time.time()-t0)}s)", flush=True)
            else:
                finish_session(sid, 0)
                print(f"  ✓ done ({int(time.time()-t0)}s)", flush=True)

        print(f"---\nAll {total} sessions processed.")
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
