# Fungus

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Kiro CLI](https://img.shields.io/badge/runs%20on-Kiro%20CLI-7c3aed)](https://github.com/kirolabs/kiro)

General-purpose AI coding agent that builds long-term memory from
every interaction, extended by drop-in skills.

Fungus is a layer on top of [Kiro CLI](https://github.com/kirolabs/kiro).
It turns an ephemeral chat agent into one that accumulates
knowledge, adapts across sessions, and can be extended by adding
self-contained skill directories.

## Why

A coding agent that forgets everything between sessions can't grow
with your work. Every new chat starts from zero — you re-explain
the project, repeat preferences, rediscover the same gotchas.

Fungus fixes this at the agent level:

- Every turn is captured and distilled into a reusable memory
  entry automatically, without any user action.
- Entries are indexed as a knowledge base that the agent searches
  when a prompt references past context.
- Domain-specific behavior lives in drop-in skill directories;
  adding a skill is one folder and one config file.

## Features

- **Automatic long-term memory** — a background pipeline captures
  every prompt/tool/response cycle, extracts the reusable knowledge
  in it, and appends a Markdown entry to a searchable knowledge
  base. The user never triggers or reviews the pipeline.
- **Asynchronous parse worker** — memory extraction runs in a
  detached `kiro-cli` subprocess; the user's `stop → next prompt`
  experience stays instant.
- **Self-contained skills** — each skill is a folder with its own
  `SKILL.md`, scripts, references, and data. Add or remove skills
  by creating or deleting a directory.
- **Single-entry hook router** — one script dispatches every hook
  event to annotated handlers in `hooks/` or `skills/*/scripts/`
  by priority.
- **Progressive disclosure** — skill `description` fields are
  loaded at startup; full `SKILL.md` content and references load
  only when the agent activates the skill.
- **Batteries included** — Fungus ships with skills for
  Atlassian API access, Office document scraping/patching, prompt
  refinement, and tool usage auditing.

## Quickstart

Prerequisites:

- [Kiro CLI](https://github.com/kirolabs/kiro)
- Python 3.12+
- Git, Bash ≥ 4.0

Install:

```bash
git clone https://github.com/nsqk11/fungus.git
cd fungus
bash install.sh
kiro-cli chat --agent fungus
```

The installer copies Fungus into `$KIRO_HOME/skills/fungus`
(defaults to `~/.kiro/skills/fungus`), clones the reference
knowledge bases (Google style guide, design patterns), and writes
an agent configuration at `$KIRO_HOME/agents/fungus.json`.

## How it works

### Memory

Memory is an agent-level property — not a skill, not user-facing.
Each turn follows this path:

```
userPromptSubmit ──→ capture_prompt.py ──→ turn-<ns>.txt (new file)
preToolUse       ──→ capture_tool.py   ──→ turn-<ns>.txt (append)
postToolUse      ──→ capture_error.py  ──→ turn-<ns>.txt (append)
stop             ──→ auto_parse.sh     ──→ response appended
                                        ──→ worker spawned (async)
                                        ──→ older turns archived
```

`auto_parse.sh` launches the worker detached and returns
immediately, so the user feels no latency. The worker reads the
turn file and rewrites it in place: either a Markdown entry or
an empty file (drop). On the next `stop`, any turn file the
worker has finished rewriting is appended to
`data/long-term-memory.md` — the Markdown store that Kiro indexes
as the `fungus-memory` knowledge base.

See [`prompts/memory.md`](prompts/memory.md) for the full design.

### Hook routing

`hooks/router.py` is the single entry point registered with Kiro.
It scans three locations for annotated scripts:

- `hooks/*.{py,sh}` — top-level global hooks
- `hooks/<group>/*.{py,sh}` — grouped hooks (e.g. `hooks/memory/`)
- `skills/*/scripts/*.{py,sh}` — skill-owned hooks

Each script declares its trigger in a header comment:

```python
# @hook userPromptSubmit
# @priority 10
# @description Capture the user prompt into the turn file.
```

Scripts matching the current hook event run in priority order.
Files starting with `_` are skipped (shared utility modules).

The router exports `FUNGUS_ROOT` into the environment so child
scripts can locate installed files without hard-coded paths.

### Skills

Skills live in `skills/<name>/`. Each skill must have a
`SKILL.md` with YAML frontmatter declaring a name, description,
and triggers. The agent picks the right skill based on the
user's prompt matching the description.

The bundled skills:

| Skill | Purpose |
|-------|---------|
| [`atlassian-api`](skills/atlassian-api) | PAT management and Confluence page caching |
| [`office-toolkit`](skills/office-toolkit) | Scrape and patch docx/pptx/xlsx/pdf via XML |
| [`prompt-refinement`](skills/prompt-refinement) | Extract behavior principles from external projects |
| [`tool-audit`](skills/tool-audit) | Record and report on tool usage |

## Adding a skill

1. Create `skills/<name>/` with a `SKILL.md` in the format from
   the [Agent Skills Specification](knowledgeBase/agent-skills-spec.md).
   Keep descriptions sharp — see
   [`prompts/writing-standards.md`](prompts/writing-standards.md).
2. Add `scripts/` for hook handlers or CLI tools. Scripts starting
   with `_` are treated as shared modules (not dispatched).
3. Add `references/` for detail the `SKILL.md` body can point to
   — loaded only when the agent follows the reference.
4. Run `bash install.sh` to sync the new skill and regenerate the
   agent config.

## Directory layout

```
fungus/
├── install.sh                 Installs to $KIRO_HOME/skills/fungus
├── hooks/                     Agent-level hook scripts
│   ├── router.py              Single entry point; dispatches events
│   ├── inject_git_context.py  Inject git state before write ops
│   └── memory/                Memory pipeline (agent property)
│       ├── capture_*.py       Per-lifecycle-stage turn capture
│       ├── remind_search.py   Nudge agent to search memory KB
│       └── auto_parse.sh      Spawn async worker, archive turns
├── prompts/                   Agent-facing text
│   ├── system-prompt.md       Agent identity and behavior rules
│   ├── memory.md              Memory property definition
│   ├── parse-criteria.md      Memory-worker operating manual
│   ├── coding-standards.md    Project coding conventions
│   └── writing-standards.md   Project writing conventions
├── knowledgeBase/             Reference material indexed as KBs
│   └── agent-skills-spec.md   Skill format specification
└── skills/                    Self-contained skills
    ├── atlassian-api/
    ├── office-toolkit/
    ├── prompt-refinement/
    └── tool-audit/
```

At install time `install.sh` also creates
`$KIRO_HOME/skills/fungus/data/` for runtime state
(`long-term-memory.md`, transient `turn-*.txt` files).

## Uninstall

Remove the install directory and the agent config:

```bash
rm -rf "$KIRO_HOME/skills/fungus"
rm -f  "$KIRO_HOME/agents/fungus.json"
```

Knowledge-base caches under `$KIRO_HOME/skills/fungus/knowledgeBase/`
are disposable and can be regenerated by a reinstall.

## License

[MIT](LICENSE)
