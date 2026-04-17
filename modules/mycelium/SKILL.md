---
name: mycelium
description: "[module] Digest raw spores into structured
  nutrients at session start. Do NOT capture signals
  or produce skills."
---

# Mycelium

> Digest raw spores into structured nutrients.

## Boundary

- **Does**:
  - Load network memory into agent context.
  - Count undigested spores and prompt the agent to review.
  - Guide the agent to upgrade or skip spores.
- **Does not**:
  - Capture raw signals.
  - Produce skills or detect mature patterns.
  - Run `clean` (substrate handles that).

## Interface

- **Hooks**: `agentSpawn`
- **Reads**: `spore` and `network` stages via `bash memory.sh`
- **Writes**: updates `spore` → `nutrient` or `skipped`
  via `bash memory.sh`

## Storage Commands

List network memory:

```bash
bash hooks/memory.sh list --stage network
```

List undigested spores:

```bash
bash hooks/memory.sh list --stage spore
```

Get full spore detail:

```bash
bash hooks/memory.sh get <id>
```

Upgrade spore to nutrient:

```bash
bash hooks/memory.sh update --id <id> --field stage --value nutrient
bash hooks/memory.sh update --id <id> --field summary --value "<summary>"
bash hooks/memory.sh update --id <id> --field keywords --value '["kw1","kw2"]'
```

Skip valueless spore:

```bash
bash hooks/memory.sh update --id <id> --field stage --value skipped
```

## Digest Direction

Extract reusable knowledge from spores based on hook type.
Skip everything that does not match these directions.

### userPromptSubmit

- User preferences and habits.
- Architecture decisions and rationale.
- Technical discoveries about tools or systems.
- Bugs, defects, or anomalies.
- Domain knowledge: naming rules, process conventions,
  reusable facts.

### toolChain

- Tool combination sequences for a task.
  Produced by `hypha` from `preToolUse` spores within a turn.

### preToolUse

- Normally absent — aggregated into `toolChain` by `hypha`.
  Skip if encountered (residual from incomplete aggregation).

### postToolUse

- Error context: what failed, why, and surrounding conditions.
  Only failure spores reach this stage
  (`hypha` filters success out).

### stop

- AI analysis summaries: reasoning path, conclusions,
  decision rationale.

## Behavior

### On agentSpawn

The script outputs context for the agent.
The agent performs the actual digest in-session.

1. Query network summaries via `bash memory.sh`.
   Output as `<memory>` block.
2. Count spores via `bash memory.sh count --stage spore`.
   If zero, skip silently.
3. Output `<mycelium-reminder>` prompting the agent
   to ask the user about digestion.

The agent, when confirmed by the user, reads this SKILL.md
and processes each spore using the Storage Commands
and Digest Direction above.
