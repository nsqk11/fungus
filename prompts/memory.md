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

Memory is implemented as a pipeline that runs outside your turn.
You do not invoke it; it observes.

```
userPromptSubmit ──→ memory/capture_prompt.py ──→ current-turn.txt (created)
preToolUse       ──→ memory/capture_tool.py   ──→ current-turn.txt (tool appended)
postToolUse      ──→ memory/capture_error.py  ──→ current-turn.txt (error appended)
stop             ──→ memory/auto_parse.sh     ──→ response appended
                                              ──→ worker invoked
                                              ──→ worker writes last-parse-output.md
                                              ──→ non-empty output appended to long-term-memory.md
                                              ──→ scratch files removed
```

One turn = one `userPromptSubmit` → `stop` cycle.
Each turn produces at most one memory entry.
Turns with no reusable knowledge are dropped silently.

### Components

**`hooks/memory/capture_prompt.py`** — `userPromptSubmit`: write
`PROMPT: <text>` to the turn file, overwriting any stale content
from a crashed prior turn.

**`hooks/memory/capture_tool.py`** — `preToolUse`: append `TOOL:
<name>` to the turn file. Skips noise tools such as `fs_read`,
`grep`, `glob`.

**`hooks/memory/capture_error.py`** — `postToolUse`: append
`ERROR: <text>` when `tool_response.success` is false.

**`hooks/memory/remind_search.py`** — `userPromptSubmit`: emit a
`<memory-reminder>` context entry reminding the agent to search
the `fungus-memory` KB when the prompt is ambiguous.

**`hooks/memory/_common.py`** — shared path constants and helpers.
Underscore prefix makes the router skip it (import-only module).

**`hooks/memory/auto_parse.sh`** — registered for `stop`. Runs the
entire parse in one shell invocation:

1. Append `RESPONSE: <assistant_response>` to the turn file.
2. Truncate `data/last-parse-output.md` to zero bytes so a stale
   output cannot be mistaken for this turn's result.
3. Build worker input: `parse-criteria.md` + turn content + the
   absolute path to write to (`<output_path>`).
4. Call the worker, discarding its stdout:
   ```bash
   kiro-cli chat --no-interactive --trust-all-tools "$input" \
     > /dev/null 2>&1
   ```
5. If `last-parse-output.md` is non-empty, append it to
   `long-term-memory.md`.
6. Remove `current-turn.txt` and `last-parse-output.md`.

**Worker** — a headless `kiro-cli chat --no-interactive`
invocation using the default agent. The worker needs one tool,
`fs_write`, to write its result. It reads
`prompts/parse-criteria.md` and the turn content from its prompt,
then writes either a Markdown memory entry or an empty file to
`<output_path>`.

Entry format (written to `<output_path>` when keeping):

```
## <summary>

Date: YYYY-MM-DD | Tags: tag1, tag2

<optional 1-3 sentence detail>
```

A drop is expressed as an empty file.

Writing via `fs_write` instead of parsing stdout avoids `kiro-cli`'s
unavoidable ANSI decoration, which would otherwise break any
boundary-based extraction.

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
├── current-turn.txt        # scratch, removed after stop
└── last-parse-output.md    # worker output, removed after stop
```

Worker I/O goes through `last-parse-output.md`, truncated at the
start of every turn and removed at the end. Stale scratch files
at `agentSpawn` indicate a crashed prior session and are cleaned
up then.

## Design decisions

**No database.** A turn file is a buffer, `long-term-memory.md` is
the store. A SQLite lifecycle has no reason to exist once parse is
automatic and single-pass.

**No pattern detection.** Keyword clustering has low practical
value. When the user notices a recurring topic they create a skill
directly. The knowledge base itself reveals repeated themes
through search.

**Append-only.** Deduplication would require the worker to read
the store, adding context, latency, and complexity. Occasional
duplicates cost less than slower parses. Distillation, if ever
needed, can be added as a separate pass.

**Worker writes to a file.** Capturing the worker's stdout would
have been simpler in principle, but `kiro-cli` emits ANSI color
codes and UI decorations even in `--no-interactive` mode, with no
documented way to disable them. Those escape sequences can split
literal boundary markers and corrupt captured content. Having the
worker call `fs_write` into a known path sidesteps the problem
entirely. The only prompt cost is telling the worker which path
to write to.

**Synchronous worker.** Backgrounding with `nohup … &` would let
the hook return faster but makes cleanup order fragile. The stop
hook already runs after the turn ends; blocking a few seconds is
acceptable.

**Scratch files under `data/`, not `/tmp`.** `current-turn.txt`
must cross multiple hook invocations, so it lives on disk.
`last-parse-output.md` could have gone in `/tmp`, but keeping all
runtime state together simplifies debugging and cleanup.

**Memory is a property, not a skill.** There is no `SKILL.md`, no
description to match, no user-facing trigger. Memory is part of
what Fungus is, like the router or the system prompt.
