"""Shared helpers for hooks/memory/*.py.

Router skips files starting with underscore, so this module is
import-only (not dispatched as a hook).

Reads FUNGUS_ROOT from the environment (set by router.py).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

FUNGUS_ROOT = Path(os.environ["FUNGUS_ROOT"])
TURN_FILE = FUNGUS_ROOT / "data" / "current-turn.txt"

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


def ensure_data_dir() -> None:
    TURN_FILE.parent.mkdir(parents=True, exist_ok=True)
