# Memory

You have long-term memory.
Every turn you complete contributes to it.
Past insights surface through knowledge-base search when relevant.

## What this means for you

You do not manage memory manually.
A background pipeline records each turn, distills it into a short
entry, and appends it to a searchable store.
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

## How the property works

Memory is event-sourced. The router writes every hook event to a
shared `events.db`; downstream hooks read from it.

```
Router (all hooks) ──→ INSERT into events.db
                       ↓ (read by)
stop hook         ──→ cleanup old events
                  ──→ spawn extract worker (async)
extract worker    ──→ derive turns from events
                  ──→ keep/drop → memories table + md export
```

All raw events live in `data/events.db` (SQLite, WAL mode).
Memory state lives in `data/memory.db` (separate DB).
Multiple sessions can run concurrently — SQLite WAL handles
locking internally.

After the stop hook spawns the extract worker, control returns
to the user immediately — the worker finishes on its own timeline.

The extract worker queries `events.db` to derive completed turns
(prompt + tools + response), judges each per `parse-criteria.md`,
and writes results to `memory.db`. Kept entries are also appended
to `long-term-memory.md` for KB indexing.

### Components

**`hooks/router.py`** — registered as the Kiro hook handler.
Reads payload from stdin, inserts into `events.db` via
`insert_event()`, then dispatches to matching hook scripts.
The router only writes; it never reads events.

**`hooks/memory/_db.py`** — shared DB helpers. Manages two
databases: `events.db` (schema + `insert_event()`) and
`memory.db` (memories + meta tables). Not a hook (underscore
prefix).

**`hooks/memory/stop.py`** — `stop`: cleanup events older than
24h (preserving those linked to memories), cleanup stale drop
markers from meta, VACUUM if rows were deleted, then spawn
extract worker. Also triggers distill when memories ≥ 200.

**`hooks/memory/extract.py`** — CLI tool used by the extract
worker:

```bash
python3.12 extract.py list
python3.12 extract.py keep <prompt_event_id> "<summary>" "<detail>" "<tags>"
python3.12 extract.py drop <prompt_event_id>
```

Derives turns by querying events between consecutive
`userPromptSubmit` events. Uses `memory.db` to track which
turns have been processed (kept → memories table, dropped →
meta table).

**`hooks/memory/distill.py`** — CLI tool for memory
consolidation:

```bash
python3.12 distill.py list
python3.12 distill.py apply '<json_array>'
python3.12 distill.py unlock
```

Triggered from `stop.py` when memories ≥ 200. Merges/deduplicates
entries, re-exports `long-term-memory.md`, and VACUUMs memory.db.

**`hooks/memory/remind_search.py`** — `userPromptSubmit`: emits
a `<memory-reminder>` context entry nudging the agent to search
`fungus-memory` when the prompt is ambiguous.

**`hooks/audit/on_pre_tool.py`** — `preToolUse`: queries
`events.db` for consecutive `postToolUse` failures of the same
tool in the current turn. Emits `<audit-reminder>` when the
streak reaches 3.

**`prompts/parse-criteria.md`** — the extract worker's
operating manual: what to keep, what to drop, and the entry
format.

**`data/long-term-memory.md`** — append-only Markdown export,
indexed as the `fungus-memory` knowledge base. Materialized
view for KB indexing, not the source of truth.

### Database schemas

**events.db** (router writes, hooks read):

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,  -- time.time_ns()
    session_id TEXT NOT NULL,
    hook TEXT NOT NULL,       -- agentSpawn/userPromptSubmit/preToolUse/postToolUse/stop
    cwd TEXT,
    prompt TEXT,             -- userPromptSubmit only
    tool_name TEXT,          -- preToolUse/postToolUse only
    tool_success INTEGER,    -- postToolUse only (1/0)
    tool_error TEXT,         -- postToolUse only (on failure)
    response TEXT            -- stop only
);
```

**memory.db** (memory pipeline owns):

```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    summary TEXT NOT NULL,
    detail TEXT,
    tags TEXT,
    created_at TEXT NOT NULL,
    source_event_id INTEGER  -- links to events.id (the userPromptSubmit)
);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### Turn derivation

A turn is not stored explicitly. It is derived from events:

```
Turn = all events between a userPromptSubmit and the next
       userPromptSubmit (same session), provided a stop event
       exists in that range.
```

### Runtime files

```
$KIRO_HOME/skills/fungus/data/
├── events.db              # raw hook events (WAL mode)
├── memory.db              # memories + meta (WAL mode)
└── long-term-memory.md    # KB-indexed export
```

## Design decisions

**Event-sourced.** Router writes once, hooks read. No UPDATE,
no status flow, no cross-hook data passing. Each hook event is
an immutable fact.

**Two separate databases.** events.db is owned by the router
(write-only, append-only). memory.db is owned by the memory
pipeline. Separation of concerns; either can be deleted
independently.

**Turn derived, not stored.** No turns table. A turn is a SQL
query over events. This eliminates status columns, UPDATE
operations, and the complexity of tracking turn lifecycle.

**24h event retention.** Events older than 24h are deleted
(unless linked to a memory). This bounds DB size without
losing anything valuable — kept turns are preserved in
memories, dropped turns are forgotten by design.

**Drop markers cleaned with events.** When an event is deleted,
its `dropped_<id>` meta entry is also removed, preventing
unbounded meta table growth.

**VACUUM only when rows deleted.** Avoids unnecessary IO on
every stop.

**Memory is a property, not a skill.** There is no `SKILL.md`,
no description to match, no user-facing trigger. Memory is part
of what Fungus is, like the router or the system prompt.
