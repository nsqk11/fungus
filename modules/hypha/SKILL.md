---
name: hypha
description: "[module] Capture hook payloads as spores with structural filtering. Do NOT judge content value."
---

# Hypha

> Capture hook payloads and store as spores.
> Apply structural filters to discard noise before writing.

## Boundary

- **Does**:
  - Read stdin from every registered hook.
  - Apply structural filters per hook type.
  - Store passing payloads as spores via `bash memory.sh`.
- **Does not**:
  - Judge content value (that is Mycelium's job).
  - Write to any stage other than `spore`.

## Interface

- **Hooks**: `userPromptSubmit`, `preToolUse`, `postToolUse`, `stop`
- **Reads**: (none)
- **Writes**: `spore` stage via `bash memory.sh`

## Filters

Structural filters reduce noise before spore creation.
Content-level value judgment remains in Mycelium.

| Hook | Rule | Rationale |
|------|------|-----------|
| userPromptSubmit | Drop if `prompt` ≤ 5 chars | Exclude trivial acks |
| preToolUse | Skip if payload contains `memory.sh` | Self-referential exclusion |
| postToolUse | Skip if payload contains `memory.sh`; drop if `tool_response.success` ≠ `false` | Only errors carry diagnostic value |
| stop | No filter | Captures AI analysis summaries |

## Behavior

```bash
bash hooks/memory.sh add \
  --stage spore \
  --hook <hook-name> \
  --data "$STDIN"
```

### On userPromptSubmit

- Drop if `prompt` ≤ 5 characters.

### On preToolUse

- Skip if payload contains `memory.sh`.

### On postToolUse

- Skip if payload contains `memory.sh`.
- Drop if `tool_response.success` is not `false`.

### On stop

- Store assistant response.
- Extract tool chain for the current turn:
  find last `userPromptSubmit` timestamp, collect all `preToolUse`
  tool names after it, delete those preToolUse spores,
  write as a `toolChain` spore.
