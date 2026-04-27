# Parse Protocol

Operating manual for turning `raw` captures into `parsed` entries.
Invoked when a `<memory-curation-reminder>` reports unparsed data
pending at session start.

## Storage Commands

List unparsed entries:

```bash
python3.12 scripts/memory.py list --stage raw
```

List existing long-term memory:

```bash
python3.12 scripts/memory.py list --stage longterm
```

Get full entry detail:

```bash
python3.12 scripts/memory.py get <id>
```

Promote entry to `parsed`:

```bash
python3.12 scripts/memory.py update --id <id> --field stage --value parsed
python3.12 scripts/memory.py update --id <id> --field summary --value "<summary>"
python3.12 scripts/memory.py update --id <id> --field keywords --value '["kw1","kw2"]'
```

Drop a valueless entry:

```bash
python3.12 scripts/memory.py update --id <id> --field stage --value dropped
```

## What to Extract

Each `raw` entry represents one complete interaction (user prompt,
tool calls, and agent response stored in `data`). Evaluate the
interaction as a whole.

### Worth keeping

- User preferences and habits.
- Architecture decisions and rationale.
- Technical discoveries about tools or systems.
- Bugs, defects, or anomalies and their resolution.
- Domain knowledge: naming rules, process conventions, reusable facts.
- Tool combination sequences that solved a non-trivial task.

### Drop

- Routine file reads, simple edits, or navigation with no insight.
- Trivial confirmations ("好的", "继续", "看看").
- Interactions where the agent only repeated known information.

## Flow

1. Ask the user whether to parse now. Do not start without
   confirmation.
2. For each `raw` entry:
   - Read it with `get <id>`.
   - Review `data.prompt`, `data.tools`, `data.errors`, and
     `data.response` together.
   - If the interaction matches a "worth keeping" category, write
     a concise summary, pick 2-5 keywords, and promote to `parsed`.
   - Otherwise, drop it.
3. Report counts at the end: parsed vs dropped.
