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
  - Output keyword frequency to aid pattern detection.
  - Prompt the agent to review nutrients for patterns.
  - Guide the agent through skill creation when
    a pattern is confirmed.
  - Upgrade nutrients to `fruiting` or `network` stage.
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

1. Count nutrients via `bash memory.sh count --stage nutrient`.
   If zero, skip silently.
2. Extract keyword frequencies across all nutrients.
   Output as `<fruit-reminder>` with count and top keywords.

The agent, when confirmed by the user, reads this SKILL.md
and proceeds to Pattern Detection below.

### Pattern Detection

Review all nutrients. Look for:

- **Recurring keywords** — same keyword in 3+ nutrients
  signals a pattern worth capturing as a skill.
- **Single insight** — a standalone fact with no recurring
  pattern. Upgrade to `network` (permanent memory).
- **No pattern** — skip silently.

When a pattern is found, confirm with the user
before proceeding to Skill Creation.

### Skill Creation

Follow this sequence when a pattern matures into a skill.

#### 1. Capture Intent

Clarify with the user:
- What should this skill enable the agent to do?
- When should it trigger? (phrases, contexts, file types)
- What is explicitly out of scope?

Extract answers from the nutrients where possible.
The user fills gaps and confirms before proceeding.

#### 2. Write the SKILL.md

Follow `skill-spec.md` strictly. Key points:

- **description** must be pushy — include trigger keywords
  and `Do NOT` exclusions so the skill activates reliably.
  Err on the side of over-triggering; undertriggering
  is the more common failure mode.
- **Boundary** must have clear Does / Does not.
- **Behavior** must trace back to Boundary items.
- Explain *why* behind instructions, not just *what*.
  The agent using this skill is smart — reasoning
  is more effective than rigid MUSTs.

Place the new skill in `skills/<skill-name>/SKILL.md`.

#### 3. Verify

After writing the skill:
- Re-read it with fresh eyes. Is it general enough
  to handle variations, or overfitted to the nutrients
  that spawned it?
- Check the description triggers against realistic prompts.
  Would a user's natural phrasing activate it?
- Check the Does Not list. Are adjacent concerns excluded?

#### 4. Upgrade Nutrients

- Nutrients that formed the pattern → `fruiting`.
- Standalone insights discovered during review → `network`.

### Description Quality Checklist

Apply when writing or reviewing any skill description.

- Starts with `[type]` prefix: `[module]`, `[tool]`,
  or `[guide]`.
- States what the skill does in one sentence.
- Includes trigger keywords — the words a user would
  naturally say when they need this skill.
- Includes `Do NOT` exclusions — adjacent concerns
  that belong to other skills.
- Pushy enough: would the agent pick this skill
  even if the user does not name it explicitly?
