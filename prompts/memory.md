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

Memory is implemented as an asynchronous pipeline backed by SQLite.
You do not invoke it; it observes.

```
userPromptSubmit ──→ capture_prompt.py ──→ INSERT turn (status='userPromptSubmit')
preToolUse       ──→ capture_tool.py   ──→ UPDATE tools column (status='preToolUse')
postToolUse      ──→ capture_error.py  ──→ UPDATE tools column with error (status='postToolUse')
stop             ──→ stop.py           ──→ UPDATE response (status='stop')
                                       ──→ extract worker spawned (async)
```

All state lives in `data/memory.db` (SQLite, WAL mode). Multiple
sessions can run concurrently without interfering — SQLite handles
locking internally.

After the stop hook spawns the extract worker, control returns
to the user immediately — the worker finishes on its own timeline.

The extract worker reads all turns with status='stop', judges each
one per `parse-criteria.md`, and calls `extract.py keep` or
`extract.py drop`. Kept entries are inserted into the `memories`
table and appended to `long-term-memory.md` for KB indexing.

### Components

**`hooks/memory/_db.py`** — SQLite schema and connection helper.
Not a hook (underscore prefix). Defines `turns` and `memories`
tables, WAL mode, and `get_conn()`.

**`hooks/memory/capture_prompt.py`** — `userPromptSubmit`:
INSERT a new row into `turns` with the prompt text and
status='userPromptSubmit'.

**`hooks/memory/capture_tool.py`** — `preToolUse`: UPDATE the
current session's latest turn, appending the tool name to the
`tools` column. Skips noise tools (fs_read, grep, glob).

**`hooks/memory/capture_error.py`** — `postToolUse`: UPDATE the
current session's latest turn, appending error text to `tools`
when `tool_response.success` is false.

**`hooks/memory/remind_search.py`** — `userPromptSubmit`: emits a
`<memory-reminder>` context entry nudging the agent to search
`fungus-memory` when the prompt is ambiguous.

**`hooks/memory/stop.py`** — `stop`: UPDATE the turn with the
assistant response and status='stop', then spawn a detached
extract worker.

**`hooks/memory/extract.py`** — CLI tool used by the extract
worker:

```bash
python3.12 extract.py list                              # show status='stop' turns
python3.12 extract.py keep <id> "<summary>" "<detail>" "<tags>"
python3.12 extract.py drop <id>
```

Uses optimistic locking (claim via UPDATE WHERE status='stop')
so multiple workers never process the same turn twice.

**`prompts/parse-criteria.md`** — the extract worker's
operating manual: what to keep, what to drop, and the entry
format. Loaded into the worker prompt verbatim.

**`data/long-term-memory.md`** — append-only Markdown export,
indexed as the `fungus-memory` knowledge base with `autoUpdate:
true`. This is a materialized view for KB indexing, not the
source of truth.

Entry format (defined by `parse-criteria.md`):

```markdown
## <one-sentence summary>

Date: YYYY-MM-DD | Tags: tag1, tag2

<optional 1-3 sentence detail>
```

### Database schema

```sql
CREATE TABLE turns (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    prompt TEXT,
    tools TEXT DEFAULT '',
    response TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    summary TEXT NOT NULL,
    detail TEXT,
    tags TEXT,
    created_at TEXT NOT NULL,
    source_turn_id INTEGER REFERENCES turns(id)
);
```

### Status lifecycle

```
userPromptSubmit → preToolUse → postToolUse → stop → extracting → archived/dropped
```

Each hook updates status to its own name. The extract worker
claims turns by setting status='extracting' (optimistic lock),
then finalizes to 'archived' or 'dropped'.

### Runtime files

```
$KIRO_HOME/skills/fungus/data/
├── memory.db              # SQLite database (WAL mode)
├── memory.db-wal          # WAL file (auto-managed)
├── memory.db-shm          # shared memory (auto-managed)
└── long-term-memory.md    # KB-indexed export
```

## Design decisions

**SQLite over files.** Eliminates turn-file naming, flock,
snapshot/tail merge, and file-as-state-marker complexity. WAL
mode handles concurrent writes without manual locking.

**Per-turn extraction.** Each turn is a complete causal unit.
Per-session extraction risks information loss from context
dilution and unreliable session-end triggers.

**Optimistic locking for extract workers.** Multiple workers
can run safely in parallel — each claims a turn atomically
before processing. No blocking, no starvation.

**Immediate MD export on keep.** Each `keep_turn` appends to
`long-term-memory.md` so the KB indexes new entries without
waiting for a batch export.

**Status as hook name.** Using the hook event name as the
status value makes the lifecycle self-documenting and
debuggable via a simple SELECT.

**Memory is a property, not a skill.** There is no `SKILL.md`,
no description to match, no user-facing trigger. Memory is part
of what Fungus is, like the router or the system prompt.
