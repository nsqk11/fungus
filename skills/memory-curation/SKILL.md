---
name: memory-curation
description: "Maintain the agent's long-term memory. Triggered
  primarily by <memory-curation-reminder> tags in context entries,
  injected by hook scripts at session start or on ambiguous user
  messages. Parse raw captures into structured entries, detect
  recurring patterns, promote mature patterns into new skills, and
  retire stale data. May also trigger on mentions of 'memory',
  'recall', 'long-term memory', 'skill growth', 'digest memory',
  'review memory'. Do NOT capture raw signals — hook scripts under
  this skill handle that automatically. Do NOT modify memory.db
  schema or hook registration."
---

# Memory Curation

> Parse captures. Detect patterns. Grow skills. Retire stale data.

## Boundary

- **Does**:
  - Respond to `<memory-curation-reminder>` tags injected by hook
    scripts.
  - Parse `raw` captures into `parsed` entries with summary and
    keywords.
  - Detect recurring patterns across `parsed` entries.
  - Promote mature patterns to `candidate` and help the user create
    new skills.
  - Promote standalone insights to `longterm` memory.
  - Retire valueless entries to `dropped`.
- **Does not**:
  - Capture raw signals. Hook scripts under `scripts/` do that.
  - Modify `memory.db` schema or stage enum.
  - Register or unregister hooks. `install.sh` does that.
  - Run without user confirmation on the first action of each
    reminder type.

## Interface

- **Triggers**: `<memory-curation-reminder>` tags in context entries,
  or direct user requests matching the description keywords.
- **Data store**: `data/memory.db` at the skill root.
- **Access layer**: `scripts/memory.py` — CRUD for `memory.db`.
- **Hook scripts**: `scripts/on_*.sh` — capture and reminder injection.
- **References**:
  - `references/parse-protocol.md` — raw to parsed workflow.
  - `references/pattern-protocol.md` — parsed to skill workflow.
  - `references/memory-schema.md` — `memory.db` data model.

## Behavior

A `<memory-curation-reminder>` may signal three different situations.
Read the reminder body to determine which.

### Unparsed data pending

Reminder body reports a count of `raw` entries awaiting parsing.

Ask the user whether to parse now. If confirmed, follow
`references/parse-protocol.md` for each entry: decide whether it
contains reusable knowledge, write a summary and keywords, and promote
it to `parsed`. Entries with no value go to `dropped`.

### Accumulated patterns

Reminder body reports a count of `parsed` entries and top recurring
keywords.

Ask the user whether to review now. If confirmed, follow
`references/pattern-protocol.md`: scan `parsed` entries, identify
recurring patterns, confirm each candidate pattern with the user,
and create new skills when confirmed. Standalone insights go to
`longterm`; pattern-forming entries go to `candidate`.

### Ambiguous user message

Reminder body advises searching memory before answering.

Search the memory knowledge base for relevant `longterm` entries.
Ground the reply in prior knowledge when applicable. If nothing
relevant is found, proceed with the user's message as given.

### Direct user questions about memory

Answer from `references/memory-schema.md` and `longterm` entries.
Do not invent lifecycle rules — cite the schema.
