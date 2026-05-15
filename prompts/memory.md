# Memory

You have long-term memory.
Every turn you complete contributes to it.
Past insights surface through knowledge-base search when relevant.

## What this means for you

You do not manage memory manually.
A background pipeline records each turn, extracts memories across
9 cognitive directions, and stores them in a searchable store.
The next time a related topic comes up, the relevant entry is
available through the `fungus-memory` knowledge base.

When a user message is ambiguous or references prior context you
do not immediately recognize, search `fungus-memory` before asking
for clarification.
When you discover something worth remembering — a user preference,
an architectural decision, a non-obvious fix — trust that the
pipeline will capture it from the turn.
Do not ask the user to confirm a memory entry.
Do not write to the memory store directly.

## Memory taxonomy

Memory is classified into 9 directions based on cognitive
psychology (Squire 1992, Tulving 1985):

### Declarative (→ Knowledge Base, on-demand retrieval)

| Direction | What it captures |
|-----------|-----------------|
| **Semantic** | Facts, knowledge, terminology, configuration |
| **Episodic** | Specific events with causal chains, lessons |
| **Autobiographical** | Identity, relationships, roles |

### Non-declarative (→ Prompt, always active)

| Direction | What it captures |
|-----------|-----------------|
| **Skill** | Methods, procedures, multi-step approaches |
| **Habit** | User-preference-driven behavioral constraints |
| **Reflex** | Signal → action condition rules |
| **Metacognitive** | Self-knowledge about capabilities and limits |

### Cross-cutting

| Direction | What it captures |
|-----------|-----------------|
| **Prospective** | Future commitments, deferred actions |
| **Emotional** | User's strong attitudes toward topics |

Non-declarative memories are the upstream of skills. When
procedural knowledge consolidates sufficiently, it graduates
into a SKILL.md.

## How the pipeline works

```
Router (all hooks) ──→ INSERT into events.db
                       ↓ (read by)
stop hook         ──→ cleanup old events
                  ──→ spawn extract worker (async)
extract worker    ──→ derive turns from events
                  ──→ multi-direction extraction (1 LLM call)
                  ──→ JSON array → memories table (with category)
                  ──→ export split files
```

All raw events live in `data/events.db` (SQLite, WAL mode).
Memory state lives in `data/memory.db` (separate DB).
Multiple sessions can run concurrently — SQLite WAL handles
locking internally.

The extract worker uses `prompts/extract-criteria.md` as its
operating manual. One LLM call per turn evaluates all 9
directions independently. Output is a JSON array where each
element carries a `category` field.

### Components

**`hooks/router.py`** — registered as the Kiro hook handler.
Reads payload from stdin, inserts into `events.db` via
`insert_event()`, then dispatches to matching hook scripts.

**`hooks/memory/_db.py`** — shared DB helpers. Manages two
databases: `events.db` (schema + `insert_event()`) and
`memory.db` (memories + meta tables). Defines category
constants.

**`hooks/memory/stop.py`** — `stop`: cleanup events older than
24h, cleanup stale drop markers, VACUUM if rows deleted, spawn
extract worker. Triggers distill when memories ≥ 200.

**`hooks/memory/extract.py`** — CLI tool:

```bash
python3.12 extract.py list                    # show pending turns
python3.12 extract.py run                     # output turns for LLM processing
python3.12 extract.py keep '<json>' <event_id>  # save LLM output
python3.12 extract.py drop <event_id>           # mark turn as dropped
```

The `keep` command accepts a JSON array of extracted memories:

```json
[
  {
    "category": "semantic",
    "summary": "...",
    "detail": "...",
    "tags": "tag1, tag2"
  }
]
```

**`hooks/memory/distill.py`** — memory consolidation. Triggered
when memories ≥ 200. Merges/deduplicates, re-exports files.

**`hooks/memory/remind_search.py`** — `userPromptSubmit`: emits
`<memory-reminder>` nudging the agent to search when ambiguous.

**`prompts/extract-criteria.md`** — the extraction prompt with
9 directions, each with independent keep/drop criteria and
structured JSON output format.

### Database schemas

**events.db** (router writes, hooks read):

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,  -- time.time_ns()
    session_id TEXT NOT NULL,
    hook TEXT NOT NULL,
    cwd TEXT,
    prompt TEXT,
    tool_name TEXT,
    tool_success INTEGER,
    tool_error TEXT,
    response TEXT
);
```

**memory.db** (memory pipeline owns):

```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    summary TEXT NOT NULL,
    detail TEXT,
    tags TEXT,
    category TEXT,           -- one of 9 directions
    created_at TEXT NOT NULL,
    source_event_id INTEGER
);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### Output files

```
$KIRO_HOME/skills/fungus/data/
├── events.db                  # raw hook events
├── memory.db                  # memories + meta
├── memory-semantic.md         # KB: facts, knowledge
├── memory-episodic.md         # KB: events, lessons
├── memory-autobiographical.md # KB: identity, relationships
├── memory-procedural.md       # Prompt: skills, habits, reflexes, meta, prospective, emotional
└── long-term-memory.md        # Legacy combined (backward compat)
```

Declarative categories get individual KB files for targeted
retrieval. Non-declarative categories are combined into one
prompt file for injection.

### Turn derivation

A turn is derived from events, not stored explicitly:

```
Turn = all events between a userPromptSubmit and the next
       userPromptSubmit (same session), provided a stop event
       exists in that range.
```

## Design decisions

**Event-sourced.** Router writes once, hooks read. Each hook
event is an immutable fact.

**Two separate databases.** events.db (router-owned, append-only)
and memory.db (memory-pipeline-owned). Either can be deleted
independently.

**Turn derived, not stored.** No turns table. A turn is a SQL
query over events.

**Multi-direction extraction.** One LLM call per turn evaluates
9 cognitive directions independently. Each direction has its own
keep/drop criteria. Cost is the same as a single-direction call
(one API invocation), but extraction quality is higher because
the LLM is forced to evaluate from multiple angles.

**Category-split output.** Declarative memories go to KB files
(on-demand retrieval). Non-declarative memories go to a prompt
file (always active). This mirrors the cognitive distinction:
declarative = "what you know", non-declarative = "how you behave".

**Skill graduation.** Non-declarative memories are the upstream
of skills. When procedural knowledge consolidates sufficiently
through distill cycles, it can graduate into a SKILL.md. This
is the memory system's consolidation process.

**24h event retention.** Events older than 24h are deleted
(unless linked to a memory).

**Drop markers cleaned with events.** Prevents unbounded meta
table growth.

**VACUUM only when rows deleted.** Avoids unnecessary IO.

**Memory is a property, not a skill.** No SKILL.md, no trigger.
Memory is part of what Fungus is.
