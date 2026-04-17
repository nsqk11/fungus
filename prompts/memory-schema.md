# Memory Schema

Data structure for `memory.json` — the shared data store.

## Format

Flat JSON array. Each entry is one record.

```json
[
  {
    "id": "20260416001",
    "timestamp": "2026-04-16T07:20:00Z",
    "stage": "spore",
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
| `hook` | string | spore | Hook that produced this entry |
| `data` | object | spore | Raw hook stdin, stored as-is |
| `summary` | string | nutrient+ | Digest of the signal |
| `keywords` | array | nutrient+ | For dedup and pattern detection |
| `refs` | array | nutrient+ | IDs of upstream entries |
| `category` | string | network | Classification label |

## Stage Enum

`spore`, `nutrient`, `fruiting`, `network`, `skipped`.

## Lifecycle

```
spore → nutrient → network    (permanent memory)
spore → nutrient → fruiting   (skill candidate, cleaned after use)
spore → skipped               (no value, cleaned)
```

Each transition is an in-place update on the same entry.
One spore becomes one nutrient.
One nutrient becomes one network or one fruiting entry.

Substrate runs `clean` on `agentSpawn` before any module.
Clean deletes `skipped` and `fruiting` entries
and caps `network` at the newest entries when over limit.

## File Location

`data/memory.json` — single shared store, gitignored.
