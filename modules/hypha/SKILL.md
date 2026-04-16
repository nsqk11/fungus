---
name: hypha
description: "[module] Capture raw hook payloads and store as spores. Do NOT filter, judge, or transform."
---

# Hypha

> Capture every hook's raw payload and store it as a spore.

## Boundary

- **Does**:
  - Read stdin from every registered hook.
  - Store the full payload as a spore via `bash memory.sh`.
  - Exclude self-referential calls (see below).
- **Does not**:
  - Filter, judge, or transform signal content.
  - Write to any stage other than `spore`.

## Self-Referential Exclusion

Like auditd excluding its own PID, Hypha excludes tool calls that
operate on `memory.sh`. This prevents a feedback loop where digest
operations (which call `memory.sh`) would generate new spores.

Applies to: `preToolUse`, `postToolUse`.
Pattern: `grep -q 'memory\.sh'` on stdin payload.

## Interface

- **Hooks**: `userPromptSubmit`, `preToolUse`, `postToolUse`, `stop`
- **Reads**: (none)
- **Writes**: `spore` stage via `bash memory.sh`

## Behavior

All hooks follow the same pattern:
read stdin, forward the entire JSON as `--data`.

```bash
bash hooks/memory.sh add \
  --stage spore \
  --hook <hook-name> \
  --source <source> \
  --data "$STDIN"
```

### On userPromptSubmit

- **Source**: `user`

### On preToolUse

- **Source**: `agent`
- Skips if payload contains `memory.sh`

### On postToolUse

- **Source**: `environment`
- Skips if payload contains `memory.sh`

### On stop

- **Source**: `agent`
