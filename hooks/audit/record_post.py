#!/usr/bin/env python3.12
# @hook postToolUse
# @priority 20
# @description Write the final audit row for this tool call.

"""Consumes the pending record written by ``record_pre.py``, computes
``duration_ms``, and inserts a row into ``audit.db``.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _db  # noqa: E402


def _read_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read()
    except OSError:
        return {}
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    # strptime with explicit Z handling
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def _duration_ms(started_at: str | None) -> int | None:
    start = _parse_iso(started_at or "")
    if start is None:
        return None
    now_str = _db.now_iso()
    end = _parse_iso(now_str)
    if end is None:
        return None
    delta = end - start
    return int(delta.total_seconds() * 1000)


def _find_pending_for_tool(turn_id: str, tool: str) -> dict | None:
    """Find the oldest pending record matching (turn_id, tool).

    Pre and post hooks run in separate subprocesses with different
    pids, so we cannot match by pid. Instead we scan all pending
    files and pick the one whose payload matches the current turn
    and tool. If multiple match (nested or concurrent calls to the
    same tool in the same turn), take the one with the smallest
    seq — pre hooks are invoked in order, so the oldest unprocessed
    entry corresponds to the earliest call.
    """
    d = _db.pending_dir()
    if not d.is_dir():
        return None
    best: tuple[tuple[int, int], Path, dict] | None = None
    for path in d.glob("pending-*-*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("tool") != tool:
            continue
        # Match by turn_id when both sides know it; fall back to
        # tool-only match when either side lacks a turn id (e.g.
        # the very first pre-hook before set_turn.py has run).
        data_turn = data.get("turn_id") or ""
        if turn_id and data_turn and data_turn != turn_id:
            continue
        stem_parts = path.stem.rsplit("-", 2)
        try:
            pid = int(stem_parts[-2])
            seq = int(stem_parts[-1])
        except (ValueError, IndexError):
            continue
        key = (seq, pid)
        if best is None or key < best[0]:
            best = (key, path, data)
    if best is None:
        return None
    try:
        best[1].unlink()
    except OSError:
        pass
    return best[2]


def main() -> None:
    payload = _read_payload()
    tool = payload.get("tool_name", "")
    if not tool:
        return

    response = payload.get("tool_response") or {}
    success = response.get("success") is not False
    error = "" if success else str(response.get("error", ""))

    turn_id = _db.read_turn_id()
    started_at: str | None = None
    input_summary = _db.summarize_input(payload.get("tool_input"))
    duration_ms: int | None = None

    match = _find_pending_for_tool(turn_id, tool)
    if match is not None:
        data = match
        started_at = data.get("started_at")
        duration_ms = _duration_ms(started_at)
        if not input_summary:
            input_summary = data.get("input_summary", "")
        # Prefer the turn_id the pre hook saw, in case it rotated mid-call
        turn_id = data.get("turn_id") or turn_id

    _db.insert_record(
        turn_id=turn_id,
        tool=tool,
        success=success,
        error=error,
        duration_ms=duration_ms,
        input_summary=input_summary,
        started_at=started_at,
    )


if __name__ == "__main__":
    main()
