---
name: hypha
description: "[module] Capture hook payloads as spores
  with structural filtering. Do NOT judge content value."
---

# Hypha

> Capture hook payloads and store as spores.
> Apply structural filters to discard noise before writing.

## Boundary

- **Does**:
  - Read stdin from every registered hook.
  - Apply structural filters per hook type.
  - Store passing payloads as spores via `bash memory.sh`.
  - Aggregate tool sequences into `toolChain` spores at stop time.
  - Delete aggregated `preToolUse` spores after aggregation.
- **Does not**:
  - Judge content value (that is the digest stage's job).
  - Write to any stage other than `spore`.

## Interface

- **Hooks**: `userPromptSubmit`, `preToolUse`, `postToolUse`, `stop`
- **Reads**: `spore` stage via `bash memory.sh`
  (on `stop`, to find turn boundary and aggregate tool chain)
- **Writes**: `spore` stage via `bash memory.sh`

## Filters

Structural filters reduce noise before spore creation.
Content-level value judgment remains in the digest stage.

| Hook | Rule | Rationale |
|------|------|-----------|
| `userPromptSubmit` | Drop if `prompt` ≤ 5 chars | Trivial acks |
| `preToolUse` | Skip if payload contains `memory.sh` | Self-referential |
| `postToolUse` | Skip if `memory.sh`; drop if not failure | Errors only |
| `stop` | No filter | AI analysis summaries |

## Behavior

### On userPromptSubmit

Drop if `prompt` ≤ 5 characters.
Store as spore.

### On preToolUse

Skip if payload contains `memory.sh`.
Store as spore.

### On postToolUse

Skip if payload contains `memory.sh`.
Drop if `tool_response.success` is not `false`.
Store as spore.

### On stop

1. Store assistant response as `stop` spore.
2. Find the last `userPromptSubmit` spore ID as turn boundary.
3. Collect `preToolUse` spore tool names after that boundary.
4. Delete those `preToolUse` spores.
5. Store the tool sequence as a `toolChain` spore.

Skip steps 2–5 if no tools were used in this turn.
