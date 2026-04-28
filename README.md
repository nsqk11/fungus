# Fungus

General-purpose AI coding agent for [Kiro CLI](https://github.com/kirolabs/kiro)
with long-term memory and self-contained skills.

## What it does

Fungus runs on Kiro CLI and adds two things on top of a standard agent:

- **Long-term memory** — every turn is captured and distilled in
  the background into a searchable knowledge base, automatically
  and without user interaction. Past insights surface through KB
  search whenever relevant.
- **Self-contained skills** — each skill is a drop-in directory
  with its own scripts, references, and data. Skills can be added
  or removed without touching the core.

## Quickstart

```bash
git clone <this-repo> fungus
cd fungus
bash install.sh
kiro-cli chat --agent fungus
```

### Prerequisites

- [Kiro CLI](https://github.com/kirolabs/kiro)
- Python 3.12+
- Git, Bash ≥ 4.0

## Structure

```
fungus/
├── install.sh                  Installs to $KIRO_HOME/skills/fungus
├── hooks/
│   ├── router.py               Single entry point; dispatches events
│   │                           by annotation to grouped or skill scripts
│   ├── inject_git_context.py   Inject git state before write ops
│   └── memory/                 Memory pipeline (agent property)
│       ├── capture_*.py        Turn capture across lifecycle hooks
│       ├── remind_search.py    Nudge agent to search memory KB
│       └── auto_parse.sh       Extract entries at turn end
├── prompts/
│   ├── system-prompt.md        Agent identity and behavior rules
│   ├── memory.md               Memory property definition
│   ├── parse-criteria.md       Memory extraction criteria
│   ├── coding-standards.md     Project coding conventions
│   └── writing-standards.md    Project writing conventions
├── knowledgeBase/              Reference material indexed as KB
│   └── agent-skills-spec.md    Skill format specification
└── skills/                     Self-contained skill directories
    ├── atlassian-api/          Confluence / Jira access
    ├── office-toolkit/         Office document scrape / patch
    ├── prompt-refinement/      Agent prompt refinement guide
    └── tool-audit/             Tool usage statistics
```

## Memory

Memory is a property of the Fungus agent, not a skill. The user
never triggers or reviews it.

```
userPromptSubmit ──→ capture_prompt.py ──→ current-turn.txt
preToolUse       ──→ capture_tool.py   ──→ current-turn.txt
postToolUse      ──→ capture_error.py  ──→ current-turn.txt
stop             ──→ auto_parse.sh     ──→ worker extracts entry
                                       ──→ long-term-memory.md (KB)
```

Each turn is recorded to a scratch file. At the end of the turn,
`auto_parse.sh` runs a headless worker (`kiro-cli chat
--no-interactive`) that reads the turn and the extraction criteria,
then emits a sentinel-wrapped Markdown entry. The hook appends
non-empty entries to `data/long-term-memory.md`, which is indexed
as the `fungus-memory` knowledge base.

See `prompts/memory.md` for full details.

## Hook routing

`hooks/router.py` is the single entry point registered with Kiro.
It scans three locations for annotated scripts:

- `hooks/*.{py,sh}` — top-level global hooks
- `hooks/<group>/*.{py,sh}` — grouped hooks (e.g. `hooks/memory/`)
- `skills/*/scripts/*.{py,sh}` — skill-owned hooks

Each script declares its trigger in a header:

```python
# @hook userPromptSubmit
# @priority 10
# @description Capture the user prompt into the current turn file.
```

Scripts matching the current hook event run in priority order.
Files starting with `_` are skipped (shared utilities).

The router exports `FUNGUS_ROOT` into the environment so child
scripts can locate installed files without hard-coded paths.

## Adding a new skill

1. Create `skills/<name>/` with a `SKILL.md` that follows the format
   in the `agent-skills-spec` KB and the Description Quality
   Checklist in `prompts/writing-standards.md`.
2. Add `scripts/` with any hook handlers (annotated) or CLI tools.
3. Add `references/` for progressive-disclosure content if the
   skill has deep operational detail.
4. Run `bash install.sh` to sync and re-register.

## License

[MIT](LICENSE)
