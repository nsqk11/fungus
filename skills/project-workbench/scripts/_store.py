"""Storage helpers for project-workbench.

Owns:

- Data directory resolution (``PROJECT_WORKBENCH_DIR`` env var, fallback
  via ``FUNGUS_ROOT``, fallback via the script's own location).
- Atomic JSON read/write with ``os.replace``.
- Workbench ID resolution (exact match, then unique prefix match).

Filename starts with an underscore so the hook router skips it.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _schema import default_workbench, is_valid_id


class StoreError(Exception):
    """Raised for user-visible store errors (invalid id, not found, …)."""


# --- Paths ---------------------------------------------------------------


def data_dir() -> Path:
    """Return the directory that holds one JSON file per workbench.

    Resolution order:

    1. ``PROJECT_WORKBENCH_DIR`` environment variable (absolute path to
       the workbench directory itself).
    2. ``FUNGUS_ROOT`` environment variable — the directory below is
       ``skills/project-workbench/data/workbenches``.
    3. Fallback: walk up from this file; use
       ``<skill-dir>/data/workbenches``.
    """
    override = os.environ.get("PROJECT_WORKBENCH_DIR")
    if override:
        return Path(override)
    fungus_root = os.environ.get("FUNGUS_ROOT")
    if fungus_root:
        return (
            Path(fungus_root)
            / "skills"
            / "project-workbench"
            / "data"
            / "workbenches"
        )
    # Script lives at <skill-dir>/scripts/_store.py, so two parents up is
    # the skill directory.
    skill_dir = Path(__file__).resolve().parent.parent
    return skill_dir / "data" / "workbenches"


def workbench_path(workbench_id: str) -> Path:
    return data_dir() / f"{workbench_id}.json"


# --- I/O -----------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(workbench_id: str) -> dict[str, Any]:
    path = workbench_path(workbench_id)
    if not path.exists():
        raise StoreError(f"workbench {workbench_id!r} not found")
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise StoreError(
            f"workbench {workbench_id!r} is not valid JSON: {exc}"
        ) from exc


def save(workbench: dict[str, Any]) -> None:
    """Atomically write ``workbench`` to its file.

    Updates ``updatedAt`` to the current UTC time. Also fills
    ``createdAt`` if empty so newly-migrated files pick up a timestamp
    on first write.
    """
    workbench_id = workbench.get("id", "")
    if not is_valid_id(workbench_id):
        raise StoreError(f"invalid workbench id: {workbench_id!r}")

    now = _now_iso()
    if not workbench.get("createdAt"):
        workbench["createdAt"] = now
    workbench["updatedAt"] = now

    path = workbench_path(workbench_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(workbench, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def create(workbench_id: str, name: str, type_: str = "") -> dict[str, Any]:
    """Create a new workbench file. Errors if one already exists."""
    if not is_valid_id(workbench_id):
        raise StoreError(
            f"invalid workbench id: {workbench_id!r} "
            "(allowed: [A-Za-z0-9._-], 1-64 chars)"
        )
    path = workbench_path(workbench_id)
    if path.exists():
        raise StoreError(f"workbench {workbench_id!r} already exists")
    workbench = default_workbench(workbench_id, name, type_)
    save(workbench)
    return workbench


# --- ID resolution -------------------------------------------------------


def list_ids() -> list[str]:
    """Return all workbench IDs in sorted order."""
    d = data_dir()
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def resolve_id(prefix: str, *, exact: bool = False) -> str:
    """Return the workbench ID matching ``prefix``.

    If ``exact`` is True, only exact matches succeed. Otherwise falls
    back to a unique prefix match and fails with ``StoreError`` on
    ambiguity or no match.
    """
    all_ids = list_ids()
    if prefix in all_ids:
        return prefix
    if exact:
        raise StoreError(f"workbench {prefix!r} not found")
    matches = [i for i in all_ids if i.startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise StoreError(
            f"workbench {prefix!r} not found. Run 'list' to see available."
        )
    raise StoreError(
        f"workbench {prefix!r} is ambiguous: {', '.join(matches)}"
    )
