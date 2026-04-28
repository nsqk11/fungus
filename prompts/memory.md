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
                                              ──→ worker invoked (in-process)
                                              ──→ entry extracted from stdout
                                              ──→ entry appended to long-term-memory.md
                                              ──→ current-turn.txt removed
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
2. Build worker input by concatenating `prompts/parse-criteria.md`
   and the turn file.
3. Call the worker, capturing stdout:
   ```bash
   output=$(kiro-cli chat --no-interactive --trust-all-tools "$input" 2>&1)
   ```
4. Extract the entry between sentinel markers:
   ```bash
   entry=$(echo "$output" \
     | sed -n '/<<<FUNGUS_MEMORY_BEGIN>>>/,/<<<FUNGUS_MEMORY_END>>>/p' \
     | sed '1d;$d')
   ```
5. If `$entry` is non-empty, append it to `long-term-memory.md`.
6. Remove `current-turn.txt`.

**Worker** — a headless `kiro-cli chat --no-interactive`
invocation using the default agent. No dedicated agent, no tools.
The worker reads `prompts/parse-criteria.md` and the turn content
in its prompt, then answers with a sentinel-wrapped Markdown
entry:

```
<<<FUNGUS_MEMORY_BEGIN>>>
## <summary>

Date: YYYY-MM-DD | Tags: tag1, tag2

<optional 1-3 sentence detail>
<<<FUNGUS_MEMORY_END>>>
```

A drop is expressed as empty markers.

**`prompts/parse-criteria.md`** — the worker's operating manual:
what to keep, what to drop, the sentinel-wrapped output format.
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
├── long-term-memory.md    # long-term store, KB-indexed
└── current-turn.txt       # scratch, removed after stop
```

Only two files. Worker I/O stays in shell variables and never hits
disk. A stale `current-turn.txt` at `agentSpawn` indicates a
crashed prior session and is cleaned up then.

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

**Worker has no tools.** Forcing the worker to call `fs_write`
would require extra prompting about paths and format. Plain text
output keeps the prompt minimal. Sentinel markers separate the
entry from any UI noise in stdout.

**Worker I/O in shell variables.** The parse runs entirely inside
`auto_parse.sh`. No intermediate files for worker input or output.

**Synchronous worker.** Backgrounding with `nohup … &` would let
the hook return faster but makes cleanup order fragile. The stop
hook already runs after the turn ends; blocking a few seconds is
acceptable.

**Scratch file under `data/`, not `/tmp`.** `current-turn.txt`
must cross multiple hook invocations, so it lives on disk. Keeping
it under `data/` shares permissions with the store and survives
reboots for debugging.

**Memory is a property, not a skill.** There is no `SKILL.md`, no
description to match, no user-facing trigger. Memory is part of
what Fungus is, like the router or the system prompt.
