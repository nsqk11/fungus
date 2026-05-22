---
name: fungus-distill
description: "Memory distillation — consolidate extracted fragments into stable skills, rules, or knowledge entries. Trigger on: 'distill', '整理记忆', '归纳 skill', 'consolidate fragments', '提炼', or when a distill reminder appears. Do NOT trigger during normal tasks."
---

# Fungus Distill

## Purpose

Turn accumulated raw fragments (from automatic extraction) into stable,
high-quality outputs: SKILL.md files, prompt rules, or KB documents.
This is a collaborative process — you propose, the user decides.

## When activated

- User explicitly asks to distill/consolidate
- A distill reminder fires (fragment count or time threshold reached)

## Workflow

1. **Survey**: Read `~/.kiro/fungus/data/fragments.md` and query the DB
   to see what's accumulated since last distill.

2. **Identify candidates**: Group fragments by task name. Look for:
   - Same task with 3+ fragments → candidate for a new SKILL.md
   - Rules that overlap or conflict → candidate for consolidation
   - KB entries that are stale or redundant → candidate for cleanup

3. **Propose**: Present candidates to the user:
   - "You have 7 fragments for 'send SP kickoff email' — want me to
     draft a SKILL.md?"
   - "3 rules overlap about document writing — consolidate into one?"
   - "These 2 KB entries seem outdated — remove?"

4. **Draft**: On user approval, produce the output:
   - Skill → write SKILL.md to `~/.kiro/skills/<name>/`
   - Rule → append to system prompt or rules file
   - KB → write .md to knowledge base directory

5. **Confirm**: Show the draft. User approves, edits, or rejects.

6. **Commit**: On final approval, write the file and optionally mark
   source fragments as "distilled" in DB.

## Constraints

- Never auto-commit without user confirmation
- Prefer fewer, higher-quality outputs over many small ones
- A distilled skill should be complete enough to stand alone
- Rules must be short imperative statements
- If unsure about quality, ask the user rather than guessing

## DB queries

```bash
# Count undistilled fragments
python3 ~/.kiro/fungus/_memory.py list-existing

# Group by task (use shell)
sqlite3 ~/.kiro/fungus/data/memory.db \
  "SELECT task_or_topic, COUNT(*) FROM fragments GROUP BY task_or_topic ORDER BY COUNT(*) DESC"
```
