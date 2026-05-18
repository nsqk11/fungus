# Fungus

General-purpose AI coding agent with persistent memory and intelligent
context-aware reminders, built on [Kiro CLI](https://github.com/kirolabs/kiro).

## Features

- **Persistent memory** — background pipeline extracts reusable
  knowledge from sessions into a searchable knowledge base.
- **Intelligent reminders** — LLM-powered context analysis selectively
  injects relevant reminders per interaction.
- **Drop-in skills** — extend behavior by adding skill directories.
- **Single-entry hook router** — one script dispatches all hook events
  to annotated handlers by priority.

## Requirements

- [Kiro CLI](https://github.com/kirolabs/kiro)
- Python ≥ 3.10
- Git

## Install

```bash
git clone https://github.com/youruser/fungus.git
cd fungus
bash install.sh
kiro-cli chat --agent fungus
```

## Structure

```
fungus/
├── hooks/
│   └── router.py                    # Hook dispatcher
├── prompts/
│   └── system-prompt.md             # Agent system prompt
├── properties/
│   ├── memory/
│   │   ├── memory.md                # Property definition
│   │   ├── extract-prompt.md        # Worker agent prompt
│   │   ├── _memory.py              # Core library (store/export/CLI)
│   │   └── hooks/
│   │       ├── spawn-extractor.py   # stop: spawn extraction worker
│   │       └── register-sessions.py # agentSpawn: register sessions
│   └── reminder/
│       ├── reminder.md              # Property definition
│       ├── analyze-prompt.md        # LLM classifier prompt + tendencies
│       └── hooks/
│           ├── analyze-and-inject.py # userPromptSubmit: LLM-driven
│           ├── git-reminder.py       # preToolUse: rule-based
│           ├── large-file-warning.py # preToolUse: rule-based
│           ├── failure-warning.py    # postToolUse: rule-based
│           └── context-limit.py      # postToolUse: rule-based
├── skills/
│   ├── atlassian-api/
│   └── project-workbench/
└── install.sh
```

## Properties vs Skills

- **Properties** are always-on agent capabilities (memory, reminders).
  They run via hooks on every interaction.
- **Skills** are on-demand capabilities activated when the user's
  request matches their trigger description.

## License

MIT
