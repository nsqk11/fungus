#!/usr/bin/env python3.12
"""Export nutrient and network entries to data/memory.md for KB indexing."""
import json
import os
import sqlite3

_FUNGUS_HOME = os.environ.get(
    "FUNGUS_HOME",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."),
)
_DB = os.path.join(_FUNGUS_HOME, "data", "memory.db")
_OUT = os.path.join(_FUNGUS_HOME, "data", "memory.md")


def _entry_md(r: dict) -> str:
    kw = json.loads(r["keywords"]) if isinstance(r["keywords"], str) else r["keywords"]
    data = json.loads(r["data"]) if isinstance(r["data"], str) else r["data"]

    lines = [f"## {r['summary'] or r['id']}"]
    meta = [f"Stage: {r['stage']}", f"Date: {r['timestamp']}"]
    if kw:
        meta.append(f"Tags: {', '.join(kw)}")
    if r["category"]:
        meta.append(f"Category: {r['category']}")
    lines.append(" | ".join(meta))
    lines.append("")
    if data.get("prompt"):
        lines += [f"> {data['prompt']}", ""]
    if data.get("assistant_response"):
        lines += [data["assistant_response"], ""]
    return "\n".join(lines)


def main() -> None:
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    sections = ["# Fungus Memory", ""]
    count = 0
    for stage in ("nutrient", "network"):
        for row in conn.execute(
            "SELECT * FROM memory WHERE stage = ? ORDER BY timestamp",
            (stage,),
        ):
            sections.append(_entry_md(dict(row)))
            count += 1
    conn.close()
    with open(_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(sections))
    print(f"Exported {count} entries")


if __name__ == "__main__":
    main()
