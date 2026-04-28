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

Memory is implemented as an asynchronous pipeline that runs
outside your turn. You do not invoke it; it observes.

```
userPromptSubmit ──→ capture_prompt.py ──→ turn-<ts>.txt (new file)
preToolUse       ──→ capture_tool.py   ──→ turn-<ts>.txt (tool appended)
postToolUse      ──→ capture_error.py  ──→ turn-<ts>.txt (error appended)
stop             ──→ auto_parse.sh     ──→ response appended
                                       ──→ worker spawned (async, detached)
                                       ──→ older turn files archived
```

Each turn has its own file, keyed by a nanosecond timestamp.
After the stop hook launches the worker, control returns to the
user immediately — the worker finishes on its own timeline.

The worker reads the turn file and rewrites it in place: either a
Markdown memory entry (keep) or an empty file (drop). On the
next stop, any turn file that is no longer `PROMPT:`-prefixed is
archived into `long-term-memory.md` and removed.

### Components

**`hooks/memory/capture_prompt.py`** — `userPromptSubmit`:
creates a new `turn-<nanoseconds>.txt` and writes the `PROMPT:`
line. A fresh file per turn means the pipeline tolerates
concurrent turns and delayed worker completions without
overwriting anything.

**`hooks/memory/capture_tool.py`** — `preToolUse`: finds the most
recent turn file (lexicographic max over `turn-*.txt`) and
appends `TOOL: <name>`. Skips noise tools such as `fs_read`,
`grep`, `glob`.

**`hooks/memory/capture_error.py`** — `postToolUse`: finds the
most recent turn file and appends `ERROR: <text>` when
`tool_response.success` is false.

**`hooks/memory/remind_search.py`** — `userPromptSubmit`: emits a
`<memory-reminder>` context entry nudging the agent to search
`fungus-memory` when the prompt is ambiguous.

**`hooks/memory/_common.py`** — shared helpers: `new_turn_file()`
creates a timestamped turn file, `latest_turn_file()` returns the
current turn (if any). Underscore prefix makes the router skip
it.

**`hooks/memory/auto_parse.sh`** — registered for `stop`:

1. Find the current turn file (the newest `turn-*.txt`).
2. Append `RESPONSE: <assistant_response>` to it.
3. Spawn a detached `kiro-cli chat --no-interactive` worker in
   the background. The worker prompt contains
   `prompts/parse-criteria.md` and the absolute path of the
   current turn file. The worker will read, judge, and rewrite
   the file in place.
4. For every *other* `turn-*.txt` in `data/`:
   - If the file is empty, remove it (the worker chose drop).
   - If the first line still starts with `PROMPT:`, skip it (the
     worker has not finished yet; it will be picked up on a
     future stop).
   - Otherwise the file is a finished memory entry: append it to
     `long-term-memory.md`, then remove it.
5. Exit immediately. The worker keeps running on its own.

**Worker** — a headless `kiro-cli chat --no-interactive`
invocation using the default agent. It needs `fs_read` (to read
the turn file) and `fs_write` (to overwrite it). The default
agent must have both tools enabled; without them the worker
cannot rewrite the turn file and the pipeline stalls. The worker
prompt is `parse-criteria.md` plus the turn file's path; the
worker reads the turn, decides keep or drop, and rewrites the
file.

Having the worker rewrite the turn file in place means:
- No separate output file to coordinate.
- The file's content is the pipeline's status marker:
  `PROMPT:...` means "not yet processed", anything else means
  "worker finished".
- `kiro-cli`'s unavoidable ANSI decoration on stdout is ignored
  entirely.

**`prompts/parse-criteria.md`** — the worker's operating manual:
what to keep, what to drop, and the file-write output format.
Loaded into the worker prompt verbatim.

**`data/long-term-memory.md`** — append-only Markdown store,
indexed as the `fungus-memory` knowledge base with `autoUpdate:
true`. Not committed to the repo; `install.sh` creates an empty
file on first install.

Entry format (defined by `parse-criteria.md`):

```markdown
## <one-sentence summary>

Date: YYYY-MM-DD | Tags: tag1, tag2

<optional 1-3 sentence detail>
```

### Runtime files

```
$KIRO_HOME/skills/fungus/data/
├── long-term-memory.md     # long-term store, KB-indexed
└── turn-<nanoseconds>.txt  # one per in-flight or pending turn
```

Normally only the current turn file exists. Extra turn files mean
one or more workers are still running or crashed mid-parse. Files
whose workers crashed before rewriting will be reclaimed on the
next successful turn-end — or left to accumulate if the worker
never succeeds on any turn. Manual cleanup (`rm turn-*.txt`) is
safe at any time between sessions.

## Design decisions

**Asynchronous worker.** The worker takes several seconds per
turn. Running it inline would block every `stop` for that long.
Launching it detached keeps the user's `stop → next prompt`
experience instant; the memory entry lands on the following stop.

**Worker rewrites the turn file in place.** Using the same file
for input and output means the pipeline needs no separate
"output" path, no filename convention, and no race-prone
coordination. The file's first line is the state marker:
`PROMPT:...` → not yet processed, anything else → processed.

**Archive at stop, not at next prompt.** The stop hook already
runs after the turn ends, with the user waiting for nothing; a
few milliseconds of file IO there is invisible. Doing it at the
next `userPromptSubmit` would couple archive work to the start
of the user's next turn for no benefit.

**Turn file per turn, keyed by nanosecond timestamp.** A single
file would need locking or serialization; concurrent
userPromptSubmits could clobber each other. Per-file isolation
makes each turn independent.

**No database.** A turn file is a buffer, `long-term-memory.md`
is the store. A SQLite lifecycle has no reason to exist once
parse is automatic.

**No pattern detection.** Keyword clustering has low practical
value. When the user notices a recurring topic they create a
skill directly. The knowledge base itself reveals repeated
themes through search.

**Append-only memory store.** Deduplication would require the
worker to read the store, adding context, latency, and
complexity. Occasional duplicates cost less than slower parses.
Distillation, if ever needed, can be added as a separate pass.

**Memory is a property, not a skill.** There is no `SKILL.md`,
no description to match, no user-facing trigger. Memory is part
of what Fungus is, like the router or the system prompt.
