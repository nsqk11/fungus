#!/usr/bin/env python3.12
# @hook stop
# @priority 40
# @skill memory-curation
# @description Export parsed and longterm entries to data/memory.md
#   for knowledge base indexing.

import json
import subprocess
from pathlib import Path

MEMORY_PY = str(Path(__file__).resolve().parent / "memory.py")
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.md"
EXPORT_STAGES = ("parsed", "longterm")


def _list_stage(stage: str) -> list[dict]:
    result = subprocess.run(
        ["python3.12", MEMORY_PY, "list", "--stage", stage],
        capture_output=True, text=True, check=False,
    )
    return [json.loads(line) for line in result.stdout.splitlines() if line]


def _entry_md(e: dict) -> str:
    lines = [f"## {e.get('summary') or e['id']}"]
    meta = [f"Stage: {e['stage']}", f"Date: {e['timestamp']}"]
    if e.get("keywords"):
        meta.append(f"Tags: {', '.join(e['keywords'])}")
    if e.get("category"):
        meta.append(f"Category: {e['category']}")
    lines.append(" | ".join(meta))
    lines.append("")

    data = e.get("data") or {}
    if data.get("prompt"):
        lines.append(f"> {data['prompt']}")
        lines.append("")
    if data.get("assistant_response"):
        lines.append(data["assistant_response"])
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    entries: list[dict] = []
    for stage in EXPORT_STAGES:
        entries.extend(_list_stage(stage))
    entries.sort(key=lambda e: e["timestamp"])

    sections = ["# Fungus Memory", ""]
    sections.extend(_entry_md(e) for e in entries)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(sections), encoding="utf-8")


if __name__ == "__main__":
    main()
