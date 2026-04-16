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
    "hook": "post-tool-use",
    "source": "environment",
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
| `stage` | string | yes | `spore`, `nutrient`, `fruiting`, `network` |
| `hook` | string | spore | Hook that produced this entry |
| `source` | string | spore | `user`, `agent`, `environment` |
| `data` | object | spore | Raw hook stdin, stored as-is |
| `summary` | string | nutrient+ | Digest of the signal |
| `keywords` | array | nutrient+ | For dedup and pattern detection |
| `refs` | array | nutrient+ | IDs of upstream entries |
| `category` | string | network | `Tool Usage`, `Preferences`, etc. |

## Lifecycle

```
spore → nutrient → fruiting → network
```

A spore may produce multiple nutrients.
Multiple nutrients may converge into one fruiting entry.
A fruiting entry becomes a network entry when mature.

## File Location

`data/memory.json` — gitignored.
