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

Extract reusable knowledge from `raw` entries based on their `hook`
field. Skip everything that does not match these directions.

### userPromptSubmit

- User preferences and habits.
- Architecture decisions and rationale.
- Technical discoveries about tools or systems.
- Bugs, defects, or anomalies.
- Domain knowledge: naming rules, process conventions, reusable facts.

### toolChain

- Tool combination sequences for a task.
  Aggregated from individual tool calls within a turn by the stop
  hook.

### preToolUse

- Normally absent — aggregated into `toolChain` at stop time.
  If encountered, treat as residual and drop.

### postToolUse

- Error context: what failed, why, and surrounding conditions.
  Only failure entries reach this stage (successes are filtered
  at capture time).

### stop

- Agent analysis summaries: reasoning path, conclusions, decision
  rationale.

## Flow

1. Ask the user whether to parse now. Do not start without
   confirmation.
2. For each `raw` entry:
   - Read it with `get <id>`.
   - Check the `hook` field against the matching section above.
   - If the content matches one of the extraction directions, write
     a concise summary, pick 2-5 keywords, and promote to `parsed`.
   - Otherwise, drop it.
3. Report counts at the end: parsed vs dropped.
