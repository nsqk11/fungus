"""Shared pytest fixtures for the atlassian-api skill.

Pytest is run from the skill directory; this file inserts scripts/ into
sys.path so that tests can ``import auth``, ``import urls``, etc. without
installing the skill as a Python package.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make sibling ``scripts/`` importable for all tests.
_SKILL_DIR = Path(__file__).resolve().parent.parent
_SCRIPTS = _SKILL_DIR / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import pytest  # noqa: E402


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Point the auth/confluence modules at a per-test SQLite file."""
    db = tmp_path / "store.db"
    monkeypatch.setenv("ATLASSIAN_API_DB", str(db))
    return db
