"""Schema definitions for project-workbench JSON files.

Each workbench is a single JSON document with a fixed set of top-level
keys. This module owns the canonical default shape, the allowed status
values, and the ID validation rule.

Filename starts with an underscore so the hook router skips it during
dispatch; it is an import-only module.
"""
from __future__ import annotations

import re
from typing import Any

# Allowed characters in a workbench ID. Excludes slashes and whitespace
# to prevent path-injection tricks like ``../foo``.
ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
ID_MAX_LEN = 64

VALID_STATUSES = ("active", "paused", "done", "archived")

# Section names that hold arrays of records in a workbench.
ARRAY_SECTIONS = (
    "deliverables",
    "references",
    "milestones",
    "changeLog",
    "reviews",
    "notes",
)


def default_workbench(workbench_id: str, name: str, type_: str = "") -> dict[str, Any]:
    """Return a fresh workbench dict with all sections empty.

    ``createdAt`` / ``updatedAt`` are left blank here; ``_store.save``
    fills them on write so that all time handling lives in one place.
    """
    return {
        "id": workbench_id,
        "name": name,
        "type": type_,
        "status": "active",
        "createdAt": "",
        "updatedAt": "",
        "deliverables": [],
        "references": [],
        "milestones": [],
        "changeLog": [],
        "reviews": [],
        "notes": [],
    }


def is_valid_id(workbench_id: str) -> bool:
    """Return True if ``workbench_id`` is safe to use as a filename."""
    if not workbench_id or len(workbench_id) > ID_MAX_LEN:
        return False
    if not ID_PATTERN.match(workbench_id):
        return False
    # Reject leading dots and consecutive dots to avoid paths like
    # ``..`` or ``.hidden`` that look like directory tricks even
    # though they would land in the workbench directory as files.
    if workbench_id.startswith(".") or ".." in workbench_id:
        return False
    return True


def is_valid_status(status: str) -> bool:
    return status in VALID_STATUSES
