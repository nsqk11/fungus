---
name: mycelium
description: "[module] Digest raw spores into structured nutrients at session start. Do NOT capture signals or produce skills."
---

# Mycelium

> Digest raw spores into structured nutrients.

## Boundary

- **Does**:
  - Load network memory into context.
  - List undigested spores for the agent to review.
  - Prompt the agent to upgrade or skip spores.
- **Does not**:
  - Capture raw signals.
  - Produce skills or detect mature patterns.

## Interface

- **Hooks**: `agentSpawn`
- **Reads**: `spore` and `network` stages via `bash memory.sh`
- **Writes**: updates `spore` → `nutrient` or `skipped` via `bash memory.sh`

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

## Behavior

### On agentSpawn

1. Run `bash hooks/memory.sh list --stage network`.
   Output as `<memory>` block.
2. Run `bash hooks/memory.sh list --stage spore`.
   If no spores, skip silently.
3. Output digest prompt:

```
<mycelium-digest>
Undigested spores:
  [id] [hook] [source]
  ...

For each spore, review and run one of:

  Upgrade to nutrient:
    bash hooks/memory.sh update --id <id> --field stage --value nutrient
    bash hooks/memory.sh update --id <id> --field summary --value "<summary>"
    bash hooks/memory.sh update --id <id> --field keywords --value '["kw1","kw2"]'

  Skip (no value):
    bash hooks/memory.sh update --id <id> --field stage --value skipped

Skip silently if session is trivial.
</mycelium-digest>
```
