---
name: fruit
description: "[module] Detect mature patterns in nutrients and produce new skills. Do NOT capture signals or digest spores."
---

# Fruit

> Emerge when nutrients accumulate — produce new skills.

## Boundary

- **Does**:
  - List nutrient entries via `bash memory.sh`.
  - Detect recurring keywords across nutrients.
  - Prompt the agent to produce a new skill when a pattern matures.
  - Upgrade mature nutrients to `fruiting` or `network` stage.
- **Does not**:
  - Capture raw signals.
  - Digest spores into nutrients.

## Interface

- **Hooks**: `agent-spawn`
- **Reads**: `nutrient` stage via `bash memory.sh`
- **Writes**: updates `nutrient` → `fruiting` or `network` via `bash memory.sh`

## Storage Commands

List nutrients:

```bash
bash hooks/memory.sh list --stage nutrient
```

Get nutrient detail:

```bash
bash hooks/memory.sh get <id>
```

Upgrade nutrient to network (permanent memory):

```bash
bash hooks/memory.sh update --id <id> --field stage --value network
bash hooks/memory.sh update --id <id> --field category --value "<category>"
```

Upgrade nutrient to fruiting (skill candidate):

```bash
bash hooks/memory.sh update --id <id> --field stage --value fruiting
```

## Behavior

### On agent-spawn

1. Run `bash hooks/memory.sh list --stage nutrient`.
   If no nutrients, skip silently.
2. Check for recurring keywords across nutrients.
   If no pattern, skip silently.
3. Output nutrient list for the agent to review.

The agent decides:
- Single insight → upgrade to `network` (permanent memory).
- Recurring pattern → upgrade to `fruiting`,
  then create a new skill in `skills/` following `skill-spec.md`.
