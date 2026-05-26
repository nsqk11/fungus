---
name: fragment-extractor
description: "Persistent memory for AI agents. Automatically extracts reusable knowledge fragments from session transcripts after each session ends (background, no user action needed). Also provides a manual distill workflow to consolidate accumulated fragments into stable skills, rules, or KB entries. Use this skill when the user wants to review what the agent has learned, consolidate fragments into skills, clean up redundant memories, or check extraction status."
compatibility: "Python 3.10+, kiro-cli (for extractor agents)"
---

# Fragment Extractor

Two modes of operation:

1. **Automatic extraction** — runs in the background after every session,
   no user action needed. Extracts knowledge fragments and persists them.
2. **Manual distill** — user-driven consolidation of accumulated fragments
   into stable outputs (skills, rules, KB entries).

---

## Automatic Extraction (background)

### How it works

```
Session ends → agentSpawn hook fires
    → scripts/spawn-extract.py launches scripts/extract.py (background)
        → 3 extractor agents run in parallel on the session transcript
            → fragments scored and saved to SQLite
                → exported to rules.md + fragments.md
```

### Components

| File | Role |
|------|------|
| `scripts/spawn-extract.py` | Hook triggered on `agentSpawn`; launches extraction in background |
| `scripts/extract.py` | Batch scheduler; loops unprocessed sessions with 5-min timeout |
| `scripts/memory.py` | DB operations; called by extractor agents to save results |
| `references/agents/*.md` | 3 worker agent configs (skill-extractor, kb-extractor, rule-extractor). Install by copying to `$KIRO_HOME/agents/` as `.json`. |
| `references/extract-*.md` | Instructions for each extractor agent |

### Scoring dimensions

Each fragment is scored on three axes (0.0–1.0):

| Dimension | Meaning | Export target |
|-----------|---------|---------------|
| `x_knowledge` | Standalone factual content | fragments.md (KB) |
| `y_rule` | Unconditional behavioral constraint | rules.md (always loaded) |
| `z_task` | Bound to a specific recurring task | fragments.md (KB) |

Fragments with `y_rule > 0` go to `rules.md` (injected into every
session). The rest go to `fragments.md` (searchable via knowledge base).

### Setup

Register the hook in your agent config:

```json
{
  "hooks": {
    "agentSpawn": ["$KIRO_HOME/skills/fragment-extractor/scripts/spawn-extract.py"]
  }
}
```

Register extractor agents:

```bash
for f in references/agents/*.md; do
    name=$(basename "$f" .md)
    sed "s|FUNGUS_ROOT|$KIRO_HOME/skills|g" "$f" > $KIRO_HOME/agents/${name}.json
done
```

After setup, extraction runs automatically. No user action needed.

---

## Manual Distill (user-driven)

When fragments accumulate, the user (or a reminder) triggers
consolidation. This is a collaborative process — the agent proposes,
the user decides.

### Workflow

1. **Survey**: Check what's accumulated.
2. **Identify candidates**: Group by task, find clusters (3+ fragments on same topic).
3. **Propose**: Present candidates to user:
   - "7 fragments for 'send kickoff email' — draft a SKILL.md?"
   - "3 overlapping rules about document writing — consolidate?"
   - "2 stale KB entries — remove?"
4. **Draft**: On user approval, produce the output.
5. **Confirm**: Show draft. User approves, edits, or rejects.
6. **Commit**: Write the final file.

### Distill commands

```bash
# List recent fragments
scripts/memory.py list-existing

# Group by task (find consolidation candidates)
sqlite3 $KIRO_HOME/data/fragment-extractor/memory.db \
  "SELECT task_or_topic, COUNT(*) as c FROM fragments GROUP BY task_or_topic HAVING c >= 3 ORDER BY c DESC"

# Check which sessions have been processed
scripts/memory.py list-unprocessed
```

### Distill constraints

- Never auto-commit without user confirmation
- Prefer fewer, higher-quality outputs over many small ones
- A distilled skill should be complete enough to stand alone
- If unsure about quality, ask the user rather than guessing

---

## Examples

**Check extraction status:**
```
$ scripts/memory.py list-existing
[kb-extractor] docker-compose: Service depends_on only waits for container start...
[rule-extractor] output format: Always use markdown code blocks for code snippets
[skill-extractor] git workflow: When pushing, check remote URL first and exclude...
```

**Find distill candidates:**
```
$ sqlite3 $KIRO_HOME/data/fragment-extractor/memory.db \
    "SELECT task_or_topic, COUNT(*) as c FROM fragments GROUP BY task_or_topic HAVING c >= 3 ORDER BY c DESC"
git workflow|8
API integration|5
document formatting|4
```

**Manual extraction (rarely needed):**
```
$ scripts/extract.py
Sessions to process: 3
[1/3] 10:30:15 abc123def456
  ✓ done (45s)
[2/3] 10:31:00 789ghi012jkl
  ✓ done (38s)
[3/3] 10:31:40 mno345pqr678
  ✓ done (52s)
---
All 3 sessions processed.
```

---

## Error handling

| Situation | Behaviour |
|-----------|-----------|
| Lock held (another extraction running) | Hook exits silently; no duplicate runs |
| Session timeout (>5 min) | Session moved to end of queue for retry |
| Extractor agent fails | Session marked as processed with 0 fragments |
| No unprocessed sessions | Hook exits immediately |
| DB locked | Retries with 10s timeout (SQLite WAL mode) |

---

## Data

SQLite at `$KIRO_HOME/data/fragment-extractor/memory.db`.

Exports:
- `$KIRO_HOME/prompts/rules.md` — rules (y_rule > 0), always loaded
- `$KIRO_HOME/knowledge-bases/fungus/fragments.md` — KB entries, searchable

---

## CLI reference (scripts/memory.py)

```
memory.py save <extractor> '<json_array>' [session_id]   # Save fragments (used by agents)
memory.py finish <session_id> [count]                    # Mark session done
memory.py list-existing                                  # Show recent fragments
```
