---
name: fruit
description: "[module] Detect mature patterns in nutrients
  and produce new skills. Do NOT capture signals
  or digest spores."
---

# Fruit

> Emerge when nutrients accumulate — produce new skills.

## Boundary

- **Does**:
  - Count nutrient entries via `bash memory.sh`.
  - Prompt the agent to review nutrients for patterns.
  - Guide the agent to upgrade nutrients to `fruiting`
    or `network` stage.
- **Does not**:
  - Capture raw signals.
  - Digest spores into nutrients.

## Interface

- **Hooks**: `agentSpawn`
- **Reads**: `nutrient` stage via `bash memory.sh`
- **Writes**: updates `nutrient` → `fruiting` or `network`
  via `bash memory.sh`

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

### On agentSpawn

The script outputs a reminder for the agent.
The agent performs pattern detection in-session.

1. Count nutrients via `bash memory.sh count --stage nutrient`.
   If zero, skip silently.
2. Output `<fruit-reminder>` prompting the agent
   to ask the user about skill emergence review.

The agent, when confirmed by the user, reads this SKILL.md
and reviews nutrients using the Storage Commands above.

Pattern detection criteria (applied by the agent):
- Check for recurring keywords across nutrients.
- Single insight → upgrade to `network`.
- Recurring pattern → upgrade to `fruiting`,
  then create a new skill in `skills/` following `skill-spec.md`.
