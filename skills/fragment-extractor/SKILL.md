---
name: fragment-extractor
description: "Automatically extracts reusable knowledge fragments from session transcripts. Runs in the background after each session ends. Also provides a manual distill workflow to consolidate accumulated fragments into stable skills, rules, or KB entries. Trigger on: 'distill', '整理记忆', '归纳 skill', 'consolidate fragments', '提炼', or when a distill reminder appears."
---

# Fragment Extractor

Extracts reusable knowledge from session transcripts and persists them
as scored fragments in a local SQLite database.

## How it works

```
Session ends → agentSpawn hook → batch extraction (background)
                                        │
                        ┌───────────────┼───────────────┐
                        ▼               ▼               ▼
                 skill-extractor  kb-extractor   rule-extractor
                        │               │               │
                        └───────────────┼───────────────┘
                                        ▼
                                   SQLite DB
                                        │
                             ┌──────────┴──────────┐
                             ▼                     ▼
                        rules.md              fragments.md
                     (always loaded)         (KB searchable)
```

Each extractor scores fragments on three dimensions:
- **x_knowledge** — standalone factual content (0.0–1.0)
- **y_rule** — unconditional behavioral constraint (0.0–1.0)
- **z_task** — bound to a specific recurring task (0.0–1.0)

Fragments with `y_rule > 0` export to `rules.md` (injected every
session). The rest export to `fragments.md` (searchable via KB).

## Distill workflow

When fragments accumulate, consolidate them into stable outputs:

1. **Survey**: Query DB to see what's accumulated.
2. **Identify candidates**: Group by task, find clusters (3+ fragments).
3. **Propose**: Present candidates to user.
4. **Draft**: On approval, produce SKILL.md / rule / KB entry.
5. **Confirm**: User approves, edits, or rejects.
6. **Commit**: Write final output.

```bash
# Count fragments
scripts/memory.py list-existing

# Group by task
sqlite3 $KIRO_HOME/data/fragment-extractor/memory.db \
  "SELECT task_or_topic, COUNT(*) FROM fragments GROUP BY task_or_topic ORDER BY COUNT(*) DESC"
```

## Constraints

- Never auto-commit without user confirmation
- Prefer fewer, higher-quality outputs over many small ones
- If unsure about quality, ask the user
