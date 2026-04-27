# Memory Schema

Data structure for `data/memory.db` — the long-term memory store.

## Format

Flat JSON array. Each entry is one record.

```json
[
  {
    "id": "20260416001",
    "timestamp": "2026-04-16T07:20:00Z",
    "stage": "raw",
    "hook": "postToolUse",
    "data": {},
    "summary": "",
    "keywords": [],
    "refs": [],
    "category": ""
  }
]
```

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | `YYYYMMDD` + 3-digit sequence |
| `timestamp` | string | yes | ISO 8601 UTC |
| `stage` | string | yes | See Stage enum below |
| `hook` | string | raw | Hook event that produced this entry |
| `data` | object | raw | Raw hook stdin, stored as-is |
| `summary` | string | parsed+ | Condensed description of the signal |
| `keywords` | array | parsed+ | For deduplication and pattern detection |
| `refs` | array | parsed+ | IDs of upstream entries |
| `category` | string | longterm | Classification label |

## Stage Enum

| Stage | Meaning |
|-------|---------|
| `raw` | Captured by a hook, not yet parsed |
| `parsed` | Condensed with summary and keywords |
| `longterm` | Promoted to permanent memory |
| `candidate` | Pattern formed; awaiting skill creation |
| `dropped` | No value; will be cleaned |

## Lifecycle

```
raw → parsed → longterm    (permanent memory)
raw → parsed → candidate   (skill material, cleaned after use)
raw → dropped              (no value, cleaned)
```

Each transition is an in-place update on the same entry.
One `raw` becomes one `parsed`.
One `parsed` becomes one `longterm` or one `candidate`.

The on-spawn hook runs a cleanup pass before other handlers.
Cleanup deletes `dropped` and `candidate` entries and caps
`longterm` at the newest entries when over limit.

## File Location

`skills/memory-curation/data/memory.db` — single shared store,
gitignored.
