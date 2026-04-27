"""Shared utilities for memory-curation hook scripts.

Router skips files starting with underscore, so this module is
import-only (not dispatched as a hook).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = SKILL_ROOT / "data" / "memory.db"


def read_payload() -> dict:
    """Read and parse hook stdin JSON. Returns {} on failure."""
    if sys.stdin.isatty():
        return {}
    raw = sys.stdin.read()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def emit_reminder(body: str) -> None:
    """Print a memory-curation-reminder tag to stdout.

    Host agent includes stdout from hook scripts as context entries.
    """
    print(f"<memory-curation-reminder>\n{body}\n</memory-curation-reminder>")
