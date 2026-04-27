# Fungus

General-purpose AI coding agent for [Kiro CLI](https://github.com/kirolabs/kiro)
with persistent memory and a skill-growth pipeline.

## What it does

Fungus runs on Kiro CLI and adds three things on top of a standard agent:

- **Long-term memory** — every interaction is captured, parsed, and
  promoted into durable notes that persist across sessions.
- **Skill growth** — recurring patterns in memory become candidates
  for new skills; mature patterns are written as reusable `SKILL.md`.
- **Self-contained skills** — each skill is a drop-in directory with
  its own hooks, scripts, references, and data. Skills can be added
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
│   └── router.py               Single entry point; routes hook events
│                               to skill scripts by annotation
├── prompts/
│   ├── system-prompt.md        Agent identity and behavior rules
│   ├── coding-standards.md     Project coding conventions
│   └── writing-standards.md    Project writing conventions
├── knowledgeBase/              Reference material indexed as KB
│   └── agent-skills-spec.md    Skill format specification
└── skills/                     Self-contained skill directories
    ├── memory-curation/        Memory capture, curation, growth
    ├── atlassian-api/          Confluence / Jira access
    ├── office-toolkit/         Office document scrape / patch
    └── prompt-refinement/      Agent prompt refinement guide
```

## How the memory pipeline works

```
hook event ──→ capture_*.py ──→ raw (memory.db)
                                   │
                                   ↓ parse-protocol (agent-guided)
                               parsed (memory.db)
                                   │
                                   ├─→ longterm  (memory.db)
                                   │     │
                                   │     └─→ memory.md (KB-indexed)
                                   │
                                   └─→ candidate (memory.db)
                                         │
                                         └─→ new skill in skills/
```

Hook scripts under `skills/memory-curation/scripts/` capture raw
signals. The agent parses them when prompted by
`<memory-curation-reminder>` tags injected at session start. Mature
patterns graduate into new skills through the pattern-protocol flow.

## Hook routing

`hooks/router.py` is the single entry point registered with Kiro.
It scans `skills/*/scripts/*.{py,sh}` for annotation headers:

```python
# @hook userPromptSubmit
# @priority 10
# @skill memory-curation
# @description Capture non-trivial user prompts as raw entries.
```

Scripts matching the current hook event run in priority order. Files
starting with `_` are skipped (used for shared utilities).

## Adding a new skill

1. Create `skills/<name>/` with a `SKILL.md` that follows the format
   in the `agent-skills-spec` KB and the Description Quality Checklist
   in `prompts/writing-standards.md`.
2. Add `scripts/` with any hook handlers (annotated) or CLI tools.
3. Add `references/` for progressive-disclosure content if the skill
   has deep operational detail.
4. Run `bash install.sh` to sync and re-register.

## License

[MIT](LICENSE)
