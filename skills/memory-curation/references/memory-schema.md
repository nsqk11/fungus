# Memory Schema

Data structure for `data/memory.db` — the long-term memory store.

## Format

Flat JSON array. Each entry is one record.

```json
[
  {
    "id": "20260416001",
    "timestamp": "2026-04-16T07:20:00Z",
    "stage": "pending",
    "hook": "",
    "data": {
      "prompt": "user message text",
      "tools": ["execute_bash", "fs_read"],
      "errors": [],
      "response": "agent response summary"
    },
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
| `hook` | string | no | Empty for interaction entries |
| `data` | object | yes | Interaction payload (see below) |
| `summary` | string | parsed+ | Condensed description |
| `keywords` | array | parsed+ | For deduplication and pattern detection |
| `refs` | array | parsed+ | IDs of upstream entries |
| `category` | string | longterm | Classification label |

### `data` Object

One entry represents one complete interaction (user prompt through
agent response).

| Key | Type | Set by | Description |
|-----|------|--------|-------------|
| `prompt` | string | capture_prompt | User message text |
| `tools` | array | capture_tool_call | Tool names used during the turn |
| `errors` | array | capture_tool_error | Tool failure descriptions |
| `response` | string | capture_response | Agent response summary |

## Stage Enum

| Stage | Meaning |
|-------|---------|
| `pending` | Interaction in progress, accumulating data |
| `raw` | Complete interaction, not yet parsed |
| `parsed` | Condensed with summary and keywords |
| `longterm` | Promoted to permanent memory |
| `dropped` | No value; will be cleaned |

## Lifecycle

```
pending → raw → parsed → longterm    (permanent memory)
                       → dropped     (no value, cleaned)
raw → dropped                        (no value, cleaned)
```

Each transition is an in-place update on the same entry.

- `capture_prompt` creates a `pending` entry with the user prompt.
- `capture_tool_call` and `capture_tool_error` append to the
  `pending` entry during the turn.
- `capture_response` finalizes the entry and promotes it to `raw`.
- The on-spawn hook runs a cleanup pass that deletes `dropped` and
  stale `pending` entries, and caps `longterm` at the newest entries
  when over limit.

## File Location

`skills/memory-curation/data/memory.db` — single shared store,
gitignored.
