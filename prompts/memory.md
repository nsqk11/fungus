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
                                       ──→ extract worker spawned (async)
                                       ──→ older turn files archived
                                       ──→ distill worker spawned when
                                           long-term-memory.md exceeds 200
                                           entries (async)
                                       ──→ pending distill applied from a
                                           prior turn
```

Each turn has its own file, keyed by a nanosecond timestamp.
After the stop hook launches the extract worker, control returns
to the user immediately — the worker finishes on its own timeline.

The extract worker reads the turn file and rewrites it in place:
either a Markdown memory entry (keep) or an empty file (drop).
On the next stop, any turn file that is no longer `PROMPT:`-prefixed
is archived into `long-term-memory.md` and removed.

The distill worker reads `long-term-memory.md` and writes a
consolidated replacement to `memory-<ts>.md`. The next stop merges
that replacement with any entries appended since the worker took
its snapshot, atomically replaces the main file, and cleans up.

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

1. **Apply pending distill.** If a previous stop spawned a
   distill worker that finished, apply its result now: read
   `memory-<ts>.md` (the distilled replacement) and
   `memory-<ts>.snapshot.md` (the main file as the worker saw
   it), append any bytes written to `long-term-memory.md` beyond
   the snapshot's length, atomically replace the main file, and
   remove both files. Because `long-term-memory.md` is
   append-only, the post-snapshot tail is exactly the bytes
   beyond the snapshot's size, so no entries are lost even
   though the worker ran asynchronously.

2. **Finalize the current turn.** Find the newest
   `turn-*.txt`. If its first line is `PROMPT:`, append
   `RESPONSE: <assistant_response>` and spawn a detached
   `kiro-cli chat --no-interactive` extract worker whose prompt
   is `prompts/parse-criteria.md` plus the turn file's path. The
   worker reads, judges, and rewrites the file in place.

3. **Archive finished turns.** For every *other* `turn-*.txt`:
   - If the file is empty, remove it (the worker chose drop).
   - If the first line still starts with `PROMPT:`, skip it (the
     worker has not finished yet; it will be picked up on a
     future stop).
   - Otherwise the file is a finished memory entry: append it to
     `long-term-memory.md`, then remove it.

4. **Trigger distill.** Count entries (`## ` lines) in
   `long-term-memory.md`. If the count exceeds 200 and no
   `memory-*.snapshot.md` is already pending, snapshot the main
   file to `memory-<ts>.snapshot.md` and spawn a detached
   distill worker whose prompt is `prompts/distill-criteria.md`
   plus the snapshot path (input) and `memory-<ts>.md` (output).
   The worker reads the snapshot and writes a consolidated
   replacement; step 1 on a future stop applies it.

5. Exit immediately. Both workers keep running on their own.

**Extract worker** — a headless `kiro-cli chat --no-interactive`
invocation using the default agent. It needs `fs_read` (to read
the turn file) and `fs_write` (to overwrite it). The default
agent must have both tools enabled; without them the worker
cannot rewrite the turn file and the pipeline stalls. The worker
prompt is `parse-criteria.md` plus the turn file's path; the
worker reads the turn, decides keep or drop, and rewrites the
file.

Having the extract worker rewrite the turn file in place means:
- No separate output file to coordinate.
- The file's content is the pipeline's status marker:
  `PROMPT:...` means "not yet processed", anything else means
  "worker finished".
- `kiro-cli`'s unavoidable ANSI decoration on stdout is ignored
  entirely.

**Distill worker** — another headless `kiro-cli chat
--no-interactive` invocation. Its prompt is
`distill-criteria.md` plus two paths: the snapshot of
`long-term-memory.md` to read, and the output path
`memory-<ts>.md` to write. The worker reads the full snapshot,
decides merge / supersede / keep / drop across all entries, and
writes a consolidated replacement. It never touches the main
file directly; the apply step in step 1 of `auto_parse.sh` is
the only place the main file is replaced.

**`prompts/parse-criteria.md`** — the extract worker's
operating manual: what to keep, what to drop, and the turn-file
output format. Loaded into the worker prompt verbatim.

**`prompts/distill-criteria.md`** — the distill worker's
operating manual: merge / supersede / keep / drop rules across
the whole store, plus the replacement-file output format.
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
├── long-term-memory.md              # long-term store, KB-indexed
├── turn-<nanoseconds>.txt           # one per in-flight or pending turn
├── memory-<ts>.snapshot.md          # distill: snapshot taken when worker spawned
└── memory-<ts>.md                   # distill: worker's consolidated replacement
```

Normally only the current turn file exists. Extra turn files mean
one or more extract workers are still running or crashed
mid-parse. Files whose workers crashed before rewriting will be
reclaimed on the next successful turn-end — or left to accumulate
if the worker never succeeds on any turn.

A `memory-<ts>.snapshot.md` without a matching `memory-<ts>.md`
means a distill worker is still running or crashed before writing
its output; the snapshot alone blocks new distill triggers until
a `memory-<ts>.md` appears (apply succeeds and both files are
removed) or the user removes them manually.

Manual cleanup (`rm turn-*.txt` or `rm memory-*.md*`) is safe at
any time between sessions.

## Design decisions

**Asynchronous extract worker.** The extract worker takes
several seconds per turn. Running it inline would block every
`stop` for that long. Launching it detached keeps the user's
`stop → next prompt` experience instant; the memory entry lands
on the following stop.

**Extract worker rewrites the turn file in place.** Using the
same file for input and output means the pipeline needs no
separate "output" path, no filename convention, and no
race-prone coordination. The file's first line is the state
marker: `PROMPT:...` → not yet processed, anything else →
processed.

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

**Append-only memory store with periodic distillation.**
Per-turn writes never deduplicate — reading the full store on
every turn would add context, latency, and complexity for little
gain. Instead, the store grows append-only until it exceeds 200
entries, at which point a detached distill worker consolidates
it across all entries in one pass. Occasional duplicates between
distillations cost less than slower per-turn parses.

**Distill uses snapshot plus append-tail, not plain replace.**
The distill worker is detached and may finish several stops
later. In the meantime, new entries are appended to
`long-term-memory.md`. A plain replace would overwrite them.
Before spawning the worker, the hook copies the main file to
`memory-<ts>.snapshot.md`. When the hook applies the worker's
output, it takes `memory-<ts>.md` as the base and appends the
bytes in the main file beyond the snapshot's size. Because the
store is append-only, that byte range is exactly the entries
written during the worker's run — no data loss, no diffing, no
timestamps inside entries.

**One pending distill at a time.** The hook spawns a new distill
worker only when no `memory-<ts>.snapshot.md` exists. This
prevents concurrent workers from racing over the same main file
and simplifies the apply step to "find the one pair and use it".
If a worker crashes and leaves an orphan snapshot, the user can
remove `memory-*.md*` manually to unblock further triggers.

**Memory is a property, not a skill.** There is no `SKILL.md`,
no description to match, no user-facing trigger. Memory is part
of what Fungus is, like the router or the system prompt.
