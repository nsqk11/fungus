"""Shared helpers for hooks/memory/*.py.

Router skips files starting with underscore, so this module is
import-only (not dispatched as a hook).

Reads FUNGUS_ROOT from the environment (set by router.py).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

FUNGUS_ROOT = Path(os.environ["FUNGUS_ROOT"])
DATA_DIR = FUNGUS_ROOT / "data"

NOISE_TOOLS = frozenset({"fs_read", "grep", "glob"})
MIN_PROMPT_LEN = 5


def read_payload() -> dict:
    """Return parsed hook payload, or empty dict on failure."""
    if sys.stdin.isatty():
        return {}
    raw = sys.stdin.read()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def new_turn_file() -> Path:
    """Create a new turn file keyed by nanosecond timestamp."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"turn-{time.time_ns()}.txt"


def latest_turn_file() -> Path | None:
    """Return the most recent turn file (lexicographic max), or None."""
    turns = sorted(DATA_DIR.glob("turn-*.txt"))
    return turns[-1] if turns else None
