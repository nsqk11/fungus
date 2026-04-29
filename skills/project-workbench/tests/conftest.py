"""Pytest config: isolate each test into its own workbench directory."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make scripts/ importable.
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def workbench_dir(tmp_path, monkeypatch):
    """Point PROJECT_WORKBENCH_DIR at a fresh temp dir."""
    d = tmp_path / "workbenches"
    d.mkdir()
    monkeypatch.setenv("PROJECT_WORKBENCH_DIR", str(d))
    return d
